"""
Миграции базы данных: создание таблиц, индексов и системных данных.
"""

import logging
from typing import Dict, Any, List
from core.db.interfaces import QueryExecutor, TransactionManager

logger = logging.getLogger(__name__)


class MigrationManager:
    """Управление миграциями базы данных."""
    
    def __init__(self, executor: QueryExecutor, transaction_manager: TransactionManager):
        """
        Args:
            executor: Исполнитель SQL-запросов.
            transaction_manager: Менеджер транзакций.
        """
        self.executor = executor
        self.transaction = transaction_manager
    
    def migrate(self) -> None:
        """Выполнить все миграции (создание таблиц и индексов)."""
        logger.info("Запуск миграций базы данных...")
        
        with self.transaction.transaction() as cursor:
            # 1. Таблица счетов (accounts)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    initial_balance REAL DEFAULT 0.0,
                    current_balance REAL DEFAULT 0.0,
                    credit_limit REAL DEFAULT 0.0,
                    payment_due_day INTEGER DEFAULT 1,
                    min_payment_percent REAL DEFAULT 5.0,
                    last_payment_date TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    is_system BOOLEAN DEFAULT 0,
                    currency TEXT DEFAULT 'RUB',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 2. Таблица категорий (categories)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                    budget_amount_monthly REAL DEFAULT 0.0,
                    parent_id INTEGER DEFAULT NULL,
                    color TEXT DEFAULT '#3498db',
                    icon TEXT DEFAULT '',
                    is_system BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE CASCADE
                )
            ''')
            
            # 3. Таблица транзакций (transactions) - ОБНОВЛЕННАЯ!
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    type TEXT NOT NULL CHECK (type IN ('income', 'expense', 'refund', 'correct')),
                    category_id INTEGER,
                    description TEXT,
                    account_id INTEGER NOT NULL,
                    original_transaction_id INTEGER DEFAULT NULL,
                    quantity REAL DEFAULT 1.0,
                    unit_price REAL GENERATED ALWAYS AS (
                        CASE 
                            WHEN quantity != 0 THEN amount / quantity 
                            ELSE NULL 
                        END
                    ) STORED,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
                    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE RESTRICT,
                    FOREIGN KEY (original_transaction_id) REFERENCES transactions(id) ON DELETE SET NULL,
                    CHECK (
                        (type IN ('income', 'expense', 'refund') AND category_id IS NOT NULL) OR
                        (type = 'correct' AND category_id IS NULL)
                    ),
                    CHECK (
                        (type != 'refund') OR 
                        (type = 'refund' AND original_transaction_id IS NOT NULL)
                    )
                )
            ''')
            
            # 4. Таблица переводов (transfers)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transfers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    from_account_id INTEGER NOT NULL,
                    to_account_id INTEGER NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (from_account_id) REFERENCES accounts(id),
                    FOREIGN KEY (to_account_id) REFERENCES accounts(id),
                    CHECK (from_account_id != to_account_id)
                )
            ''')
            
            # 5. Таблица бюджетов (budgets)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS budgets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER NOT NULL,
                    month_year TEXT NOT NULL,
                    planned_amount REAL NOT NULL,
                    actual_amount REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(category_id, month_year),
                    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
                )
            ''')
            
            # 6. Таблица займов (loans)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS loans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    counterparty_account_id INTEGER NOT NULL,
                    contact_name TEXT NOT NULL,
                    loan_type TEXT NOT NULL CHECK (loan_type IN ('issued', 'received')),
                    loan_amount REAL NOT NULL,
                    outstanding_amount REAL NOT NULL,
                    interest_rate REAL DEFAULT 0.0,
                    issue_date TEXT NOT NULL,
                    due_date TEXT,
                    description TEXT,
                    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'paid', 'default')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (account_id) REFERENCES accounts (id) ON DELETE CASCADE,
                    FOREIGN KEY (counterparty_account_id) REFERENCES accounts (id) ON DELETE CASCADE
                )
            ''')
            
            # 7. Таблица платежей по займам (loan_payments)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS loan_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    loan_id INTEGER NOT NULL,
                    payment_date TEXT NOT NULL,
                    payment_amount REAL NOT NULL,
                    interest_amount REAL DEFAULT 0.0,
                    principal_amount REAL DEFAULT 0.0,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (loan_id) REFERENCES loans (id) ON DELETE CASCADE
                )
            ''')
            
            # Создание индексов
            self._create_indexes(cursor)
        
        # Создание системных данных
        self._create_system_data()
        
        logger.info("Миграции базы данных успешно выполнены")
    
    def _create_indexes(self, cursor) -> None:
        """Создание индексов для ускорения запросов."""
        indexes = [
            # Индексы для транзакций
            "CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_date_type ON transactions(date, type)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_original ON transactions(original_transaction_id)",
            
            # Индексы для категорий
            "CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories(parent_id)",
            "CREATE INDEX IF NOT EXISTS idx_categories_type ON categories(type)",
            
            # Индексы для счетов
            "CREATE INDEX IF NOT EXISTS idx_accounts_type ON accounts(type)",
            "CREATE INDEX IF NOT EXISTS idx_accounts_active ON accounts(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_accounts_system ON accounts(is_system)",
            
            # Индексы для переводов
            "CREATE INDEX IF NOT EXISTS idx_transfers_date ON transfers(date)",
            "CREATE INDEX IF NOT EXISTS idx_transfers_from_account ON transfers(from_account_id)",
            "CREATE INDEX IF NOT EXISTS idx_transfers_to_account ON transfers(to_account_id)",
            
            # Индексы для займов
            "CREATE INDEX IF NOT EXISTS idx_loans_account ON loans(account_id)",
            "CREATE INDEX IF NOT EXISTS idx_loans_status ON loans(status)",
            "CREATE INDEX IF NOT EXISTS idx_loans_due_date ON loans(due_date)",
            
            # Индексы для бюджетов
            "CREATE INDEX IF NOT EXISTS idx_budgets_month ON budgets(month_year)",
            "CREATE INDEX IF NOT EXISTS idx_budgets_category_month ON budgets(category_id, month_year)"
        ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
            except Exception as e:
                logger.warning(f"Не удалось создать индекс: {e}")
    
    def _create_system_data(self) -> None:
        """Создание системных данных (системная категория и т.д.)."""
        try:
            # Проверяем существование системной категории "Сверка баланса"
            category = self._get_category_by_name("Сверка баланса")
            if not category:
                self._add_category({
                    'name': 'Сверка баланса',
                    'type': 'expense',
                    'budget_amount_monthly': 0.0,
                    'is_system': True,
                    'color': '#FF0000',
                    'icon': '⚖️'
                })
                logger.info("Создана системная категория 'Сверка баланса'")
            
            # Проверяем наличие хотя бы одной категории дохода и расхода
            income_cats = self._get_categories(type='income')
            expense_cats = self._get_categories(type='expense')
            
            if not income_cats:
                self._add_category({
                    'name': 'Прочие доходы',
                    'type': 'income',
                    'budget_amount_monthly': 0.0,
                    'color': '#2ECC71',
                    'icon': '💰'
                })
            
            if not expense_cats:
                self._add_category({
                    'name': 'Прочие расходы',
                    'type': 'expense',
                    'budget_amount_monthly': 0.0,
                    'color': '#E74C3C',
                    'icon': '🛒'
                })
                
        except Exception as e:
            logger.error(f"Ошибка при создании системных данных: {e}")
    
    # Вспомогательные методы для работы с категориями (используются только внутри миграций)
    def _get_category_by_name(self, name: str) -> Dict[str, Any]:
        """Получить категорию по имени (внутренний метод)."""
        sql = "SELECT * FROM categories WHERE name = ?"
        return self.executor.fetch_one(sql, (name,))
    
    def _get_categories(self, type: str = None) -> List[Dict[str, Any]]:
        """Получить категории (внутренний метод)."""
        if type:
            sql = "SELECT * FROM categories WHERE type = ?"
            return self.executor.fetch_all(sql, (type,))
        else:
            sql = "SELECT * FROM categories"
            return self.executor.fetch_all(sql)
    
    def _add_category(self, category_data: Dict[str, Any]) -> int:
        """Добавить категорию (внутренний метод)."""
        sql = '''
            INSERT INTO categories 
            (name, type, budget_amount_monthly, parent_id, color, icon, is_system)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        '''
        params = (
            category_data['name'],
            category_data['type'],
            category_data.get('budget_amount_monthly', 0.0),
            category_data.get('parent_id'),
            category_data.get('color', '#3498db'),
            category_data.get('icon', ''),
            int(category_data.get('is_system', False))
        )
        return self.executor.execute(sql, params)
    
    def get_database_info(self) -> Dict[str, Any]:
        """Получить информацию о базе данных."""
        tables = ['accounts', 'categories', 'transactions', 'transfers', 'budgets', 'loans', 'loan_payments']
        info = {}
        
        for table in tables:
            count = self.executor.fetch_value(f"SELECT COUNT(*) FROM {table}")
            info[table] = count or 0
        
        return info