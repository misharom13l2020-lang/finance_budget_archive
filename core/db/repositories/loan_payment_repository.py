"""
Репозиторий для работы с платежами по займам (loan_payments).
"""

import logging
from typing import List, Dict, Any, Optional
from core.db.repositories.base import BaseRepository
from core.db.models import LoanPayment
from core.db.interfaces import QueryExecutor, TransactionManager
from core.db.repositories.loan_repository import LoanRepository
from core.db.repositories.transfer_repository import TransferRepository

logger = logging.getLogger(__name__)


class LoanPaymentRepository(BaseRepository[LoanPayment]):
    """Репозиторий для работы с платежами по займам."""
    
    def __init__(self, executor: QueryExecutor, loan_repository: LoanRepository, 
                 transfer_repository: TransferRepository):
        """
        Args:
            executor: Исполнитель SQL-запросов.
            loan_repository: Репозиторий займов для обновления остатка долга.
            transfer_repository: Репозиторий переводов для создания операции перевода.
        """
        super().__init__(executor)
        self.loan_repository = loan_repository
        self.transfer_repository = transfer_repository
    
    def _get_table_name(self) -> str:
        return "loan_payments"
    
    def _get_model_class(self) -> type[LoanPayment]:
        return LoanPayment
    
    def add_loan_payment(self, payment_data: Dict[str, Any]) -> int:
        """Добавление платежа по займу."""
        required_fields = ['loan_id', 'payment_date', 'payment_amount']
        for field in required_fields:
            if field not in payment_data:
                raise ValueError(f"Отсутствует обязательное поле: {field}")
        
        # Получаем данные займа
        loan = self.loan_repository.get_by_id(payment_data['loan_id'])
        if not loan:
            raise ValueError(f"Займ с ID {payment_data['loan_id']} не найден")
        
        if loan.outstanding_amount < payment_data['payment_amount']:
            raise ValueError("Сумма платежа превышает остаток долга")
        
        # Добавляем платеж
        sql = '''
            INSERT INTO loan_payments 
            (loan_id, payment_date, payment_amount, interest_amount, 
             principal_amount, description)
            VALUES (?, ?, ?, ?, ?, ?)
        '''
        
        # Пока считаем весь платеж как основную сумму (без процентов)
        params = (
            payment_data['loan_id'],
            payment_data['payment_date'],
            payment_data['payment_amount'],
            payment_data.get('interest_amount', 0.0),
            payment_data.get('principal_amount', payment_data['payment_amount']),
            payment_data.get('description', '')
        )
        
        payment_id = self.executor.execute(sql, params)
        
        # Обновляем остаток долга
        new_outstanding = loan.outstanding_amount - payment_data['payment_amount']
        self.loan_repository.update_loan(payment_data['loan_id'], {
            'outstanding_amount': new_outstanding
        })
        
        # Обновляем статус займа если долг погашен
        if new_outstanding <= 0:
            self.loan_repository.update_loan(payment_data['loan_id'], {
                'status': 'paid'
            })
        
        # Создаем перевод между счетами
        if loan.loan_type == 'issued':
            # Возврат выданного займа: контрагент → наш счет
            from_account_id = loan.counterparty_account_id
            to_account_id = loan.account_id
            transfer_desc = f"Возврат займа: {loan.contact_name}"
        else:  # 'received'
            # Погашение полученного займа: наш счет → контрагент
            from_account_id = loan.account_id
            to_account_id = loan.counterparty_account_id
            transfer_desc = f"Погашение займа: {loan.contact_name}"
        
        if payment_data.get('description'):
            transfer_desc += f" - {payment_data['description']}"
        
        self.transfer_repository.add_transfer({
            'date': payment_data['payment_date'],
            'amount': payment_data['payment_amount'],
            'from_account_id': from_account_id,
            'to_account_id': to_account_id,
            'description': transfer_desc
        })
        
        logger.info(f"Добавлен платеж по займу ID: {payment_id}")
        return payment_id
    
    def delete_loan_payment_with_restore(self, payment_id: int) -> bool:
        """Удаление платежа по займу с восстановлением балансов."""
        try:
            # Получаем данные платежа
            sql = '''
                SELECT lp.*, l.loan_type, l.account_id, l.counterparty_account_id, 
                       l.contact_name, l.outstanding_amount
                FROM loan_payments lp
                JOIN loans l ON lp.loan_id = l.id
                WHERE lp.id = ?
            '''
            payment = self.executor.fetch_one(sql, (payment_id,))
            
            if not payment:
                logger.error(f"Платеж с ID {payment_id} не найден")
                return False
            
            # Восстанавливаем балансы через обратный перевод
            if payment['loan_type'] == 'issued':
                # Отменяем возврат выданного займа
                self.transfer_repository.add_transfer({
                    'date': payment['payment_date'],
                    'amount': payment['payment_amount'],
                    'from_account_id': payment['account_id'],
                    'to_account_id': payment['counterparty_account_id'],
                    'description': f"Отмена возврата займа: {payment['contact_name']}"
                })
            else:  # 'received'
                # Отменяем погашение полученного займа
                self.transfer_repository.add_transfer({
                    'date': payment['payment_date'],
                    'amount': payment['payment_amount'],
                    'from_account_id': payment['counterparty_account_id'],
                    'to_account_id': payment['account_id'],
                    'description': f"Отмена погашения займа: {payment['contact_name']}"
                })
            
            # Восстанавливаем остаток долга
            new_outstanding = payment['outstanding_amount'] + payment['payment_amount']
            self.loan_repository.update_loan(payment['loan_id'], {
                'outstanding_amount': new_outstanding
            })
            
            # Обновляем статус займа если нужно
            if new_outstanding > 0 and payment['outstanding_amount'] <= 0:
                self.loan_repository.update_loan(payment['loan_id'], {
                    'status': 'active'
                })
            
            # Удаляем платеж
            success = self.delete(payment_id)
            
            if success:
                logger.info(f"Удален платеж по займу ID: {payment_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Ошибка при удалении платежа по займу: {e}")
            return False