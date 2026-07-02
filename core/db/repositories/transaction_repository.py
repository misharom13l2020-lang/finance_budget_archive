"""
Репозиторий для работы с транзакциями (transactions).
Работает с dataclass-моделями вместо словарей.
"""

import logging
from typing import List, Dict, Any, Optional
from core.db.repositories.base import BaseRepository
from core.db.models import Transaction
from core.db.interfaces import QueryExecutor, TransactionManager
from core.db.repositories.account_repository import AccountRepository

logger = logging.getLogger(__name__)


class TransactionRepository(BaseRepository[Transaction]):
    """Репозиторий для работы с транзакциями."""
    
    def __init__(self, executor: QueryExecutor, account_repository: AccountRepository):
        """
        Args:
            executor: Исполнитель SQL-запросов.
            account_repository: Репозиторий счетов для обновления балансов.
        """
        super().__init__(executor)
        self.account_repository = account_repository
    
    def _get_table_name(self) -> str:
        return "transactions"
    
    def _get_model_class(self) -> type[Transaction]:
        return Transaction
    
    def get_transactions(self, filters: Dict[str, Any] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Получение транзакций с фильтрами."""
        sql = '''
            SELECT 
                t.id, t.date, t.amount, t.type, t.description,
                t.account_id, t.quantity, t.unit_price,
                t.created_at, t.updated_at,
                t.original_transaction_id,
                ot.date as original_date,
                ot.amount as original_amount,
                ot.type as original_type,
                c.id as category_id, c.name as category_name,
                c.color as category_color, c.icon as category_icon,
                a.name as account_name, a.type as account_type,
                a.currency as account_currency
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            JOIN accounts a ON t.account_id = a.id
            LEFT JOIN transactions ot ON t.original_transaction_id = ot.id
            WHERE 1=1
        '''
        
        params = []
        
        if filters:
            # Фильтр по дате
            if 'date_from' in filters and filters['date_from']:
                sql += " AND t.date >= ?"
                params.append(filters['date_from'])
            
            if 'date_to' in filters and filters['date_to']:
                sql += " AND t.date <= ?"
                params.append(filters['date_to'])
            
            # Фильтр по типу
            if 'type' in filters and filters['type']:
                sql += " AND t.type = ?"
                params.append(filters['type'])
            
            # Фильтр по категории
            if 'category_id' in filters and filters['category_id']:
                sql += " AND t.category_id = ?"
                params.append(filters['category_id'])
            
            # Фильтр по счету
            if 'account_id' in filters and filters['account_id']:
                sql += " AND t.account_id = ?"
                params.append(filters['account_id'])
            
            # Фильтр по описанию
            if 'description_text' in filters and filters['description_text']:
                sql += " AND LOWER(t.description) LIKE LOWER(?)"
                params.append(f'%{filters["description_text"]}%')
            
            # Исключаем корректировки из обычных запросов
            if filters.get('exclude_corrections', True):
                sql += " AND t.type != 'correct'"
        
        sql += " ORDER BY t.date DESC, t.id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        return self.executor.fetch_all(sql, tuple(params))
    
    def add_transaction(self, transaction_data: Dict[str, Any]) -> int:
        """Добавление новой транзакции с обновлением баланса счета."""
        required_fields = ['date', 'amount', 'type', 'account_id']
        for field in required_fields:
            if field not in transaction_data:
                raise ValueError(f"Отсутствует обязательное поле: {field}")
        
        # Проверяем тип транзакции
        if transaction_data['type'] not in ['income', 'expense', 'refund', 'correct']:
            raise ValueError(f"Некорректный тип транзакции: {transaction_data['type']}")
        
        # Для возвратов проверяем original_transaction_id
        if transaction_data['type'] == 'refund':
            if 'original_transaction_id' not in transaction_data:
                raise ValueError("Для возврата обязателен original_transaction_id")
            original_transaction_id = transaction_data.get('original_transaction_id')
        else:
            original_transaction_id = None
        
        # Проверяем категорию для income/expense/refund
        if transaction_data['type'] in ['income', 'expense', 'refund'] and 'category_id' not in transaction_data:
            raise ValueError(f"Для типа '{transaction_data['type']}' обязательна категория")
        
        # Для корректировок категория должна быть NULL
        if transaction_data['type'] == 'correct':
            transaction_data['category_id'] = None
        
        # Добавляем транзакцию
        sql = '''
            INSERT INTO transactions 
            (date, amount, type, category_id, description, 
             account_id, quantity, original_transaction_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        params = (
            transaction_data['date'],
            transaction_data['amount'],
            transaction_data['type'],
            transaction_data.get('category_id'),
            transaction_data.get('description', ''),
            transaction_data['account_id'],
            transaction_data.get('quantity', 1.0),
            original_transaction_id
        )
        
        transaction_id = self.executor.execute(sql, params)
        
        # Определяем изменение баланса в зависимости от типа транзакции
        amount = transaction_data['amount']
        transaction_type = transaction_data['type']
        
        if transaction_type == 'income':
            balance_change = amount  # доход увеличивает баланс
        elif transaction_type == 'expense':
            balance_change = -amount  # расход уменьшает баланс
        elif transaction_type == 'refund':
            # Для возврата знак уже должен быть противоположным оригиналу
            # (обрабатывается в add_refund). Здесь просто применяем как есть.
            balance_change = amount
        elif transaction_type == 'correct':
            # Корректировка может быть как положительной, так и отрицательной
            balance_change = amount
        else:
            raise ValueError(f"Неизвестный тип транзакции: {transaction_type}")
        
        # Обновляем баланс счета
        self.account_repository.update_account_balance(
            transaction_data['account_id'],
            balance_change
        )
        
        logger.info(f"Добавлена транзакция ID: {transaction_id}")
        return transaction_id
    
    def add_refund(self, original_transaction_id: int,
                   date: str = None,
                   amount: float = None,
                   description: str = "") -> int:
        """Упрощенное создание возврата."""
        # Получаем оригинальную транзакцию
        original = self.get_by_id(original_transaction_id)
        if not original:
            raise ValueError(f"Транзакция с ID {original_transaction_id} не найдена")
        
        # Определяем дату - по умолчанию сегодня
        if date is None:
            from datetime import datetime
            date = datetime.now().strftime('%Y-%m-%d')
        
        # Определяем сумму возврата: компенсируем изменение баланса от оригинальной транзакции
        if amount is None:
            if original.type == 'expense':
                # Расход уменьшил баланс, возврат должен увеличить баланс (положительная сумма)
                amount = original.amount
            elif original.type == 'income':
                # Доход увеличил баланс, возврат должен уменьшить баланс (отрицательная сумма)
                amount = -original.amount
            else:
                # Для других типов (refund, correct) используем противоположный знак
                amount = -original.amount
        
        # Формируем описание
        if not description:
            original_desc = original.description or ''
            if original_desc:
                description = f"Возврат: {original_desc}"
            else:
                description = f"Возврат транзакции #{original_transaction_id}"
        
        # Создаем возврат
        refund_data = {
            'date': date,
            'amount': amount,
            'type': 'refund',
            'original_transaction_id': original_transaction_id,
            'category_id': original.category_id,
            'account_id': original.account_id,
            'description': description
        }
        
        return self.add_transaction(refund_data)
    
    def reconcile_account(self, account_id: int, actual_balance: float,
                         description: str = "") -> int:
        """Создание операции сверки баланса (корректировка)."""
        account = self.account_repository.get_by_id(account_id)
        if not account:
            raise ValueError(f"Счет с ID {account_id} не найден")
        
        current_balance = account.current_balance
        difference = actual_balance - current_balance
        
        if abs(difference) < 0.01:  # игнорируем мелкие различия
            logger.info(f"Баланс счета {account_id} уже правильный")
            return 0
        
        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%d')
        
        if not description:
            direction = "увеличение" if difference > 0 else "уменьшение"
            description = f"Корректировка баланса ({direction}): {difference:+.2f} {account.currency or 'RUB'}"
        
        # Создаем транзакцию типа 'correct' без категории
        transaction_id = self.add_transaction({
            'date': today,
            'amount': difference,
            'type': 'correct',
            'account_id': account_id,
            'description': description,
            'category_id': None
        })
        
        logger.info(f"Создана корректировка баланса для счета {account_id}: {difference:+.2f}")
        return transaction_id
    
    def get_account_corrections(self, account_id: int, date_from: str = None, 
                               date_to: str = None) -> List[Dict[str, Any]]:
        """Получение корректировок баланса для счета."""
        sql = '''
            SELECT id, date, amount, description, created_at
            FROM transactions
            WHERE account_id = ? AND type = 'correct'
        '''
        
        params = [account_id]
        
        if date_from:
            sql += " AND date >= ?"
            params.append(date_from)
        
        if date_to:
            sql += " AND date <= ?"
            params.append(date_to)
        
        sql += " ORDER BY date DESC"
        return self.executor.fetch_all(sql, tuple(params))
    
    def get_refunds_for_transaction(self, original_transaction_id: int) -> List[Dict[str, Any]]:
        """Получение всех возвратов для оригинальной транзакции."""
        sql = '''
            SELECT 
                t.id, t.date, t.amount, t.description,
                t.created_at, t.updated_at
            FROM transactions t
            WHERE t.original_transaction_id = ?
              AND t.type = 'refund'
            ORDER BY t.date ASC
        '''
        return self.executor.fetch_all(sql, (original_transaction_id,))
    
    def delete_transaction_with_checks(self, transaction_id: int) -> bool:
        """Удаление транзакции с проверкой связанных возвратов."""
        # Получаем транзакцию
        transaction = self.get_by_id(transaction_id)
        if not transaction:
            logger.error(f"Транзакция с ID {transaction_id} не найдена")
            return False
        
        # Проверяем, есть ли возвраты для этой транзакции
        if transaction.type != 'refund':
            refunds = self.get_refunds_for_transaction(transaction_id)
            if refunds:
                logger.error(f"Нельзя удалить транзакцию с возвратами. Сначала удалите возвраты.")
                return False
        
        # Возвращаем баланс
        self.account_repository.update_account_balance(
            transaction.account_id,
            -transaction.amount
        )
        
        # Удаляем транзакцию
        success = self.delete(transaction_id)
        
        if success:
            logger.info(f"Удалена транзакция ID: {transaction_id}")
        
        return success