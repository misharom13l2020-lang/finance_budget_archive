"""
Управление транзакциями базы данных.
Реализует протокол TransactionManager.
"""

import logging
import sqlite3
from contextlib import contextmanager
from typing import Iterator
from core.db.interfaces import TransactionManager, Connection

logger = logging.getLogger(__name__)


class SQLiteTransactionManager(TransactionManager):
    """Менеджер транзакций для SQLite."""
    
    def __init__(self, connection: Connection):
        """
        Args:
            connection: Объект подключения к БД.
        """
        self.connection = connection
    
    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Cursor]:
        """
        Контекстный менеджер для транзакции.
        
        Usage:
            with transaction_manager.transaction() as cursor:
                cursor.execute(...)
        """
        conn = self.connection.get_raw_connection()
        cursor = conn.cursor()
        
        try:
            yield cursor
            conn.commit()
            logger.debug("Транзакция успешно завершена")
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка в транзакции: {e}")
            raise
    
    def begin(self) -> None:
        """Начать транзакцию вручную."""
        conn = self.connection.get_raw_connection()
        conn.execute("BEGIN TRANSACTION")
        logger.debug("Транзакция начата")
    
    def commit(self) -> None:
        """Зафиксировать текущую транзакцию."""
        conn = self.connection.get_raw_connection()
        conn.commit()
        logger.debug("Транзакция зафиксирована")
    
    def rollback(self) -> None:
        """Откатить текущую транзакцию."""
        conn = self.connection.get_raw_connection()
        conn.rollback()
        logger.debug("Транзакция откачена")