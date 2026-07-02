"""
Репозиторий для работы со счетами (accounts).
Работает с dataclass-моделями вместо словарей.
"""

import logging
from typing import List, Dict, Any, Optional
from core.db.repositories.base import BaseRepository
from core.db.models import Account
from core.db.interfaces import QueryExecutor

logger = logging.getLogger(__name__)


class AccountRepository(BaseRepository[Account]):
    """Репозиторий для работы со счетами."""
    
    def _get_table_name(self) -> str:
        return "accounts"
    
    def _get_model_class(self) -> type[Account]:
        return Account
    
    def get_accounts(self, active_only: bool = True, include_system: bool = False) -> List[Account]:
        """Получение всех счетов."""
        sql = '''
            SELECT id, name, type, initial_balance, current_balance,
                   credit_limit, payment_due_day, min_payment_percent,
                   last_payment_date, created_at, is_active, is_system, currency
            FROM accounts
            WHERE 1=1
        '''
        
        params = []
        if active_only:
            sql += " AND is_active = 1"
        if not include_system:
            sql += " AND is_system = 0"
        
        sql += " ORDER BY type, name"
        rows = self.executor.fetch_all(sql, tuple(params))
        return [self._to_model(row) for row in rows]
    
    def get_account_by_name(self, name: str) -> Optional[Account]:
        """Получение счета по имени."""
        sql = '''
            SELECT id, name, type, initial_balance, current_balance,
                   credit_limit, payment_due_day, min_payment_percent,
                   last_payment_date, created_at, is_active, is_system, currency
            FROM accounts
            WHERE name = ?
        '''
        row = self.executor.fetch_one(sql, (name,))
        if row is None:
            return None
        return self._to_model(row)
    
    def update_account_balance(self, account_id: int, amount_change: float) -> bool:
        """Обновление баланса счета."""
        try:
            amount_change = float(amount_change)
        except (ValueError, TypeError):
            logger.error(f"Некорректное значение изменения баланса: {amount_change}")
            return False
        
        sql = "UPDATE accounts SET current_balance = current_balance + ? WHERE id = ?"
        success = self.executor.execute(sql, (amount_change, account_id))
        
        if success:
            logger.debug(f"Обновлен баланс счета {account_id} на {amount_change}")
        
        return bool(success)
    
    def get_credit_cards(self) -> List[Account]:
        """Получение всех кредитных карт."""
        sql = '''
            SELECT id, name, type, initial_balance, current_balance,
                   credit_limit, payment_due_day, min_payment_percent,
                   last_payment_date, created_at, is_active, currency
            FROM accounts
            WHERE type = 'Credit Card' AND is_active = 1
            ORDER BY name
        '''
        rows = self.executor.fetch_all(sql)
        return [self._to_model(row) for row in rows]
    
    def get_counterparty_accounts(self) -> List[Account]:
        """Получение всех счетов контрагентов."""
        sql = '''
            SELECT id, name, type, current_balance, created_at, is_active
            FROM accounts
            WHERE type = 'Counterparty'
            ORDER BY name
        '''
        rows = self.executor.fetch_all(sql)
        return [self._to_model(row) for row in rows]
    
    def create_counterparty_account(self, contact_name: str) -> int:
        """Создание или получение счета контрагента."""
        account_name = f"Контрагент: {contact_name}"
        
        # Проверяем существование
        existing = self.get_account_by_name(account_name)
        if existing:
            return existing.id
        
        # Создаем новый
        account_id = self.add({
            'name': account_name,
            'type': 'Counterparty',
            'initial_balance': 0.0,
            'current_balance': 0.0,
            'is_system': True,
            'is_active': True
        })
        
        logger.info(f"Создан счет контрагента: {account_name} (ID: {account_id})")
        return account_id
    
    def delete_account_with_checks(self, account_id: int) -> Dict[str, Any]:
        """
        Удаление счета с проверкой связанных операций.
        Возвращает dict с результатом операции.
        """
        try:
            # Проверяем существование счета
            account = self.get_by_id(account_id)
            if not account:
                return {
                    'success': False,
                    'message': f"Счет с ID {account_id} не найден"
                }
            
            account_name = account.name
            
            # Проверяем наличие связанных операций
            checks = [
                ("транзакций", "SELECT COUNT(*) FROM transactions WHERE account_id = ?"),
                ("исходящих переводов", "SELECT COUNT(*) FROM transfers WHERE from_account_id = ?"),
                ("входящих переводов", "SELECT COUNT(*) FROM transfers WHERE to_account_id = ?"),
                ("займов", "SELECT COUNT(*) FROM loans WHERE account_id = ? OR counterparty_account_id = ?")
            ]
            
            operations = []
            total_count = 0
            
            for operation_name, query in checks:
                if 'counterparty_account_id' in query:
                    count = self.executor.fetch_value(query, (account_id, account_id)) or 0
                else:
                    count = self.executor.fetch_value(query, (account_id,)) or 0
                
                if count > 0:
                    operations.append(f"{count} {operation_name}")
                    total_count += count
            
            if total_count > 0:
                return {
                    'success': False,
                    'can_delete': False,
                    'account_name': account_name,
                    'operations': operations,
                    'total_operations': total_count,
                    'message': f"На счете '{account_name}' есть связанные операции"
                }
            
            # Удаляем счет
            success = self.delete(account_id)
            
            if success:
                logger.info(f"Удален счет: {account_name} (ID: {account_id})")
                
                return {
                    'success': True,
                    'message': f"Счет '{account_name}' успешно удален"
                }
            else:
                return {
                    'success': False,
                    'message': f"Ошибка при удалении счета '{account_name}'"
                }
                
        except Exception as e:
            logger.error(f"Ошибка при удалении счета: {e}")
            return {
                'success': False,
                'message': f"Ошибка при удалении счета: {str(e)}"
            }