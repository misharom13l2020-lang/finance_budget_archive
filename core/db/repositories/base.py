"""
Базовый класс репозитория с общими методами CRUD.
Работает с dataclass-моделями вместо словарей.
"""

import logging
from typing import Type, TypeVar, Generic, Optional, List, Dict, Any
from core.db.interfaces import QueryExecutor, Repository
from core.db.models import (
    Account, Category, Transaction, Transfer, Budget, Loan, LoanPayment
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseRepository(Repository, Generic[T]):
    """Базовый репозиторий с общими CRUD операциями."""
    
    def __init__(self, executor: QueryExecutor):
        """
        Args:
            executor: Исполнитель SQL-запросов.
        """
        self.executor = executor
        self._table_name = self._get_table_name()
        self._model_class = self._get_model_class()
    
    def _get_table_name(self) -> str:
        """Получить имя таблицы, соответствующее репозиторию."""
        # По умолчанию имя класса репозитория без суффикса 'Repository' в нижнем регистре
        class_name = self.__class__.__name__
        if class_name.endswith('Repository'):
            class_name = class_name[:-10]
        return class_name.lower() + 's'
    
    def _get_model_class(self) -> Type[T]:
        """Получить класс модели, соответствующей репозиторию."""
        # Должен быть переопределён в дочерних классах
        raise NotImplementedError("Дочерний класс должен определить _get_model_class()")
    
    def _to_model(self, data: Dict[str, Any]) -> T:
        """
        Преобразовать словарь данных в объект модели.
        
        Args:
            data: Словарь с данными из БД.
            
        Returns:
            Объект модели.
        """
        # Используем метод from_dict модели, если он есть, иначе создаем через конструктор
        if hasattr(self._model_class, 'from_dict'):
            return self._model_class.from_dict(data)
        else:
            return self._model_class(**data)
    
    def _from_model(self, model: T) -> Dict[str, Any]:
        """
        Преобразовать объект модели в словарь для БД.
        
        Args:
            model: Объект модели.
            
        Returns:
            Словарь с данными для БД (исключая None значения).
        """
        # Используем метод to_dict модели, если он есть, иначе преобразуем через asdict
        if hasattr(model, 'to_dict'):
            return model.to_dict()
        else:
            from dataclasses import asdict
            return asdict(model)
    
    def get_by_id(self, id: int) -> Optional[T]:
        """Получить запись по ID."""
        sql = f"SELECT * FROM {self._table_name} WHERE id = ?"
        row = self.executor.fetch_one(sql, (id,))
        if row is None:
            return None
        return self._to_model(row)
    
    def get_all(self, **filters) -> List[T]:
        """Получить все записи с опциональными фильтрами."""
        sql = f"SELECT * FROM {self._table_name}"
        params = []
        
        if filters:
            conditions = []
            for key, value in filters.items():
                if value is None:
                    conditions.append(f"{key} IS NULL")
                else:
                    conditions.append(f"{key} = ?")
                    params.append(value)
            sql += " WHERE " + " AND ".join(conditions)
        
        sql += " ORDER BY id"
        rows = self.executor.fetch_all(sql, tuple(params))
        return [self._to_model(row) for row in rows]
    
    def add(self, data: T) -> int:
        """Добавить новую запись и вернуть её ID."""
        # Если передан словарь, преобразуем в модель для единообразия
        if isinstance(data, dict):
            # Создаем модель из словаря (временная модель для преобразования)
            model = self._to_model(data)
        else:
            model = data
        
        # Преобразуем модель в словарь для БД
        data_dict = self._from_model(model)
        # Удаляем id, если он есть (автоинкремент)
        data_dict.pop('id', None)
        
        columns = ', '.join(data_dict.keys())
        placeholders = ', '.join(['?'] * len(data_dict))
        sql = f"INSERT INTO {self._table_name} ({columns}) VALUES ({placeholders})"
        
        params = tuple(data_dict.values())
        result = self.executor.execute(sql, params)
        
        if isinstance(result, int):
            return result
        else:
            # Если execute вернул True, нужно получить lastrowid через отдельный запрос
            sql = "SELECT last_insert_rowid()"
            return self.executor.fetch_value(sql) or 0
    
    def update(self, id: int, data: T) -> bool:
        """Обновить запись с указанным ID."""
        # Если передан словарь, преобразуем в модель для единообразия
        if isinstance(data, dict):
            model = self._to_model(data)
        else:
            model = data
        
        # Преобразуем модель в словарь для БД
        data_dict = self._from_model(model)
        if not data_dict:
            return False
        
        # Удаляем id из данных обновления
        data_dict.pop('id', None)
        
        columns = ', '.join([f"{key} = ?" for key in data_dict.keys()])
        sql = f"UPDATE {self._table_name} SET {columns} WHERE id = ?"
        
        params = tuple(data_dict.values()) + (id,)
        result = self.executor.execute(sql, params)
        
        return bool(result)
    
    def delete(self, id: int) -> bool:
        """Удалить запись с указанным ID."""
        sql = f"DELETE FROM {self._table_name} WHERE id = ?"
        result = self.executor.execute(sql, (id,))
        return bool(result)