"""
Репозиторий для работы с переводами (transfers).
Работает с dataclass-моделями вместо словарей.
"""

import logging
from typing import List, Dict, Any, Optional
from core.db.repositories.base import BaseRepository
from core.db.models import Transfer
from core.db.interfaces import QueryExecutor, TransactionManager
from core.db.repositories.account_repository import AccountRepository

logger = logging.getLogger(__name__)


class TransferRepository(BaseRepository[Transfer]):
    """Репозиторий для работы с переводами."""
    
    def __init__(self, executor: QueryExecutor, account_repository: AccountRepository):
        """
        Args:
            executor: Исполнитель SQL-запросов.
            account_repository: Репозиторий счетов для обновления балансов.
        """
        super().__init__(executor)
        self.account_repository = account_repository
    
    def _get_table_name(self) -> str:
        return "transfers"
    
    def _get_model_class(self) -> type[Transfer]:
        return Transfer
    
    def get_transfers(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Получение всех переводов."""
        sql = '''
            SELECT 
                t.id, t.date, t.amount, t.description, t.created_at,
                fa.id as from_account_id, fa.name as from_account_name,
                fa.type as from_account_type, fa.currency as from_account_currency,
                ta.id as to_account_id, ta.name as to_account_name,
                ta.type as to_account_type, ta.currency as to_account_currency
            FROM transfers t
            JOIN accounts fa ON t.from_account_id = fa.id
            JOIN accounts ta ON t.to_account_id = ta.id
            WHERE 1=1
        '''
        
        params = []
        
        if filters:
            if 'date_from' in filters and filters['date_from']:
                sql += " AND t.date >= ?"
                params.append(filters['date_from'])
            
            if 'date_to' in filters and filters['date_to']:
                sql += " AND t.date <= ?"
                params.append(filters['date_to'])
            
            if 'account_id' in filters and filters['account_id']:
                sql += " AND (t.from_account_id = ? OR t.to_account_id = ?)"
                params.extend([filters['account_id'], filters['account_id']])
        
        sql += " ORDER BY t.date DESC"
        return self.executor.fetch_all(sql, tuple(params))
    
    def add_transfer(self, transfer_data: Dict[str, Any]) -> int:
        """Добавление нового перевода с обновлением балансов счетов."""
        required_fields = ['date', 'amount', 'from_account_id', 'to_account_id']
        for field in required_fields:
            if field not in transfer_data:
                raise ValueError(f"Отсутствует обязательное поле: {field}")
        
        if transfer_data['from_account_id'] == transfer_data['to_account_id']:
            raise ValueError("Нельзя переводить средства на тот же счет")
        
        # Обновляем баланс счета-отправителя
        self.account_repository.update_account_balance(
            transfer_data['from_account_id'],
            -transfer_data['amount']
        )
        
        # Обновляем баланс счета-получателя
        self.account_repository.update_account_balance(
            transfer_data['to_account_id'],
            transfer_data['amount']
        )
        
        # Добавляем запись о переводе
        sql = '''
            INSERT INTO transfers 
            (date, amount, from_account_id, to_account_id, description)
            VALUES (?, ?, ?, ?, ?)
        '''
        
        params = (
            transfer_data['date'],
            transfer_data['amount'],
            transfer_data['from_account_id'],
            transfer_data['to_account_id'],
            transfer_data.get('description', '')
        )
        
        transfer_id = self.executor.execute(sql, params)
        
        logger.info(f"Добавлен перевод ID: {transfer_id}")
        return transfer_id
    
    def delete_transfer_with_restore(self, transfer_id: int) -> bool:
        """Удаление перевода с восстановлением балансов."""
        # Получаем данные перевода через модель
        transfer = self.get_by_id(transfer_id)
        if not transfer:
            logger.error(f"Перевод с ID {transfer_id} не найден")
            return False
        
        # Восстанавливаем балансы
        self.account_repository.update_account_balance(
            transfer.from_account_id,
            transfer.amount  # Возвращаем отправителю
        )
        
        self.account_repository.update_account_balance(
            transfer.to_account_id,
            -transfer.amount  # Забираем у получателя
        )
        
        # Удаляем перевод
        success = self.delete(transfer_id)
        
        if success:
            logger.info(f"Удален перевод ID: {transfer_id}")
        
        return success