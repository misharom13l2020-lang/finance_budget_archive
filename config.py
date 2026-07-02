# config.py
"""
Конфигурация приложения " Бюджет"
"""

from pathlib import Path
import sys
import os

# ========== ПРИЛОЖЕНИЕ ==========
APP_NAME = " Бюджет"
APP_VERSION = "2.5"
APP_ORGANIZATION = "MyFinance"
APP_DESCRIPTION = "Управление личными финансами"

# ========== БАЗА ДАННЫХ ==========
DB_FILENAME = "budget.db"
DB_CACHE_TTL = 60  # секунд

def get_app_root() -> str:
    """
    Возвращает папку, где лежит запущенный .exe (или main.py).
    Это гарантирует, что БД и конфиги ищутся рядом с программой.
    """
    if getattr(sys, 'frozen', False):
        # Если запущено как скомпилированный .exe (PyInstaller)
        return os.path.dirname(sys.executable)
    else:
        # Если запущено как скрипт Python
        return os.path.dirname(os.path.abspath(__file__))

def get_db_path() -> str:
    """Полный путь к файлу базы данных рядом с приложением."""
    return os.path.join(get_app_root(), DB_FILENAME)

# ========== GUI НАСТРОЙКИ ==========
# Размеры главного окна
MAIN_WINDOW_MIN_WIDTH = 1300
MAIN_WINDOW_MIN_HEIGHT = 680
MAIN_WINDOW_DEFAULT_WIDTH = 1300
MAIN_WINDOW_DEFAULT_HEIGHT = 680

# Размеры диалогов
DIALOG_MIN_WIDTH = 600
DIALOG_MIN_HEIGHT = 400

# Пути к стилям
STYLES_DIR = "ui/styles"

# ========== ВАЛЮТА ==========
DEFAULT_CURRENCY = "RUB"
CURRENCY_SYMBOL = "₽"
CURRENCY_FORMAT = "{:,.2f} ₽"  # формат с разделителем тысяч

# ========== ДАТА И ВРЕМЯ ==========
DATE_FORMAT = "YYYY-MM-DD"
DATE_DISPLAY_FORMAT = "%d.%m.%Y"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# ========== ЛОГИРОВАНИЕ ==========
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ========== КЭШИРОВАНИЕ ==========
CACHE_ENABLED = True
CACHE_TTL_ACCOUNTS = 60    # секунд
CACHE_TTL_CATEGORIES = 60  # секунд
CACHE_TTL_CREDIT_CARDS = 60  # секунд

# ========== ГРАФИКИ ==========
CHART_MIN_HEIGHT = 250
CHART_MAX_HEIGHT = 270
PIE_CHART_COLORS = [
    "#3498db", "#e74c3c", "#2ecc71", "#f39c12",
    "#9b59b6", "#1abc9c", "#e67e22", "#34495e",
    "#16a085", "#27ae60", "#2980b9", "#8e44ad"
]

# ========== ТИПЫ СЧЕТОВ ==========
ACCOUNT_TYPES = [
    "Cash",
    "Bank Account",
    "Credit Card",
    "Counterparty"
]

# ========== ТИПЫ ТРАНЗАКЦИЙ ==========
TRANSACTION_TYPES = [
    "income",
    "expense",
    "correct"
]

# ========== КАТЕГОРИИ ПО УМОЛЧАНИЮ ==========
DEFAULT_INCOME_CATEGORIES = [
    {"name": "Прочие доходы", "color": "#2ecc71", "icon": "💰"}
]

DEFAULT_EXPENSE_CATEGORIES = [
    {"name": "Прочие расходы", "color": "#e74c3c", "icon": "🛒"}
]

# ========== СИСТЕМНЫЕ КАТЕГОРИИ ==========
SYSTEM_CATEGORIES = []

# ========== РЕЗЕРВНОЕ КОПИРОВАНИЕ ==========
BACKUP_DIR = "backups"
BACKUP_PREFIX = "budget_backup_"
BACKUP_SUFFIX = ".db"

# ========== CSV ИМПОРТ/ЭКСПОРТ ==========
CSV_ENCODING = "utf-8"
CSV_DELIMITER = ","
CSV_DATE_FORMATS = ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"]

# ========== ЛИМИТЫ ==========
MAX_TRANSACTIONS_DISPLAY = 100
MAX_CATEGORIES_DEPTH = 3  # максимальная глубина вложенности категорий
