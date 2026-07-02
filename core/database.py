# core/database.py
"""
DatabaseManager для PySide6 Budget App
Версия 2.0 - Полная переработка с dict API
"""

import sqlite3
import logging
import threading
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from contextlib import contextmanager
from PySide6.QtCore import QObject, Signal, QMutex
from config import get_db_path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class DatabaseManager(QObject):
    """
    Основной менеджер базы данных с поддержкой PySide6.
    Все методы возвращают dict или list[dict].
    """
    
    # ========== СИГНАЛЫ PYQT ==========
    data_updated = Signal(str)  # Тип обновленных данных: 'accounts', 'transactions', etc.
    progress_signal = Signal(str, int)  # Сообщение, процент
    error_signal = Signal(str)  # Сообщение об ошибке
    
    # ========== SINGLETON PATTERN ==========
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls, db_path: str = None) -> 'DatabaseManager':
        """Получение единственного экземпляра DatabaseManager"""
        with cls._lock:
            if cls._instance is None:
                if db_path is None:
                    db_path = get_db_path()  # ← Используем "умный" путь по умолчанию
                cls._instance = cls(db_path)
            return cls._instance

    
    def __init__(self, db_path: str = 'budget.db'):
        super().__init__()
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Thread-safe подключения
        self._thread_local = threading.local()
        self.mutex = QMutex()
        
        # Кэширование
        self._cache = {
            'accounts': {'data': None, 'timestamp': None},
            'categories': {'data': None, 'timestamp': None},
            'credit_cards': {'data': None, 'timestamp': None}
        }
        self._cache_ttl = 60  # секунды
        
        # Инициализация БД
        self._init_database()
        self._create_system_data()
        
        self.logger.info(f"DatabaseManager инициализирован с БД: {db_path}")
    
    # ========== ПОДКЛЮЧЕНИЕ К БД ==========
    def _get_connection(self) -> sqlite3.Connection:
        """Получение соединения для текущего потока"""
        if not hasattr(self._thread_local, 'connection'):
            conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            conn.row_factory = sqlite3.Row  # Для преобразования в dict
            conn.execute("PRAGMA foreign_keys = ON")
            self._thread_local.connection = conn
            self.logger.debug("Создано новое соединение с БД")
        return self._thread_local.connection
    
    @contextmanager
    def transaction(self):
        """
        Контекстный менеджер для транзакций.
        Автоматически делает commit/rollback.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            yield cursor
            conn.commit()
            self.logger.debug("Транзакция успешно завершена")
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Ошибка в транзакции: {e}")
            self.error_signal.emit(f"Ошибка БД: {e}")
            raise
    
    def _execute_query(self, sql: str, params: tuple = (), 
                      fetch: str = None) -> Union[bool, Dict, List[Dict]]:
        """
        Универсальный метод выполнения SQL запросов.
        
        Args:
            sql: SQL запрос
            params: Параметры запроса
            fetch: None, 'one', 'all', 'row'
        
        Returns:
            - Если fetch=None: True/False или lastrowid
            - Если fetch='one': один результат как dict
            - Если fetch='all': список dict
            - Если fetch='row': одна строка как dict или None
        """
        self.mutex.lock()
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            self.logger.debug(f"Выполнение SQL: {sql[:100]}...")
            if params:
                self.logger.debug(f"Параметры: {params}")
            
            cursor.execute(sql, params)
            
            if fetch == 'one':
                result = cursor.fetchone()
                return dict(result) if result else {}
            elif fetch == 'all':
                results = cursor.fetchall()
                return [dict(row) for row in results]
            elif fetch == 'row':
                result = cursor.fetchone()
                return dict(result) if result else None
            else:
                conn.commit()
                # Возвращаем ID вставленной записи или True
                return cursor.lastrowid if cursor.lastrowid else True
                
        except sqlite3.Error as e:
            self.logger.error(f"Ошибка SQL: {e}")
            self.logger.error(f"Запрос: {sql}")
            self.logger.error(f"Параметры: {params}")
            self.error_signal.emit(f"Ошибка БД: {e}")
            raise
        finally:
            self.mutex.unlock()
    
    # ========== ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ==========
    def _init_database(self):
        """Создание всех таблиц и индексов"""
        self.logger.info("Инициализация структуры базы данных...")
        
        with self.transaction() as cursor:
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
            
            # # Создание системного счёта, если отсутствует
            # cursor.execute('''
            #     INSERT OR IGNORE INTO accounts (name, type, initial_balance, current_balance, is_system, currency)
            #     VALUES ('Основной счёт', 'cash', 0.0, 0.0, 1, 'RUB')
            # ''')
            
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
                    original_transaction_id INTEGER DEFAULT NULL,  -- НОВОЕ ПОЛЕ!
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
            
            # 5. Таблица бюджетов (budgets) - НОВАЯ
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
            
            # Создание индексов для производительности
            self._create_indexes(cursor)
        
        self.logger.info("Структура базы данных создана успешно")
    
    def _create_indexes(self, cursor):
        """Создание индексов для ускорения запросов"""
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
            except sqlite3.Error as e:
                self.logger.warning(f"Не удалось создать индекс: {e}")
    
    def _create_system_data(self):
        """Создание системных данных (системная категория и т.д.)"""
        try:
            # Проверяем существование системной категории "Сверка баланса"
            category = self.get_category_by_name("Сверка баланса")
            if not category:
                self.add_category({
                    'name': 'Сверка баланса',
                    'type': 'expense',
                    'budget_amount_monthly': 0.0,
                    'is_system': True,
                    'color': '#FF0000',
                    'icon': '⚖️'
                })
                self.logger.info("Создана системная категория 'Сверка баланса'")
            
            # Проверяем наличие хотя бы одной категории дохода и расхода
            income_cats = self.get_categories(type='income')
            expense_cats = self.get_categories(type='expense')
            
            if not income_cats:
                self.add_category({
                    'name': 'Прочие доходы',
                    'type': 'income',
                    'budget_amount_monthly': 0.0,
                    'color': '#2ECC71',
                    'icon': '💰'
                })
            
            if not expense_cats:
                self.add_category({
                    'name': 'Прочие расходы',
                    'type': 'expense',
                    'budget_amount_monthly': 0.0,
                    'color': '#E74C3C',
                    'icon': '🛒'
                })
                
        except Exception as e:
            self.logger.error(f"Ошибка при создании системных данных: {e}")
    
    # ========== КЭШИРОВАНИЕ ==========
    def _get_cached(self, cache_key: str):
        """Получение данных из кэша"""
        cache_item = self._cache.get(cache_key)
        if cache_item and cache_item['data']:
            if time.time() - cache_item['timestamp'] < self._cache_ttl:
                self.logger.debug(f"Данные из кэша: {cache_key}")
                return cache_item['data']
        return None
    
    def _set_cached(self, cache_key: str, data):
        """Сохранение данных в кэш"""
        self._cache[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }
        self.logger.debug(f"Данные сохранены в кэш: {cache_key}")
    
    def invalidate_cache(self, cache_key: str = None):
        """Очистка кэша"""
        if cache_key:
            if cache_key in self._cache:
                self._cache[cache_key] = {'data': None, 'timestamp': None}
                self.logger.debug(f"Кэш очищен: {cache_key}")
        else:
            for key in self._cache:
                self._cache[key] = {'data': None, 'timestamp': None}
            self.logger.debug("Весь кэш очищен")
    
    # ========== МЕТОДЫ ДЛЯ СЧЕТОВ (ACCOUNTS) ==========
    def get_accounts(self, active_only: bool = True, include_system: bool = False) -> List[Dict]:
        """Получение всех счетов - БЕЗ КЭШИРОВАНИЯ"""
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
        
        # ВОЗВРАЩАЕМ СРАЗУ РЕЗУЛЬТАТ, БЕЗ КЭША
        return self._execute_query(sql, tuple(params), fetch='all')

    # Удаляем метод get_accounts_direct() так как он больше не нужен
    # Или оставляем как alias для совместимости:
    def get_accounts_direct(self, active_only: bool = True, include_system: bool = False) -> List[Dict]:
        """Алиас для get_accounts() для обратной совместимости"""
        return self.get_accounts(active_only, include_system)
        
    def get_accounts_direct(self, active_only: bool = True, include_system: bool = False) -> List[Dict]:
        """Получение всех счетов напрямую из БД, минуя кэш"""
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
        
        return self._execute_query(sql, tuple(params), fetch='all')
    
    def get_account_by_id(self, account_id: int) -> Optional[Dict]:
        """Получение счета по ID"""
        sql = '''
            SELECT id, name, type, initial_balance, current_balance,
                   credit_limit, payment_due_day, min_payment_percent,
                   last_payment_date, created_at, is_active, is_system, currency
            FROM accounts
            WHERE id = ?
        '''
        return self._execute_query(sql, (account_id,), fetch='row')
    
    def get_account_by_name(self, name: str) -> Optional[Dict]:
        """Получение счета по имени"""
        sql = '''
            SELECT id, name, type, initial_balance, current_balance,
                   credit_limit, payment_due_day, min_payment_percent,
                   last_payment_date, created_at, is_active, is_system, currency
            FROM accounts
            WHERE name = ?
        '''
        return self._execute_query(sql, (name,), fetch='row')
    
    def add_account(self, account_data: Dict) -> int:
        """Добавление нового счета"""
        required_fields = ['name', 'type']
        for field in required_fields:
            if field not in account_data:
                raise ValueError(f"Отсутствует обязательное поле: {field}")
        
        sql = '''
            INSERT INTO accounts 
            (name, type, initial_balance, current_balance, credit_limit,
             payment_due_day, min_payment_percent, last_payment_date,
             is_active, is_system, currency)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        params = (
            account_data['name'],
            account_data['type'],
            account_data.get('initial_balance', 0.0),
            account_data.get('current_balance', account_data.get('initial_balance', 0.0)),
            account_data.get('credit_limit', 0.0),
            account_data.get('payment_due_day', 1),
            account_data.get('min_payment_percent', 5.0),
            account_data.get('last_payment_date'),
            int(account_data.get('is_active', True)),
            int(account_data.get('is_system', False)),
            account_data.get('currency', 'RUB')
        )
        
        account_id = self._execute_query(sql, params)
        if account_id:
            self.invalidate_cache('accounts')
            self.data_updated.emit('accounts')
            self.logger.info(f"Добавлен новый счет: {account_data['name']} (ID: {account_id})")
        
        return account_id
    
    def update_account(self, account_id: int, account_data: Dict) -> bool:
        """Обновление данных счета"""
        if not account_data:
            return False
        
        fields = []
        params = []
        
        # Список разрешенных полей для обновления
        allowed_fields = [
            'name', 'type', 'initial_balance', 'current_balance',
            'credit_limit', 'payment_due_day', 'min_payment_percent',
            'last_payment_date', 'is_active', 'is_system', 'currency'
        ]
        
        for field, value in account_data.items():
            if field in allowed_fields:
                fields.append(f"{field} = ?")
                params.append(value)
        
        if not fields:
            return False
        
        params.append(account_id)
        sql = f"UPDATE accounts SET {', '.join(fields)} WHERE id = ?"
        
        success = self._execute_query(sql, tuple(params))
        if success:
            self.invalidate_cache('accounts')
            self.data_updated.emit('accounts')
            self.logger.info(f"Обновлен счет ID: {account_id}")
        
        return bool(success)
    
    def update_account_balance(self, account_id: int, amount_change: float) -> bool:
        """Обновление баланса счета"""
        try:
            amount_change = float(amount_change)
        except (ValueError, TypeError):
            self.logger.error(f"Некорректное значение изменения баланса: {amount_change}")
            return False
        
        sql = "UPDATE accounts SET current_balance = current_balance + ? WHERE id = ?"
        success = self._execute_query(sql, (amount_change, account_id))
        
        if success:
            self.invalidate_cache('accounts')
            self.data_updated.emit('accounts')
            self.logger.debug(f"Обновлен баланс счета {account_id} на {amount_change}")
        
        return bool(success)
    
    def delete_account(self, account_id: int) -> Dict:
        """
        Удаление счета с проверкой связанных операций.
        Возвращает dict с результатом операции.
        """
        try:
            # Проверяем существование счета
            account = self.get_account_by_id(account_id)
            if not account:
                return {
                    'success': False,
                    'message': f"Счет с ID {account_id} не найден"
                }
            
            account_name = account['name']
            
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
                    count = self._execute_query(query, (account_id, account_id), fetch='one')['COUNT(*)']
                else:
                    count = self._execute_query(query, (account_id,), fetch='one')['COUNT(*)']
                
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
            sql = "DELETE FROM accounts WHERE id = ?"
            success = self._execute_query(sql, (account_id,))
            
            if success:
                self.invalidate_cache('accounts')
                self.data_updated.emit('accounts')
                self.logger.info(f"Удален счет: {account_name} (ID: {account_id})")
                
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
            self.logger.error(f"Ошибка при удалении счета: {e}")
            return {
                'success': False,
                'message': f"Ошибка при удалении счета: {str(e)}"
            }
    
    def get_credit_cards(self) -> List[Dict]:
        """Получение всех кредитных карт"""
        cache_key = 'credit_cards'
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        sql = '''
            SELECT id, name, type, initial_balance, current_balance,
                   credit_limit, payment_due_day, min_payment_percent,
                   last_payment_date, created_at, is_active, currency
            FROM accounts
            WHERE type = 'Credit Card' AND is_active = 1
            ORDER BY name
        '''
        
        cards = self._execute_query(sql, fetch='all')
        self._set_cached(cache_key, cards)
        return cards
    
    def get_counterparty_accounts(self) -> List[Dict]:
        """Получение всех счетов контрагентов"""
        sql = '''
            SELECT id, name, type, current_balance, created_at, is_active
            FROM accounts
            WHERE type = 'Counterparty'
            ORDER BY name
        '''
        return self._execute_query(sql, fetch='all')
    
    def create_counterparty_account(self, contact_name: str) -> int:
        """Создание или получение счета контрагента"""
        account_name = f"Контрагент: {contact_name}"
        
        # Проверяем существование
        existing = self.get_account_by_name(account_name)
        if existing:
            return existing['id']
        
        # Создаем новый
        account_id = self.add_account({
            'name': account_name,
            'type': 'Counterparty',
            'initial_balance': 0.0,
            'is_system': True,  # Системный счет
            'is_active': True
        })
        
        self.logger.info(f"Создан счет контрагента: {account_name} (ID: {account_id})")
        return account_id
    
    # ========== МЕТОДЫ ДЛЯ КАТЕГОРИЙ (CATEGORIES) ==========
    def get_categories(self, type: str = None, include_system: bool = False, 
                      include_subcategories: bool = True) -> List[Dict]:
        """Получение всех категорий"""
        cache_key = f"categories_{type}_{include_system}_{include_subcategories}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        sql = '''
            SELECT id, name, type, budget_amount_monthly, 
                   parent_id, color, icon, is_system, created_at
            FROM categories
            WHERE 1=1
        '''
        
        params = []
        if type:
            sql += " AND type = ?"
            params.append(type)
        
        if not include_system:
            sql += " AND is_system = 0"
        
        if not include_subcategories:
            sql += " AND parent_id IS NULL"
        
        sql += " ORDER BY type, parent_id, name"
        
        categories = self._execute_query(sql, tuple(params), fetch='all')
        self._set_cached(cache_key, categories)
        return categories
    
    def get_category_by_id(self, category_id: int) -> Optional[Dict]:
        """Получение категории по ID"""
        sql = '''
            SELECT id, name, type, budget_amount_monthly, 
                   parent_id, color, icon, is_system, created_at
            FROM categories
            WHERE id = ?
        '''
        return self._execute_query(sql, (category_id,), fetch='row')
    
    def get_category_by_name(self, name: str) -> Optional[Dict]:
        """Получение категории по имени"""
        sql = '''
            SELECT id, name, type, budget_amount_monthly, 
                   parent_id, color, icon, is_system, created_at
            FROM categories
            WHERE name = ?
        '''
        return self._execute_query(sql, (name,), fetch='row')
    
    def add_category(self, category_data: Dict) -> int:
        """Добавление новой категории"""
        required_fields = ['name', 'type']
        for field in required_fields:
            if field not in category_data:
                raise ValueError(f"Отсутствует обязательное поле: {field}")
        
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
        
        category_id = self._execute_query(sql, params)
        if category_id:
            self.invalidate_cache('categories')
            self.data_updated.emit('categories')
            self.logger.info(f"Добавлена новая категория: {category_data['name']} (ID: {category_id})")
        
        return category_id
    
    def update_category(self, category_id: int, category_data: Dict) -> bool:
        """Обновление категории"""
        if not category_data:
            return False
        
        fields = []
        params = []
        
        allowed_fields = [
            'name', 'type', 'budget_amount_monthly', 'parent_id',
            'color', 'icon', 'is_system'
        ]
        
        for field, value in category_data.items():
            if field in allowed_fields:
                fields.append(f"{field} = ?")
                params.append(value)
        
        if not fields:
            return False
        
        params.append(category_id)
        sql = f"UPDATE categories SET {', '.join(fields)} WHERE id = ?"
        
        success = self._execute_query(sql, tuple(params))
        if success:
            self.invalidate_cache('categories')
            self.data_updated.emit('categories')
            self.logger.info(f"Обновлена категория ID: {category_id}")
        
        return bool(success)
    
    def delete_category(self, category_id: int, delete_children: bool = False) -> Dict:
        """
        Удаление категории.
        Если delete_children=True, удаляет все подкатегории.
        """
        try:
            category = self.get_category_by_id(category_id)
            if not category:
                return {
                    'success': False,
                    'message': f"Категория с ID {category_id} не найдена"
                }
            
            if category['is_system']:
                return {
                    'success': False,
                    'message': "Нельзя удалить системную категорию"
                }
            
            category_name = category['name']
            
            if delete_children:
                # Удаляем категорию и все подкатегории
                sql = '''
                    WITH RECURSIVE category_tree AS (
                        SELECT id FROM categories WHERE id = ?
                        UNION ALL
                        SELECT c.id FROM categories c
                        JOIN category_tree ct ON c.parent_id = ct.id
                    )
                    DELETE FROM categories WHERE id IN (SELECT id FROM category_tree)
                '''
                self._execute_query(sql, (category_id,))
                
                # Обнуляем category_id в транзакциях
                sql = '''
                    WITH RECURSIVE category_tree AS (
                        SELECT id FROM categories WHERE id = ?
                        UNION ALL
                        SELECT c.id FROM categories c
                        JOIN category_tree ct ON c.parent_id = ct.id
                    )
                    UPDATE transactions 
                    SET category_id = NULL 
                    WHERE category_id IN (SELECT id FROM category_tree)
                '''
                self._execute_query(sql, (category_id,))
                
                self.logger.info(f"Удалена категория с подкатегориями: {category_name}")
                
            else:
                # Делаем подкатегории основными
                sql = "UPDATE categories SET parent_id = NULL WHERE parent_id = ?"
                self._execute_query(sql, (category_id,))
                
                # Обнуляем category_id в транзакциях
                sql = "UPDATE transactions SET category_id = NULL WHERE category_id = ?"
                self._execute_query(sql, (category_id,))
                
                # Удаляем саму категорию
                sql = "DELETE FROM categories WHERE id = ?"
                self._execute_query(sql, (category_id,))
                
                self.logger.info(f"Удалена категория: {category_name}")
            
            self.invalidate_cache('categories')
            self.data_updated.emit('categories')
            
            return {
                'success': True,
                'message': f"Категория '{category_name}' успешно удалена"
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка при удалении категории: {e}")
            return {
                'success': False,
                'message': f"Ошибка при удалении категории: {str(e)}"
            }
    
    def get_category_hierarchy(self, type: str = None) -> List[Dict]:
        """Получение иерархии категорий"""
        sql = '''
            WITH RECURSIVE category_hierarchy AS (
                SELECT 
                    id,
                    name,
                    type,
                    budget_amount_monthly,
                    parent_id,
                    color,
                    icon,
                    is_system,
                    created_at,
                    0 as level,
                    name as path
                FROM categories
                WHERE parent_id IS NULL
                
                UNION ALL
                
                SELECT 
                    c.id,
                    c.name,
                    c.type,
                    c.budget_amount_monthly,
                    c.parent_id,
                    c.color,
                    c.icon,
                    c.is_system,
                    c.created_at,
                    ch.level + 1 as level,
                    ch.path || ' > ' || c.name as path
                FROM categories c
                JOIN category_hierarchy ch ON c.parent_id = ch.id
            )
            SELECT 
                id,
                name,
                type,
                budget_amount_monthly,
                parent_id,
                color,
                icon,
                is_system,
                created_at,
                level,
                path
            FROM category_hierarchy
            WHERE 1=1
        '''
        
        params = []
        if type:
            sql += " AND type = ?"
            params.append(type)
        
        sql += " ORDER BY type, level, path"
        
        return self._execute_query(sql, tuple(params), fetch='all')
    
    def get_categories_for_display(self, type: str = None) -> List[Dict]:
        """Получение категорий для отображения в UI (с отступами)"""
        hierarchy = self.get_category_hierarchy(type)
        
        result = []
        for cat in hierarchy:
            indent = "    " * cat['level']
            result.append({
                'id': cat['id'],
                'display_name': f"{indent}{cat['name']}",
                'name': cat['name'],
                'type': cat['type'],
                'level': cat['level'],
                'color': cat['color'],
                'icon': cat['icon']
            })
        
        return result
    
    # ========== МЕТОДЫ ДЛЯ ТРАНЗАКЦИЙ (TRANSACTIONS) ==========
    def get_transactions(self, filters: Dict = None, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Получение транзакций с фильтрами"""
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
        
        print(f"DEBUG database.get_transactions SQL WHERE part: {sql.split('WHERE')[1] if 'WHERE' in sql else 'NO WHERE'}")
        print(f"DEBUG database.get_transactions params: {params}")
        
        return self._execute_query(sql, tuple(params), fetch='all')
    
    def get_transaction_by_id(self, transaction_id: int) -> Optional[Dict]:
        """Получение транзакции по ID"""
        sql = '''
            SELECT 
                t.id, t.date, t.amount, t.type, t.description,
                t.account_id, t.quantity, t.unit_price,
                t.created_at, t.updated_at,
                t.original_transaction_id,  -- НОВОЕ ПОЛЕ
                ot.date as original_date,
                ot.amount as original_amount,
                ot.type as original_type,
                ot.description as original_description,
                c.id as category_id, c.name as category_name,
                c.color as category_color, c.icon as category_icon,
                a.name as account_name, a.type as account_type,
                a.currency as account_currency
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            JOIN accounts a ON t.account_id = a.id
            LEFT JOIN transactions ot ON t.original_transaction_id = ot.id
            WHERE t.id = ?
        '''
        return self._execute_query(sql, (transaction_id,), fetch='row')
        
    def add_transaction(self, transaction_data: Dict) -> int:
        """Добавление новой транзакции"""
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
        
        with self.transaction() as cursor:
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
            
            cursor.execute(sql, params)
            transaction_id = cursor.lastrowid
            
            # Обновляем баланс счета
            cursor.execute(
                "UPDATE accounts SET current_balance = current_balance + ? WHERE id = ?",
                (transaction_data['amount'], transaction_data['account_id'])
            )
            
            # ИСПРАВЛЕННАЯ ЧАСТЬ: вычисляем и логируем price_per_unit
            quantity = transaction_data.get('quantity', 1.0)
            if quantity > 1.0:
                amount = transaction_data['amount']
                price_per_unit = amount / quantity if quantity != 0 else None
                self.logger.debug(f"Транзакция с количеством: {quantity}, "
                                f"price_per_unit: {price_per_unit}")
        
        self.data_updated.emit('transactions')
        self.logger.info(f"Добавлена транзакция ID: {transaction_id}")
        
        return transaction_id
        
    def add_refund(self, original_transaction_id: int, 
                   date: str = None, 
                   amount: float = None,
                   description: str = "") -> int:
        """
        Упрощенное создание возврата
        
        Args:
            original_transaction_id: ID оригинальной транзакции (ОБЯЗАТЕЛЬНО)
            date: Дата возврата (по умолчанию сегодня)
            amount: Сумма возврата (по умолчанию полная сумма оригинала)
            description: Описание возврата
        
        Returns:
            ID созданной транзакции возврата
        """
        # Получаем оригинальную транзакцию
        original = self.get_transaction_by_id(original_transaction_id)
        if not original:
            raise ValueError(f"Транзакция с ID {original_transaction_id} не найдена")
        
        # Определяем дату - теперь она передается параметром
        if date is None:
            from datetime import datetime
            date = datetime.now().strftime('%Y-%m-%d')
        
        # Определяем сумму возврата (противоположный знак оригинала)
        if amount is None:
            amount = -original['amount']  # Противоположный знак
        
        # Формируем описание
        if not description:
            original_desc = original.get('description', '')
            if original_desc:
                description = f"Возврат: {original_desc}"
            else:
                description = f"Возврат транзакции #{original_transaction_id}"
        
        # Создаем возврат
        refund_data = {
            'date': date,
            'amount': amount,
            'type': 'refund',
            'original_transaction_id': original_transaction_id,  # <-- ВАЖНО!
            'category_id': original['category_id'],
            'account_id': original['account_id'],
            'description': description
        }
        
        # Используем add_transaction который теперь поддерживает original_transaction_id
        return self.add_transaction(refund_data)
    
    def _add_transaction_with_original(self, transaction_data: Dict, original_transaction_id: int) -> int:
        """Добавление транзакции с поддержкой original_transaction_id"""
        required_fields = ['date', 'amount', 'type', 'account_id']
        for field in required_fields:
            if field not in transaction_data:
                raise ValueError(f"Отсутствует обязательное поле: {field}")
        
        # Проверяем тип транзакции
        if transaction_data['type'] not in ['income', 'expense', 'refund', 'correct']:
            raise ValueError(f"Некорректный тип транзакции: {transaction_data['type']}")
        
        # Для возвратов проверяем original_transaction_id
        if transaction_data['type'] == 'refund' and original_transaction_id is None:
            raise ValueError("Для возврата обязателен original_transaction_id")
        
        # Проверяем категорию для income/expense/refund
        if transaction_data['type'] in ['income', 'expense', 'refund'] and 'category_id' not in transaction_data:
            raise ValueError(f"Для типа '{transaction_data['type']}' обязательна категория")
        
        # Для корректировок категория должна быть NULL
        if transaction_data['type'] == 'correct':
            transaction_data['category_id'] = None
        
        with self.transaction() as cursor:
            # Добавляем транзакцию с original_transaction_id
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
                original_transaction_id if transaction_data['type'] == 'refund' else None
            )
            
            cursor.execute(sql, params)
            transaction_id = cursor.lastrowid
            
            # Обновляем баланс счета
            cursor.execute(
                "UPDATE accounts SET current_balance = current_balance + ? WHERE id = ?",
                (transaction_data['amount'], transaction_data['account_id'])
            )
            
            # ИСПРАВЛЕННАЯ ЧАСТЬ: вычисляем и логируем price_per_unit
            quantity = transaction_data.get('quantity', 1.0)
            if quantity > 1.0:
                amount = transaction_data['amount']
                price_per_unit = amount / quantity if quantity != 0 else None
                self.logger.debug(f"Транзакция с количеством: {quantity}, "
                                f"price_per_unit: {price_per_unit}")
        
        self.data_updated.emit('transactions')
        self.logger.info(f"Добавлена транзакция ID: {transaction_id}")
        
        return transaction_id
        
    def update_transaction(self, transaction_id: int, transaction_data: Dict) -> bool:
        """Обновление транзакции с проверкой возвратов"""
        # Получаем старую транзакцию
        old_transaction = self.get_transaction_by_id(transaction_id)
        if not old_transaction:
            self.logger.error(f"Транзакция с ID {transaction_id} не найдена")
            return False
        
        # Проверяем, не пытаемся ли изменить оригинальную транзакцию для возврата
        if old_transaction['type'] == 'refund' and 'original_transaction_id' in transaction_data:
            if transaction_data['original_transaction_id'] != old_transaction.get('original_transaction_id'):
                self.logger.error("Нельзя изменить original_transaction_id для возврата")
                return False
        
        # Остальная логика остается прежней, но с учетом нового поля
        try:
            with self.transaction() as cursor:
                # Отменяем старую транзакцию
                cursor.execute(
                    "UPDATE accounts SET current_balance = current_balance - ? WHERE id = ?",
                    (old_transaction['amount'], old_transaction['account_id'])
                )
                
                # Подготавливаем новые значения
                fields = []
                params = []
                
                allowed_fields = [
                    'date', 'amount', 'type', 'category_id', 
                    'description', 'account_id', 'quantity',
                    'original_transaction_id'  # НОВОЕ ПОЛЕ
                ]
                
                for field in allowed_fields:
                    if field in transaction_data:
                        fields.append(f"{field} = ?")
                        params.append(transaction_data[field])
                
                if not fields:
                    self.logger.warning("Нет полей для обновления")
                    return False
                
                # Добавляем updated_at
                fields.append("updated_at = CURRENT_TIMESTAMP")
                
                params.append(transaction_id)
                sql = f"UPDATE transactions SET {', '.join(fields)} WHERE id = ?"
                
                cursor.execute(sql, params)
                
                # Применяем новую транзакцию
                new_amount = transaction_data.get('amount', old_transaction['amount'])
                new_account_id = transaction_data.get('account_id', old_transaction['account_id'])
                
                cursor.execute(
                    "UPDATE accounts SET current_balance = current_balance + ? WHERE id = ?",
                    (new_amount, new_account_id)
                )
            
            self.data_updated.emit('transactions')
            self.logger.info(f"Обновлена транзакция ID: {transaction_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении транзакции: {e}")
            self.error_signal.emit(f"Ошибка обновления транзакции: {e}")
            return False
            
    def delete_transaction(self, transaction_id: int) -> bool:
        """Удаление транзакции с проверкой связанных возвратов"""
        # Получаем транзакцию
        transaction = self.get_transaction_by_id(transaction_id)
        if not transaction:
            self.logger.error(f"Транзакция с ID {transaction_id} не найдена")
            return False
        
        # Проверяем, есть ли возвраты для этой транзакции
        if transaction['type'] != 'refund':
            refunds = self.get_refunds_for_transaction(transaction_id)
            if refunds:
                self.logger.error(f"Нельзя удалить транзакцию с возвратами. Сначала удалите возвраты.")
                self.error_signal.emit("Нельзя удалить транзакцию с возвратами")
                return False
        
        try:
            with self.transaction() as cursor:
                # Возвращаем баланс
                cursor.execute(
                    "UPDATE accounts SET current_balance = current_balance - ? WHERE id = ?",
                    (transaction['amount'], transaction['account_id'])
                )
                
                # Удаляем транзакцию
                cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
            
            self.data_updated.emit('transactions')
            self.logger.info(f"Удалена транзакция ID: {transaction_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при удалении транзакции: {e}")
            self.error_signal.emit(f"Ошибка удаления транзакции: {e}")
            return False
            
    def reconcile_account(self, account_id: int, actual_balance: float, 
                         description: str = "") -> int:
        """Создание операции сверки баланса (корректировка)"""
        account = self.get_account_by_id(account_id)
        if not account:
            raise ValueError(f"Счет с ID {account_id} не найден")
        
        current_balance = account['current_balance']
        difference = actual_balance - current_balance
        
        if abs(difference) < 0.01:  # игнорируем мелкие различия
            self.logger.info(f"Баланс счета {account_id} уже правильный")
            return 0
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        if not description:
            direction = "увеличение" if difference > 0 else "уменьшение"
            description = f"Корректировка баланса ({direction}): {difference:+.2f} {account.get('currency', 'RUB')}"
        
        # Создаем транзакцию типа 'correct' без категории
        transaction_id = self.add_transaction({
            'date': today,
            'amount': difference,
            'type': 'correct',
            'account_id': account_id,
            'description': description,
            'category_id': None  # обязательно NULL для корректировок
        })
        
        self.logger.info(f"Создана корректировка баланса для счета {account_id}: {difference:+.2f}")
        return transaction_id
    
    def get_account_corrections(self, account_id: int, date_from: str = None, 
                               date_to: str = None) -> List[Dict]:
        """Получение корректировок баланса для счета"""
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
        
        return self._execute_query(sql, tuple(params), fetch='all')
    
    
    def get_refunds_for_transaction(self, original_transaction_id: int) -> List[Dict]:
        """Получение всех возвратов для оригинальной транзакции"""
        sql = '''
            SELECT 
                t.id, t.date, t.amount, t.description,
                t.created_at, t.updated_at
            FROM transactions t
            WHERE t.original_transaction_id = ?
              AND t.type = 'refund'
            ORDER BY t.date ASC
        '''
        return self._execute_query(sql, (original_transaction_id,), fetch='all')
    
    # ========== МЕТОДЫ ДЛЯ ПЕРЕВОДОВ (TRANSFERS) ==========
    def get_transfers(self, filters: Dict = None) -> List[Dict]:
        """Получение всех переводов"""
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
        
        return self._execute_query(sql, tuple(params), fetch='all')
    
    def add_transfer(self, transfer_data: Dict) -> int:
        """Добавление нового перевода"""
        required_fields = ['date', 'amount', 'from_account_id', 'to_account_id']
        for field in required_fields:
            if field not in transfer_data:
                raise ValueError(f"Отсутствует обязательное поле: {field}")
        
        if transfer_data['from_account_id'] == transfer_data['to_account_id']:
            raise ValueError("Нельзя переводить средства на тот же счет")
        
        try:
            with self.transaction() as cursor:
                # Обновляем баланс счета-отправителя
                cursor.execute(
                    "UPDATE accounts SET current_balance = current_balance - ? WHERE id = ?",
                    (transfer_data['amount'], transfer_data['from_account_id'])
                )
                
                # Обновляем баланс счета-получателя
                cursor.execute(
                    "UPDATE accounts SET current_balance = current_balance + ? WHERE id = ?",
                    (transfer_data['amount'], transfer_data['to_account_id'])
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
                
                cursor.execute(sql, params)
                transfer_id = cursor.lastrowid
            
            self.data_updated.emit('transfers')
            self.logger.info(f"Добавлен перевод ID: {transfer_id}")
            
            return transfer_id
            
        except Exception as e:
            self.logger.error(f"Ошибка при добавлении перевода: {e}")
            self.error_signal.emit(f"Ошибка добавления перевода: {e}")
            raise
    
    def delete_transfer(self, transfer_id: int) -> bool:
        """Удаление перевода"""
        # Получаем данные перевода
        sql = '''
            SELECT amount, from_account_id, to_account_id 
            FROM transfers WHERE id = ?
        '''
        transfer = self._execute_query(sql, (transfer_id,), fetch='row')
        
        if not transfer:
            self.logger.error(f"Перевод с ID {transfer_id} не найден")
            return False
        
        try:
            with self.transaction() as cursor:
                # Возвращаем средства
                cursor.execute(
                    "UPDATE accounts SET current_balance = current_balance + ? WHERE id = ?",
                    (transfer['amount'], transfer['from_account_id'])
                )
                
                cursor.execute(
                    "UPDATE accounts SET current_balance = current_balance - ? WHERE id = ?",
                    (transfer['amount'], transfer['to_account_id'])
                )
                
                # Удаляем перевод
                cursor.execute("DELETE FROM transfers WHERE id = ?", (transfer_id,))
            
            self.data_updated.emit('transfers')
            self.logger.info(f"Удален перевод ID: {transfer_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при удалении перевода: {e}")
            self.error_signal.emit(f"Ошибка удаления перевода: {e}")
            return False
    
    # ========== МЕТОДЫ ДЛЯ БЮДЖЕТОВ (BUDGETS) ==========
    def set_budget(self, category_id: int, month_year: str, amount: float) -> bool:
        """Установка бюджета на месяц"""
        try:
            sql = '''
                INSERT OR REPLACE INTO budgets 
                (category_id, month_year, planned_amount) 
                VALUES (?, ?, ?)
            '''
            
            success = self._execute_query(sql, (category_id, month_year, amount))
            
            if success:
                self.data_updated.emit('budgets')
                self.logger.info(f"Установлен бюджет для категории {category_id} на {month_year}: {amount}")
            
            return bool(success)
            
        except Exception as e:
            self.logger.error(f"Ошибка при установке бюджета: {e}")
            return False
    
    def get_budgets(self, month_year: str = None) -> List[Dict]:
        """Получение бюджетов"""
        if month_year:
            sql = '''
                SELECT 
                    b.id, b.category_id, b.month_year, 
                    b.planned_amount, b.actual_amount, b.created_at,
                    c.name as category_name, c.type as category_type,
                    c.color as category_color
                FROM budgets b
                JOIN categories c ON b.category_id = c.id
                WHERE b.month_year = ?
                ORDER BY c.type, c.name
            '''
            return self._execute_query(sql, (month_year,), fetch='all')
        else:
            sql = '''
                SELECT 
                    b.id, b.category_id, b.month_year, 
                    b.planned_amount, b.actual_amount, b.created_at,
                    c.name as category_name, c.type as category_type,
                    c.color as category_color
                FROM budgets b
                JOIN categories c ON b.category_id = c.id
                ORDER BY b.month_year DESC, c.type, c.name
            '''
            return self._execute_query(sql, fetch='all')
    
    def get_budget_status(self, month_year: str) -> List[Dict]:
        """Получение статуса бюджетов на месяц"""
        sql = '''
            SELECT 
                b.category_id,
                c.name as category_name,
                c.type as category_type,
                b.planned_amount,
                COALESCE(SUM(CASE 
                    WHEN t.type = 'expense' THEN ABS(t.amount)
                    ELSE 0 
                END), 0) as actual_amount,
                c.color
            FROM budgets b
            JOIN categories c ON b.category_id = c.id
            LEFT JOIN transactions t ON t.category_id = c.id 
                AND t.type = 'expense'
                AND strftime('%Y-%m', t.date) = ?
            WHERE b.month_year = ?
            GROUP BY b.category_id, c.name, c.type, b.planned_amount, c.color
        '''
        
        return self._execute_query(sql, (month_year, month_year), fetch='all')
    
    def update_budget_actuals(self, month_year: str) -> bool:
        """Обновление фактических сумм в бюджетах"""
        try:
            with self.transaction() as cursor:
                sql = '''
                    UPDATE budgets
                    SET actual_amount = (
                        SELECT COALESCE(SUM(ABS(t.amount)), 0)
                        FROM transactions t
                        WHERE t.category_id = budgets.category_id
                          AND t.type = 'expense'
                          AND strftime('%Y-%m', t.date) = budgets.month_year
                    )
                    WHERE month_year = ?
                '''
                
                cursor.execute(sql, (month_year,))
            
            self.data_updated.emit('budgets')
            self.logger.info(f"Обновлены фактические суммы бюджетов за {month_year}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении бюджетов: {e}")
            return False
    
    # ========== МЕТОДЫ ДЛЯ ЗАЙМОВ (LOANS) ==========
    def get_loans(self, filters: Dict = None) -> List[Dict]:
        """Получение всех займов"""
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
        
        return self._execute_query(sql, tuple(params), fetch='all')
    
    def get_loan_by_id(self, loan_id: int) -> Optional[Dict]:
        """Получение займа по ID"""
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
            WHERE l.id = ?
        '''
        return self._execute_query(sql, (loan_id,), fetch='row')
    
    def add_loan(self, loan_data: Dict) -> int:
        """Добавление нового займа"""
        required_fields = ['account_id', 'contact_name', 'loan_type', 'loan_amount', 'issue_date']
        for field in required_fields:
            if field not in loan_data:
                raise ValueError(f"Отсутствует обязательное поле: {field}")
        
        try:
            # Создаем или получаем счет контрагента
            counterparty_account_id = self.create_counterparty_account(loan_data['contact_name'])
            
            with self.transaction() as cursor:
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
                
                cursor.execute(sql, params)
                loan_id = cursor.lastrowid
                
                # Обновляем балансы счетов
                if loan_data['loan_type'] == 'received':
                    # Получен займ: наш счет +, контрагент -
                    cursor.execute(
                        "UPDATE accounts SET current_balance = current_balance + ? WHERE id = ?",
                        (loan_data['loan_amount'], loan_data['account_id'])
                    )
                    cursor.execute(
                        "UPDATE accounts SET current_balance = current_balance - ? WHERE id = ?",
                        (loan_data['loan_amount'], counterparty_account_id)
                    )
                else:  # 'issued'
                    # Выдан займ: наш счет -, контрагент +
                    cursor.execute(
                        "UPDATE accounts SET current_balance = current_balance - ? WHERE id = ?",
                        (loan_data['loan_amount'], loan_data['account_id'])
                    )
                    cursor.execute(
                        "UPDATE accounts SET current_balance = current_balance + ? WHERE id = ?",
                        (loan_data['loan_amount'], counterparty_account_id)
                    )
            
            self.data_updated.emit('loans')
            self.logger.info(f"Добавлен займ ID: {loan_id}")
            
            return loan_id
            
        except Exception as e:
            self.logger.error(f"Ошибка при добавлении займа: {e}")
            self.error_signal.emit(f"Ошибка добавления займа: {e}")
            raise
    
    def add_loan_payment(self, payment_data: Dict) -> int:
        """Добавление платежа по займу"""
        required_fields = ['loan_id', 'payment_date', 'payment_amount']
        for field in required_fields:
            if field not in payment_data:
                raise ValueError(f"Отсутствует обязательное поле: {field}")
        
        try:
            # Получаем данные займа
            loan = self.get_loan_by_id(payment_data['loan_id'])
            if not loan:
                raise ValueError(f"Займ с ID {payment_data['loan_id']} не найден")
            
            if loan['outstanding_amount'] < payment_data['payment_amount']:
                raise ValueError("Сумма платежа превышает остаток долга")
            
            with self.transaction() as cursor:
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
                
                cursor.execute(sql, params)
                payment_id = cursor.lastrowid
                
                # Обновляем остаток долга
                new_outstanding = loan['outstanding_amount'] - payment_data['payment_amount']
                cursor.execute(
                    "UPDATE loans SET outstanding_amount = ? WHERE id = ?",
                    (new_outstanding, payment_data['loan_id'])
                )
                
                # Обновляем статус займа если долг погашен
                if new_outstanding <= 0:
                    cursor.execute(
                        "UPDATE loans SET status = 'paid' WHERE id = ?",
                        (payment_data['loan_id'],)
                    )
                
                # Создаем перевод между счетами
                if loan['loan_type'] == 'issued':
                    # Возврат выданного займа: контрагент → наш счет
                    from_account_id = loan['counterparty_account_id']
                    to_account_id = loan['account_id']
                    transfer_desc = f"Возврат займа: {loan['contact_name']}"
                else:  # 'received'
                    # Погашение полученного займа: наш счет → контрагент
                    from_account_id = loan['account_id']
                    to_account_id = loan['counterparty_account_id']
                    transfer_desc = f"Погашение займа: {loan['contact_name']}"
                
                if payment_data.get('description'):
                    transfer_desc += f" - {payment_data['description']}"
                
                cursor.execute('''
                    INSERT INTO transfers 
                    (date, amount, from_account_id, to_account_id, description)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    payment_data['payment_date'],
                    payment_data['payment_amount'],
                    from_account_id,
                    to_account_id,
                    transfer_desc
                ))
            
            self.data_updated.emit('loans')
            self.data_updated.emit('transfers')
            self.logger.info(f"Добавлен платеж по займу ID: {payment_id}")
            
            return payment_id
            
        except Exception as e:
            self.logger.error(f"Ошибка при добавлении платежа по займу: {e}")
            self.error_signal.emit(f"Ошибка добавления платежа по займу: {e}")
            raise
    
    def update_loan(self, loan_id: int, loan_data: Dict) -> bool:
        """Обновление данных займа"""
        if not loan_data:
            return False
        
        # Проверяем существование займа
        loan = self.get_loan_by_id(loan_id)
        if not loan:
            self.logger.error(f"Займ с ID {loan_id} не найден")
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
            self.logger.warning("Нет полей для обновления в займе")
            return False
        
        params.append(loan_id)
        sql = f"UPDATE loans SET {', '.join(fields)} WHERE id = ?"
        
        try:
            success = self._execute_query(sql, tuple(params))
            if success:
                self.data_updated.emit('loans')
                self.logger.info(f"Обновлен займ ID: {loan_id}")
            
            return bool(success)
            
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении займа: {e}")
            self.error_signal.emit(f"Ошибка обновления займа: {e}")
            return False
            
    
    def get_loan_payments(self, loan_id: int) -> List[Dict]:
        """Получение платежей по займу"""
        sql = '''
            SELECT 
                id, loan_id, payment_date, payment_amount,
                interest_amount, principal_amount, description, created_at
            FROM loan_payments
            WHERE loan_id = ?
            ORDER BY payment_date DESC
        '''
        return self._execute_query(sql, (loan_id,), fetch='all')
    
    def delete_loan_payment(self, payment_id: int) -> bool:
        """Удаление платежа по займу с восстановлением балансов"""
        try:
            # Получаем данные платежа
            sql = '''
                SELECT lp.*, l.loan_type, l.account_id, l.counterparty_account_id, 
                       l.contact_name, l.outstanding_amount
                FROM loan_payments lp
                JOIN loans l ON lp.loan_id = l.id
                WHERE lp.id = ?
            '''
            payment = self._execute_query(sql, (payment_id,), fetch='row')
            
            if not payment:
                self.logger.error(f"Платеж с ID {payment_id} не найден")
                return False
            
            with self.transaction() as cursor:
                # Восстанавливаем балансы
                if payment['loan_type'] == 'issued':
                    # Отменяем возврат выданного займа
                    cursor.execute(
                        "UPDATE accounts SET current_balance = current_balance - ? WHERE id = ?",
                        (payment['payment_amount'], payment['counterparty_account_id'])
                    )
                    cursor.execute(
                        "UPDATE accounts SET current_balance = current_balance + ? WHERE id = ?",
                        (payment['payment_amount'], payment['account_id'])
                    )
                else:  # 'received'
                    # Отменяем погашение полученного займа
                    cursor.execute(
                        "UPDATE accounts SET current_balance = current_balance + ? WHERE id = ?",
                        (payment['payment_amount'], payment['account_id'])
                    )
                    cursor.execute(
                        "UPDATE accounts SET current_balance = current_balance - ? WHERE id = ?",
                        (payment['payment_amount'], payment['counterparty_account_id'])
                    )
                
                # Восстанавливаем остаток долга
                new_outstanding = payment['outstanding_amount'] + payment['payment_amount']
                cursor.execute(
                    "UPDATE loans SET outstanding_amount = ? WHERE id = ?",
                    (new_outstanding, payment['loan_id'])
                )
                
                # Обновляем статус если нужно
                if new_outstanding > 0 and payment['outstanding_amount'] <= 0:
                    cursor.execute(
                        "UPDATE loans SET status = 'active' WHERE id = ?",
                        (payment['loan_id'],)
                    )
                
                # Удаляем платеж
                cursor.execute("DELETE FROM loan_payments WHERE id = ?", (payment_id,))
                
                # Удаляем связанный перевод (опционально)
                # cursor.execute("DELETE FROM transfers WHERE ...")
            
            self.data_updated.emit('loans')
            self.logger.info(f"Удален платеж по займу ID: {payment_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при удалении платежа по займу: {e}")
            self.error_signal.emit(f"Ошибка удаления платежа по займу: {e}")
            return False
    
    # ========== ОТЧЕТЫ И АНАЛИТИКА ==========
    def get_monthly_summary(self, year: int, month: int = None) -> Dict:
        """Получение сводки за месяц с учетом возвратов"""
        sql = '''
            SELECT 
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) as total_income,
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) as total_expense,
                COALESCE(SUM(CASE WHEN type = 'refund' THEN amount ELSE 0 END), 0) as total_refund,
                COALESCE(SUM(CASE WHEN type = 'correct' THEN amount ELSE 0 END), 0) as total_correction,
                COUNT(*) as transaction_count
            FROM transactions
            WHERE strftime('%Y', date) = ?
        '''
        
        params = [str(year)]
        
        if month:
            sql += " AND strftime('%m', date) = ?"
            params.append(f"{month:02d}")
        
        result = self._execute_query(sql, tuple(params), fetch='one')
        
        return {
            'income': result.get('total_income', 0.0) or 0.0,
            'expense': result.get('total_expense', 0.0) or 0.0,
            'refund': result.get('total_refund', 0.0) or 0.0,
            'correction': result.get('total_correction', 0.0) or 0.0,
            'balance': (result.get('total_income', 0.0) or 0.0) + 
                       (result.get('total_expense', 0.0) or 0.0) + 
                       (result.get('total_refund', 0.0) or 0.0),
            'transaction_count': result.get('transaction_count', 0) or 0
        }
        
    def get_category_statistics(self, date_from: str = None, date_to: str = None) -> Dict:
        """Получение статистики по категориям."""
        result = {
            'income_categories': [],
            'expense_categories': [],
            'total_income': 0.0,
            'total_expense': 0.0
        }
        
        # Получаем все категории доходов
        income_cats = self.get_categories(type='income')
        for cat in income_cats:
            sql = '''
                SELECT 
                    COALESCE(SUM(amount), 0) as total_amount,
                    COUNT(*) as transaction_count
                FROM transactions
                WHERE category_id = ?
                    AND type = 'income'
            '''
            
            params = [cat['id']]
            if date_from:
                sql += " AND date >= ?"
                params.append(date_from)
            if date_to:
                sql += " AND date <= ?"
                params.append(date_to)
            
            stats = self._execute_query(sql, tuple(params), fetch='one')
            
            if stats:
                result['income_categories'].append({
                    'id': cat['id'],
                    'name': cat['name'],
                    'type': 'income',
                    'total_amount': stats['total_amount'] or 0.0,
                    'transaction_count': stats['transaction_count'] or 0,
                    'color': cat.get('color', '#2ECC71'),
                    'icon': cat.get('icon', '💰')
                })
                result['total_income'] += stats['total_amount'] or 0.0
        
        # Получаем все категории расходов (только основные, без подкатегорий)
        expense_cats = self.get_categories(type='expense', include_subcategories=False)
        for cat in expense_cats:
            # Получаем все подкатегории
            subcats = self.get_categories(type='expense')
            all_cat_ids = [cat['id']]
            for subcat in subcats:
                if subcat.get('parent_id') == cat['id']:
                    all_cat_ids.append(subcat['id'])
            
            # Строим IN запрос
            placeholders = ','.join(['?'] * len(all_cat_ids))
            sql = f'''
                SELECT 
                    COALESCE(SUM(ABS(amount)), 0) as total_amount,
                    COUNT(*) as transaction_count
                FROM transactions
                WHERE category_id IN ({placeholders})
                    AND type = 'expense'
            '''
            
            params = all_cat_ids
            if date_from:
                sql += " AND date >= ?"
                params.append(date_from)
            if date_to:
                sql += " AND date <= ?"
                params.append(date_to)
            
            stats = self._execute_query(sql, tuple(params), fetch='one')
            
            if stats and (stats['total_amount'] or 0) > 0:
                result['expense_categories'].append({
                    'id': cat['id'],
                    'name': cat['name'],
                    'type': 'expense',
                    'total_amount': stats['total_amount'] or 0.0,
                    'transaction_count': stats['transaction_count'] or 0,
                    'color': cat.get('color', '#E74C3C'),
                    'icon': cat.get('icon', '🛒')
                })
                result['total_expense'] += stats['total_amount'] or 0.0
        
        # Сортируем категории по сумме
        result['income_categories'].sort(key=lambda x: x['total_amount'], reverse=True)
        result['expense_categories'].sort(key=lambda x: x['total_amount'], reverse=True)
        
        return result
    
    def get_expense_distribution(self, year: int, month: int = None) -> List[Dict]:
        """Распределение расходов по категориям"""
        sql = '''
            SELECT 
                c.id, c.name, c.color, c.icon,
                COALESCE(SUM(ABS(t.amount)), 0) as amount,
                COUNT(t.id) as count
            FROM categories c
            LEFT JOIN transactions t ON c.id = t.category_id 
                AND t.type = 'expense'
                AND strftime('%Y', t.date) = ?
        '''
        
        params = [str(year)]
        
        if month:
            sql += " AND strftime('%m', t.date) = ?"
            params.append(f"{month:02d}")
        
        sql += '''
            WHERE c.type = 'expense'
            GROUP BY c.id, c.name, c.color, c.icon
            HAVING amount > 0
            ORDER BY amount DESC
        '''
        
        return self._execute_query(sql, tuple(params), fetch='all')
    
    def get_yearly_overview(self, year: int) -> Dict:
        """Обзор за год по месяцам"""
        sql = '''
            SELECT 
                strftime('%Y-%m', date) as month_year,
                SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as income,
                SUM(CASE WHEN type = 'expense' THEN ABS(amount) ELSE 0 END) as expense,
                SUM(CASE WHEN type = 'correct' THEN amount ELSE 0 END) as correction,
                COUNT(*) as count
            FROM transactions
            WHERE strftime('%Y', date) = ?
            GROUP BY month_year
            ORDER BY month_year
        '''
        
        monthly_data = self._execute_query(sql, (str(year),), fetch='all')
        
        # Заполняем все месяцы
        all_months = {}
        for month in range(1, 13):
            month_key = f"{year}-{month:02d}"
            all_months[month_key] = {
                'income': 0.0,
                'expense': 0.0,
                'correction': 0.0,
                'count': 0,
                'balance': 0.0
            }
        
        # Заполняем данные из БД
        for data in monthly_data:
            month_key = data['month_year']
            if month_key in all_months:
                all_months[month_key] = {
                    'income': data['income'] or 0.0,
                    'expense': data['expense'] or 0.0,
                    'correction': data['correction'] or 0.0,
                    'count': data['count'] or 0,
                    'balance': (data['income'] or 0.0) - (data['expense'] or 0.0)
                }
        
        # Рассчитываем накопительный баланс
        cumulative_balance = 0
        for month in range(1, 13):
            month_key = f"{year}-{month:02d}"
            month_data = all_months[month_key]
            month_balance = month_data['income'] - month_data['expense']
            cumulative_balance += month_balance
            all_months[month_key]['cumulative_balance'] = cumulative_balance
        
        return {
            'year': year,
            'monthly_data': all_months,
            'total_income': sum(data['income'] for data in all_months.values()),
            'total_expense': sum(data['expense'] for data in all_months.values()),
            'total_correction': sum(data['correction'] for data in all_months.values()),
            'final_balance': cumulative_balance
        }
    
    def get_yearly_summary(self, year: int) -> Dict[str, Dict]:
        """Получает сводку по месяцам за год для графика доходов/расходов."""
        sql = '''
            SELECT 
                strftime('%Y-%m', date) as month_year,
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) as income,
                COALESCE(SUM(CASE WHEN type = 'expense' THEN ABS(amount) ELSE 0 END), 0) as expense,
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount 
                                  WHEN type = 'expense' THEN -ABS(amount) 
                                  ELSE 0 END), 0) as balance
            FROM transactions
            WHERE strftime('%Y', date) = ?
                AND type IN ('income', 'expense')
            GROUP BY month_year
            ORDER BY month_year
        '''
        
        results = self._execute_query(sql, (str(year),), fetch='all')
        
        # Создаем структуру данных для всех месяцев
        monthly_data = {}
        for month in range(1, 13):
            month_key = f"{year}-{month:02d}"
            monthly_data[month_key] = {
                'income': 0.0,
                'expense': 0.0,
                'balance': 0.0
            }
        
        # Заполняем данные из БД
        for result in results:
            month_key = result['month_year']
            if month_key in monthly_data:
                monthly_data[month_key] = {
                    'income': result['income'] or 0.0,
                    'expense': result['expense'] or 0.0,
                    'balance': result['balance'] or 0.0
                }
        
        return monthly_data  
    
    # ========== УТИЛИТЫ ==========
    def recalculate_all_balances(self) -> Dict:
        """Пересчет всех балансов с поддержкой прогресса"""
        try:
            # Используем оптимизированный метод одним запросом
            with self.transaction() as cursor:
                # 1. Сбрасываем все балансы к начальным
                cursor.execute("UPDATE accounts SET current_balance = initial_balance")
                
                # 2. Применяем транзакции - ОДНИМ запросом
                cursor.execute('''
                    UPDATE accounts 
                    SET current_balance = current_balance + (
                        SELECT COALESCE(SUM(amount), 0)
                        FROM transactions 
                        WHERE account_id = accounts.id
                    )
                ''')
                
                # 3. Применяем переводы - ОДНИМ запросом
                cursor.execute('''
                    UPDATE accounts 
                    SET current_balance = current_balance + (
                        SELECT COALESCE(SUM(
                            CASE 
                                WHEN to_account_id = accounts.id THEN amount
                                WHEN from_account_id = accounts.id THEN -amount
                                ELSE 0
                            END
                        ), 0)
                        FROM transfers
                        WHERE to_account_id = accounts.id OR from_account_id = accounts.id
                    )
                ''')
            
            # Получаем количество обработанных счетов
            count_result = self._execute_query("SELECT COUNT(*) as cnt FROM accounts WHERE is_active = 1", fetch='one')
            processed = count_result['cnt'] if count_result else 0
            
            # Инвалидируем кэш
            self.invalidate_cache('accounts')
            
            # Отправляем сигнал об обновлении
            self.data_updated.emit('accounts')
            
            self.logger.info(f"Балансы пересчитаны для {processed} счетов")
            
            return {
                'success': True,
                'message': f'Балансы успешно пересчитаны для {processed} счетов',
                'accounts_processed': processed
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка при пересчете балансов: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                'success': False,
                'message': f'Ошибка при пересчете балансов: {str(e)[:200]}',
                'error_details': str(e)
            }
        
    def recalculate_all_balances_fast(self) -> Dict:
        """Быстрый пересчет всех балансов с использованием группировки"""
        try:
            with self.transaction() as cursor:
                # 1. Сбрасываем все балансы к начальным
                cursor.execute("UPDATE accounts SET current_balance = initial_balance")
                
                # 2. Применяем транзакции - ОДНИМ запросом
                cursor.execute('''
                    UPDATE accounts 
                    SET current_balance = current_balance + (
                        SELECT COALESCE(SUM(amount), 0)
                        FROM transactions 
                        WHERE account_id = accounts.id
                    )
                ''')
                
                # 3. Применяем переводы - ОДНИМ запросом
                cursor.execute('''
                    UPDATE accounts 
                    SET current_balance = current_balance + (
                        SELECT COALESCE(SUM(
                            CASE 
                                WHEN to_account_id = accounts.id THEN amount
                                WHEN from_account_id = accounts.id THEN -amount
                                ELSE 0
                            END
                        ), 0)
                        FROM transfers
                        WHERE to_account_id = accounts.id OR from_account_id = accounts.id
                    )
                ''')
            
            # Получаем количество обработанных счетов
            count_result = self._execute_query("SELECT COUNT(*) as cnt FROM accounts", fetch='one')
            processed = count_result['cnt'] if count_result else 0
            
            self.invalidate_cache('accounts')
            self.data_updated.emit('accounts')
            
            self.logger.info(f"Быстро пересчитаны балансы для {processed} счетов")
            
            return {
                'success': True,
                'message': f'Балансы успешно пересчитаны для {processed} счетов',
                'accounts_processed': processed,
                'method': 'fast_batch'
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка при быстром пересчете балансов: {e}")
            
            # Пробуем старый метод как fallback
            try:
                return self.recalculate_all_balances_slow()
            except:
                return {
                    'success': False,
                    'message': f'Ошибка при пересчете балансов: {str(e)}'
                }
    
    def backup_database(self, backup_path: str) -> bool:
        """Создание резервной копии БД"""
        try:
            import shutil
            import os
            
            # Создаем директорию если нет
            os.makedirs(os.path.dirname(os.path.abspath(backup_path)), exist_ok=True)
            
            # Закрываем все соединения
            if hasattr(self._thread_local, 'connection'):
                self._thread_local.connection.close()
                delattr(self._thread_local, 'connection')
            
            # Копируем файл
            shutil.copy2(self.db_path, backup_path)
            
            self.logger.info(f"Создана резервная копия: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при создании резервной копии: {e}")
            return False
    
    def check_data_integrity(self) -> Dict:
        """Проверка целостности данных"""
        checks = []
        
        try:
            # 1. Проверка балансов
            sql_balance = '''
                SELECT 
                    a.id, a.name, a.current_balance,
                    (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE account_id = a.id) as trans_sum,
                    (SELECT COALESCE(SUM(
                        CASE 
                            WHEN to_account_id = a.id THEN amount
                            WHEN from_account_id = a.id THEN -amount
                            ELSE 0
                        END
                    ), 0) FROM transfers WHERE to_account_id = a.id OR from_account_id = a.id) as transfer_sum,
                    a.initial_balance + 
                    (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE account_id = a.id) +
                    (SELECT COALESCE(SUM(
                        CASE 
                            WHEN to_account_id = a.id THEN amount
                            WHEN from_account_id = a.id THEN -amount
                            ELSE 0
                        END
                    ), 0) FROM transfers WHERE to_account_id = a.id OR from_account_id = a.id) as calculated_balance
                FROM accounts a
            '''
            
            balance_results = self._execute_query(sql_balance, fetch='all')
            balance_issues = []
            
            for acc in balance_results:
                diff = abs(acc['current_balance'] - acc['calculated_balance'])
                if diff > 0.01:  # допуск 0.01
                    balance_issues.append({
                        'account': acc['name'],
                        'current': acc['current_balance'],
                        'calculated': acc['calculated_balance'],
                        'difference': diff
                    })
            
            if balance_issues:
                checks.append({
                    'name': 'Балансы счетов',
                    'status': 'error',
                    'issues': balance_issues,
                    'message': f'Найдено {len(balance_issues)} счетов с некорректным балансом'
                })
            else:
                checks.append({
                    'name': 'Балансы счетов',
                    'status': 'ok',
                    'message': 'Все балансы корректны'
                })
            
            # 2. Проверка foreign keys
            sql_fk = '''
                SELECT 
                    'transactions -> accounts' as relation,
                    COUNT(*) as invalid_count
                FROM transactions t
                LEFT JOIN accounts a ON t.account_id = a.id
                WHERE a.id IS NULL
                
                UNION ALL
                
                SELECT 
                    'transactions -> categories' as relation,
                    COUNT(*) as invalid_count
                FROM transactions t
                LEFT JOIN categories c ON t.category_id = c.id
                WHERE t.category_id IS NOT NULL AND c.id IS NULL
                
                UNION ALL
                
                SELECT 
                    'transfers -> accounts (from)' as relation,
                    COUNT(*) as invalid_count
                FROM transfers tr
                LEFT JOIN accounts a ON tr.from_account_id = a.id
                WHERE a.id IS NULL
                
                UNION ALL
                
                SELECT 
                    'transfers -> accounts (to)' as relation,
                    COUNT(*) as invalid_count
                FROM transfers tr
                LEFT JOIN accounts a ON tr.to_account_id = a.id
                WHERE a.id IS NULL
            '''
            
            fk_results = self._execute_query(sql_fk, fetch='all')
            fk_issues = []
            
            for fk in fk_results:
                if fk['invalid_count'] > 0:
                    fk_issues.append(f"{fk['relation']}: {fk['invalid_count']} записей")
            
            if fk_issues:
                checks.append({
                    'name': 'Внешние ключи',
                    'status': 'error',
                    'issues': fk_issues,
                    'message': f'Найдено {len(fk_issues)} нарушений целостности'
                })
            else:
                checks.append({
                    'name': 'Внешние ключи',
                    'status': 'ok',
                    'message': 'Все связи корректны'
                })
            
            # 3. Проверка типов транзакций
            sql_types = '''
                SELECT type, COUNT(*) as count
                FROM transactions
                GROUP BY type
            '''
            
            type_results = self._execute_query(sql_types, fetch='all')
            checks.append({
                'name': 'Типы транзакций',
                'status': 'info',
                'data': type_results,
                'message': f'Всего транзакций: {sum(t["count"] for t in type_results)}'
            })
            
            return {
                'success': True,
                'checks': checks,
                'has_errors': any(c['status'] == 'error' for c in checks),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка при проверке целостности: {e}")
            return {
                'success': False,
                'error': str(e),
                'checks': checks
            }
    
    def get_database_info(self) -> Dict:
        """Получение информации о базе данных"""
        try:
            info = {}
            
            # Количество записей в таблицах
            tables = ['accounts', 'categories', 'transactions', 'transfers', 'budgets', 'loans', 'loan_payments']
            
            for table in tables:
                count = self._execute_query(f"SELECT COUNT(*) as count FROM {table}", fetch='one')
                info[table] = count['count'] if count else 0
            
            # Размер файла БД
            import os
            if os.path.exists(self.db_path):
                info['file_size'] = os.path.getsize(self.db_path)
                info['file_modified'] = datetime.fromtimestamp(os.path.getmtime(self.db_path)).isoformat()
            
            # Версия SQLite
            version = self._execute_query("SELECT sqlite_version() as version", fetch='one')
            info['sqlite_version'] = version['version'] if version else 'unknown'
            
            # Информация о таблицах
            tables_info = self._execute_query(
                "SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name",
                fetch='all'
            )
            info['tables'] = tables_info
            
            return {
                'success': True,
                'info': info,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка при получении информации о БД: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def close(self):
        """Закрытие всех соединений и отключение сигналов"""
        try:
            # Отключаем все сигналы
            try:
                self.data_updated.disconnect()
                self.progress_signal.disconnect()
                self.error_signal.disconnect()
            except (RuntimeError, TypeError):
                # Если нет подключений или объект уже удален - игнорируем
                pass
            
            # Закрываем соединение с БД
            if hasattr(self._thread_local, 'connection'):
                self._thread_local.connection.close()
                delattr(self._thread_local, 'connection')
                self.logger.info("Соединение с БД закрыто")
        except Exception as e:
            self.logger.error(f"Ошибка при закрытии соединения: {e}")
    
# ========== ДЕКОРАТОРЫ И ВСПОМОГАТЕЛЬНЫЕ КЛАССЫ ==========

def db_transaction(func):
    """Декоратор для автоматического управления транзакциями"""
    def wrapper(*args, **kwargs):
        db = DatabaseManager.get_instance()
        with db.transaction() as cursor:
            return func(*args, **kwargs, cursor=cursor)
    return wrapper


class DatabaseSignals(QObject):
    """Сигналы для асинхронных операций с БД"""
    result = Signal(object)
    error = Signal(str)
    progress = Signal(str, int)