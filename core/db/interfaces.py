"""
Интерфейсы (Protocol) для модульной архитектуры базы данных.
Определяют контракты для основных компонентов системы.
"""

from typing import Protocol, Any, Optional, List, Dict, Union, Iterator, TypeVar, Generic
from contextlib import AbstractContextManager
import sqlite3

T = TypeVar('T')


class Connection(Protocol):
    """Протокол для управления подключением к базе данных."""
    
    def connect(self) -> None:
        """Установить подключение к базе данных."""
        ...
    
    def disconnect(self) -> None:
        """Закрыть подключение к базе данных."""
        ...
    
    @property
    def is_connected(self) -> bool:
        """Проверить, активно ли подключение."""
        ...
    
    def get_raw_connection(self) -> sqlite3.Connection:
        """Получить низкоуровневое соединение sqlite3."""
        ...


class QueryExecutor(Protocol):
    """Протокол для выполнения SQL-запросов."""
    
    def execute(self, sql: str, params: tuple = ()) -> Union[bool, int]:
        """
        Выполнить SQL-запрос (INSERT, UPDATE, DELETE).
        
        Returns:
            True/False или lastrowid для INSERT.
        """
        ...
    
    def fetch_one(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """
        Выполнить SELECT и вернуть одну строку как словарь.
        
        Returns:
            Словарь с данными строки или None, если строк нет.
        """
        ...
    
    def fetch_all(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Выполнить SELECT и вернуть все строки как список словарей.
        """
        ...
    
    def fetch_value(self, sql: str, params: tuple = ()) -> Optional[Any]:
        """
        Выполнить SELECT и вернуть одно значение (первый столбец первой строки).
        
        Returns:
            Значение или None, если результат пуст.
        """
        ...


class TransactionManager(Protocol):
    """Протокол для управления транзакциями."""
    
    def transaction(self) -> Iterator[Any]:
        """
        Контекстный менеджер для транзакции.
        
        Usage:
            with transaction_manager.transaction() as cursor:
                cursor.execute(...)
        """
        ...
    
    def begin(self) -> None:
        """Начать транзакцию вручную."""
        ...
    
    def commit(self) -> None:
        """Зафиксировать текущую транзакцию."""
        ...
    
    def rollback(self) -> None:
        """Откатить текущую транзакцию."""
        ...


class Repository(Protocol[T]):
    """Базовый протокол для репозиториев, работающих с моделями типа T."""
    
    def get_by_id(self, id: int) -> Optional[T]:
        """Получить запись по ID."""
        ...
    
    def get_all(self, **filters) -> List[T]:
        """Получить все записи с опциональными фильтрами."""
        ...
    
    def add(self, data: T) -> int:
        """Добавить новую запись и вернуть её ID."""
        ...
    
    def update(self, id: int, data: T) -> bool:
        """Обновить запись с указанным ID."""
        ...
    
    def delete(self, id: int) -> bool:
        """Удалить запись с указанным ID."""
        ...