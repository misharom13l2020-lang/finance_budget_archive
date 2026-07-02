"""
Выполнение SQL-запросов к базе данных.
Реализует протокол QueryExecutor.
"""

import logging
import threading
from typing import Any, Optional, List, Dict, Union
from core.db.interfaces import QueryExecutor, Connection

logger = logging.getLogger(__name__)


class SQLiteQueryExecutor(QueryExecutor):
    """Выполнение SQL-запросов с поддержкой потокобезопасности."""
    
    def __init__(self, connection: Connection):
        """
        Args:
            connection: Объект подключения к БД (реализует Connection).
        """
        self.connection = connection
        self.mutex = threading.Lock()
    
    def execute(self, sql: str, params: tuple = ()) -> Union[bool, int]:
        """
        Выполнить SQL-запрос (INSERT, UPDATE, DELETE).
        
        Args:
            sql: SQL-запрос.
            params: Параметры запроса.
            
        Returns:
            True/False или lastrowid для INSERT.
        """
        with self.mutex:
            try:
                conn = self.connection.get_raw_connection()
                cursor = conn.cursor()
                
                logger.debug(f"Выполнение SQL: {sql[:100]}...")
                if params:
                    logger.debug(f"Параметры: {params}")
                
                cursor.execute(sql, params)
                conn.commit()
                
                # Возвращаем ID вставленной записи или True
                result = cursor.lastrowid if cursor.lastrowid else True
                return result
                
            except Exception as e:
                logger.error(f"Ошибка SQL: {e}")
                logger.error(f"Запрос: {sql}")
                logger.error(f"Параметры: {params}")
                raise
    
    def fetch_one(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """
        Выполнить SELECT и вернуть одну строку как словарь.
        
        Args:
            sql: SQL-запрос.
            params: Параметры запроса.
            
        Returns:
            Словарь с данными строки или None, если строк нет.
        """
        with self.mutex:
            try:
                conn = self.connection.get_raw_connection()
                cursor = conn.cursor()
                
                logger.debug(f"Выполнение SQL (fetch_one): {sql[:100]}...")
                if params:
                    logger.debug(f"Параметры: {params}")
                
                cursor.execute(sql, params)
                result = cursor.fetchone()
                
                if result:
                    return dict(result)
                return None
                
            except Exception as e:
                logger.error(f"Ошибка SQL: {e}")
                logger.error(f"Запрос: {sql}")
                logger.error(f"Параметры: {params}")
                raise
    
    def fetch_all(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Выполнить SELECT и вернуть все строки как список словарей.
        
        Args:
            sql: SQL-запрос.
            params: Параметры запроса.
            
        Returns:
            Список словарей с данными строк.
        """
        with self.mutex:
            try:
                conn = self.connection.get_raw_connection()
                cursor = conn.cursor()
                
                logger.debug(f"Выполнение SQL (fetch_all): {sql[:100]}...")
                if params:
                    logger.debug(f"Параметры: {params}")
                
                cursor.execute(sql, params)
                results = cursor.fetchall()
                
                return [dict(row) for row in results]
                
            except Exception as e:
                logger.error(f"Ошибка SQL: {e}")
                logger.error(f"Запрос: {sql}")
                logger.error(f"Параметры: {params}")
                raise
    
    def fetch_value(self, sql: str, params: tuple = ()) -> Optional[Any]:
        """
        Выполнить SELECT и вернуть одно значение (первый столбец первой строки).
        
        Args:
            sql: SQL-запрос.
            params: Параметры запроса.
            
        Returns:
            Значение или None, если результат пуст.
        """
        with self.mutex:
            try:
                conn = self.connection.get_raw_connection()
                cursor = conn.cursor()
                
                logger.debug(f"Выполнение SQL (fetch_value): {sql[:100]}...")
                if params:
                    logger.debug(f"Параметры: {params}")
                
                cursor.execute(sql, params)
                result = cursor.fetchone()
                
                if result:
                    return result[0]
                return None
                
            except Exception as e:
                logger.error(f"Ошибка SQL: {e}")
                logger.error(f"Запрос: {sql}")
                logger.error(f"Параметры: {params}")
                raise