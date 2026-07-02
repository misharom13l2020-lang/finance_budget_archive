"""
Фасад для удобной работы с базой данных.
Объединяет все компоненты новой модульной архитектуры.
"""

from core.db.connection import SQLiteConnection
from core.db.query_executor import SQLiteQueryExecutor
from core.db.transaction_manager import SQLiteTransactionManager
from core.db.migrations import MigrationManager
from core.db.repositories.account_repository import AccountRepository
from core.db.repositories.category_repository import CategoryRepository
from core.db.repositories.transaction_repository import TransactionRepository
from core.db.repositories.transfer_repository import TransferRepository
from core.db.repositories.budget_repository import BudgetRepository
from core.db.repositories.loan_repository import LoanRepository
from core.db.repositories.loan_payment_repository import LoanPaymentRepository


class Database:
    """Фасад для удобной работы с БД."""
    
    def __init__(self, db_path: str = 'budget.db'):
        """
        Args:
            db_path: Путь к файлу базы данных SQLite.
        """
        self.db_path = db_path
        
        # Инициализация компонентов
        self.connection = SQLiteConnection(db_path)
        self.connection.connect()
        
        self.executor = SQLiteQueryExecutor(self.connection)
        self.transaction = SQLiteTransactionManager(self.connection)
        
        # Миграции
        self.migrations = MigrationManager(self.executor, self.transaction)
        self.migrations.migrate()
        
        # Репозитории
        self.accounts = AccountRepository(self.executor)
        self.categories = CategoryRepository(self.executor)
        self.transactions = TransactionRepository(self.executor, self.accounts)
        self.transfers = TransferRepository(self.executor, self.accounts)
        self.budgets = BudgetRepository(self.executor)
        self.loans = LoanRepository(self.executor, self.accounts)
        self.loan_payments = LoanPaymentRepository(self.executor, self.loans, self.transfers)
    
    def close(self):
        """Закрыть соединение с базой данных."""
        self.connection.disconnect()
    
    def __enter__(self):
        """Поддержка контекстного менеджера."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Автоматическое закрытие соединения при выходе из контекста."""
        self.close()
    
    def get_database_info(self):
        """Получить информацию о базе данных."""
        return self.migrations.get_database_info()


# Экспорт публичных классов для удобного импорта
__all__ = [
    'SQLiteConnection',
    'SQLiteQueryExecutor',
    'SQLiteTransactionManager',
    'MigrationManager',
    'AccountRepository',
    'CategoryRepository',
    'TransactionRepository',
    'TransferRepository',
    'BudgetRepository',
    'LoanRepository',
    'LoanPaymentRepository',
    'Database'
]