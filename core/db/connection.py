"""
Управление подключением к SQLite базе данных.
Реализует протокол Connection.
"""

import sqlite3
import threading
import logging
from typing import Optional
from core.db.interfaces import Connection

logger = logging.getLogger(__name__)


class SQLiteConnection(Connection):
    """Управление подключением к SQLite с поддержкой thread-local соединений."""
    
    def __init__(self, db_path: str = None):
        """
        Args:
            db_path: Путь к файлу базы данных SQLite. 
                    Если None — используется путь рядом с .exe
        """
        if db_path is None:
            db_path = get_db_path()  # ← Используем абсолютный путь по умолчанию
        self.db_path = db_path
        self._thread_local = threading.local()
        self._is_connected = False

    def connect(self) -> None:
        """Установить подключение к базе данных."""
        if self.is_connected:
            logger.debug("Подключение уже установлено")
            return
        
        # Создаём соединение для текущего потока, если его нет
        if not hasattr(self._thread_local, 'connection'):
            conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            conn.row_factory = sqlite3.Row  # Для преобразования в dict
            conn.execute("PRAGMA foreign_keys = ON")
            self._thread_local.connection = conn
            self._is_connected = True
            logger.debug(f"Создано новое соединение с БД: {self.db_path}")
        else:
            self._is_connected = True
    
    def disconnect(self) -> None:
        """Закрыть подключение к базе данных."""
        if hasattr(self._thread_local, 'connection'):
            try:
                self._thread_local.connection.close()
                logger.debug("Соединение с БД закрыто")
            except Exception as e:
                logger.error(f"Ошибка при закрытии соединения: {e}")
            finally:
                del self._thread_local.connection
                self._is_connected = False
    
    @property
    def is_connected(self) -> bool:
        """Проверить, активно ли подключение."""
        return self._is_connected and hasattr(self._thread_local, 'connection')
    
    def get_raw_connection(self) -> sqlite3.Connection:
        """
        Получить низкоуровневое соединение sqlite3.
        
        Returns:
            Активное соединение sqlite3.Connection.
            
        Raises:
            RuntimeError: Если соединение не установлено.
        """
        if not self.is_connected:
            raise RuntimeError("Соединение с БД не установлено. Вызовите connect() перед использованием.")
        return self._thread_local.connection
    
    def __enter__(self):
        """Поддержка контекстного менеджера."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Автоматическое закрытие соединения при выходе из контекста."""
        self.disconnect()