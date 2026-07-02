"""
Репозиторий для работы с займами (loans).
Работает с dataclass-моделями вместо словарей.
"""

import logging
from typing import List, Dict, Any, Optional
from core.db.repositories.base import BaseRepository
from core.db.models import Loan
from core.db.interfaces import QueryExecutor, TransactionManager
from core.db.repositories.account_repository import AccountRepository

logger = logging.getLogger(__name__)


class LoanRepository(BaseRepository[Loan]):
    """Репозиторий для работы с займами."""
    
    def __init__(self, executor: QueryExecutor, account_repository: AccountRepository):
        """
        Args:
            executor: Исполнитель SQL-запросов.
            account_repository: Репозиторий счетов для обновления балансов.
        """
        super().__init__(executor)
        self.account_repository = account_repository
    
    def _get_table_name(self) -> str:
        return "loans"
    
    def _get_model_class(self) -> type[Loan]:
        return Loan
    
    def get_loans(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Получение всех займов."""
        sql = '''
            SELECT 
                l.id, l.account_id, l.counterparty_account_id,
                l.contact_name, l.loan_type, l.loan_amount,
                l.outstanding_amount, l.interest_rate,
                l.issue_date, l.due_date, l.description,
                l.status, l.created_at,
                a.name as account_name,
                ca.name as counterparty_name
            FROM loans l
            JOIN accounts a ON l.account_id = a.id
            JOIN accounts ca ON l.counterparty_account_id = ca.id
            WHERE 1=1
        '''
        
        params = []
        
        if filters:
            if 'loan_type' in filters and filters['loan_type']:
                sql += " AND l.loan_type = ?"
                params.append(filters['loan_type'])
            
            if 'status' in filters and filters['status']:
                sql += " AND l.status = ?"
                params.append(filters['status'])
            
            if 'contact_name' in filters and filters['contact_name']:
                sql += " AND l.contact_name LIKE ?"
                params.append(f"%{filters['contact_name']}%")
        
        sql += " ORDER BY l.issue_date DESC"
        return self.executor.fetch_all(sql, tuple(params))
    
    def add_loan(self, loan_data: Dict[str, Any]) -> int:
        """Добавление нового займа."""
        required_fields = ['account_id', 'contact_name', 'loan_type', 'loan_amount', 'issue_date']
        for field in required_fields:
            if field not in loan_data:
                raise ValueError(f"Отсутствует обязательное поле: {field}")
        
        # Создаем или получаем счет контрагента
        counterparty_account_id = self.account_repository.create_counterparty_account(
            loan_data['contact_name']
        )
        
        # Добавляем займ
        sql = '''
            INSERT INTO loans 
            (account_id, counterparty_account_id, contact_name, loan_type, 
             loan_amount, outstanding_amount, interest_rate, issue_date, 
             due_date, description, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        params = (
            loan_data['account_id'],
            counterparty_account_id,
            loan_data['contact_name'],
            loan_data['loan_type'],
            loan_data['loan_amount'],
            loan_data['loan_amount'],  # начальный outstanding = loan_amount
            loan_data.get('interest_rate', 0.0),
            loan_data['issue_date'],
            loan_data.get('due_date'),
            loan_data.get('description', ''),
            loan_data.get('status', 'active')
        )
        
        loan_id = self.executor.execute(sql, params)
        
        # Обновляем балансы счетов
        if loan_data['loan_type'] == 'received':
            # Получен займ: наш счет +, контрагент -
            self.account_repository.update_account_balance(
                loan_data['account_id'],
                loan_data['loan_amount']
            )
            self.account_repository.update_account_balance(
                counterparty_account_id,
                -loan_data['loan_amount']
            )
        else:  # 'issued'
            # Выдан займ: наш счет -, контрагент +
            self.account_repository.update_account_balance(
                loan_data['account_id'],
                -loan_data['loan_amount']
            )
            self.account_repository.update_account_balance(
                counterparty_account_id,
                loan_data['loan_amount']
            )
        
        logger.info(f"Добавлен займ ID: {loan_id}")
        return loan_id
    
    def update_loan(self, loan_id: int, loan_data: Dict[str, Any]) -> bool:
        """Обновление данных займа."""
        if not loan_data:
            return False
        
        # Проверяем существование займа
        loan = self.get_by_id(loan_id)
        if not loan:
            logger.error(f"Займ с ID {loan_id} не найден")
            return False
        
        # Разрешенные поля для обновления
        allowed_fields = [
            'contact_name', 'due_date', 'description', 'status',
            'interest_rate', 'outstanding_amount'
        ]
        
        fields = []
        params = []
        
        for field, value in loan_data.items():
            if field in allowed_fields:
                fields.append(f"{field} = ?")
                params.append(value)
        
        if not fields:
            logger.warning("Нет полей для обновления в займе")
            return False
        
        params.append(loan_id)
        sql = f"UPDATE loans SET {', '.join(fields)} WHERE id = ?"
        
        try:
            success = self.executor.execute(sql, tuple(params))
            if success:
                logger.info(f"Обновлен займ ID: {loan_id}")
            
            return bool(success)
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении займа: {e}")
            return False
    
    def get_loan_payments(self, loan_id: int) -> List[Dict[str, Any]]:
        """Получение платежей по займу."""
        sql = '''
            SELECT 
                id, loan_id, payment_date, payment_amount,
                interest_amount, principal_amount, description, created_at
            FROM loan_payments
            WHERE loan_id = ?
            ORDER BY payment_date DESC
        '''
        return self.executor.fetch_all(sql, (loan_id,))