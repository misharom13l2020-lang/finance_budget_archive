"""
Презентер для управления счетами по паттерну MVP.
Использует новую модульную архитектуру core/db.
"""

import logging
from typing import List, Dict, Any, Optional
from PySide6.QtCore import QObject, Signal

from core.db import Database
from core.db.models import Account
from services.account_service import AccountService
from utils.validators import validate_account_type, validate_amount
from utils.converters import safe_float, safe_int, safe_str


logger = logging.getLogger(__name__)


class AccountPresenter(QObject):
    """
    Презентер для диалога управления счетами.
    Обрабатывает бизнес-логику и взаимодействует с моделью (Database).
    """
    
    # Сигналы для обновления View
    accounts_loaded = Signal(list)  # список объектов Account
    account_added = Signal(Account)    # добавленный счет
    account_updated = Signal(Account)  # обновленный счет
    account_deleted = Signal(int)   # ID удаленного счета
    error_occurred = Signal(str)    # сообщение об ошибке
    validation_failed = Signal(dict)  # ошибки валидации {field: error}
    
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.account_service = AccountService(db.accounts)
        
    def load_accounts(self, active_only: bool = True, include_system: bool = False) -> List[Account]:
        """
        Загружает счета из базы данных и эмитит сигнал accounts_loaded.
        
        Returns:
            Список объектов Account.
        """
        try:
            accounts = self.account_service.get_all_accounts(active_only=active_only, include_system=include_system)
            self.accounts_loaded.emit(accounts)
            logger.debug(f"Загружено {len(accounts)} счетов")
            return accounts
        except Exception as e:
            error_msg = f"Ошибка загрузки счетов: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return []
    
    def add_account(self, data: Dict[str, Any]) -> Optional[int]:
        """
        Добавляет новый счет.
        
        Args:
            data: словарь с данными счета.
            
        Returns:
            ID созданного счета или None при ошибке.
        """
        # Валидация
        errors = self.validate_account_data(data)
        if errors:
            self.validation_failed.emit(errors)
            return None
        
        try:
            success, result = self.account_service.create_account(data)
            if success:
                account = result  # result is Account object
                logger.info(f"Добавлен счет ID {account.id}: {account.name}")
                self.account_added.emit(account)
                return account.id
            else:
                # result is error message
                error_msg = f"Ошибка добавления счета: {result}"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                return None
        except Exception as e:
            error_msg = f"Ошибка добавления счета: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return None
    
    def update_account(self, account_id: int, data: Dict[str, Any]) -> bool:
        """
        Обновляет существующий счет.
        
        Args:
            account_id: ID счета.
            data: словарь с обновляемыми полями.
            
        Returns:
            True при успехе, False при ошибке.
        """
        # Валидация
        errors = self.validate_account_data(data, for_update=True)
        if errors:
            self.validation_failed.emit(errors)
            return False
        
        try:
            success, result = self.account_service.update_account(account_id, data)
            if success:
                account = result  # result is Account object
                logger.info(f"Обновлен счет ID {account_id}")
                self.account_updated.emit(account)
                return True
            else:
                error_msg = f"Не удалось обновить счет ID {account_id}: {result}"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                return False
        except Exception as e:
            error_msg = f"Ошибка обновления счета {account_id}: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    def delete_account(self, account_id: int) -> Dict[str, Any]:
        """
        Удаляет счет по ID с проверкой связанных операций.
        
        Args:
            account_id: ID счета.
            
        Returns:
            Словарь результата (как delete_account_with_checks).
            Ключи: success (bool), can_delete (bool), message (str),
                   operations (list), total_operations (int), account_name (str).
        """
        try:
            success, result = self.account_service.delete_account(account_id)
            if success:
                logger.info(f"Удален счет ID {account_id}")
                self.account_deleted.emit(account_id)
                return {
                    'success': True,
                    'can_delete': True,
                    'message': result,
                    'operations': [],
                    'total_operations': 0,
                    'account_name': ''
                }
            else:
                # result is error message or details
                logger.warning(f"Не удалось удалить счет ID {account_id}: {result}")
                # Пытаемся извлечь детали из сообщения (если есть связанные операции)
                # В текущей реализации сервис возвращает строку, а не структурированный результат.
                # Для совместимости возвращаем словарь с can_delete = False если есть связанные операции.
                # Определим по наличию ключевых слов.
                can_delete = "Связанные операции" not in str(result)
                return {
                    'success': False,
                    'can_delete': can_delete,
                    'message': result,
                    'operations': [],
                    'total_operations': 0,
                    'account_name': ''
                }
        except Exception as e:
            error_msg = f"Ошибка удаления счета {account_id}: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'message': error_msg,
                'can_delete': True,
                'operations': [],
                'total_operations': 0,
                'account_name': ''
            }
    
    def validate_account_data(self, data: Dict[str, Any], for_update: bool = False) -> Dict[str, str]:
        """
        Валидирует данные счета.
        
        Args:
            data: словарь с данными.
            for_update: True если валидация для обновления (некоторые поля могут отсутствовать).
            
        Returns:
            Словарь с ошибками {поле: сообщение}, пустой если ошибок нет.
        """
        errors = {}
        
        # Название
        name = data.get('name')
        if not for_update or 'name' in data:
            if not name or not safe_str(name).strip():
                errors['name'] = "Название счета обязательно"
            elif len(safe_str(name).strip()) < 2:
                errors['name'] = "Название должно содержать минимум 2 символа"
        
        # Тип счета
        account_type = data.get('type')
        if not for_update or 'type' in data:
            if account_type and not validate_account_type(account_type):
                errors['type'] = f"Недопустимый тип счета: {account_type}"
        
        # Начальный баланс
        initial_balance = data.get('initial_balance')
        if initial_balance is not None:
            try:
                val = safe_float(initial_balance)
                if not validate_amount(val, min_value=-1000000, max_value=1000000):
                    errors['initial_balance'] = "Некорректная сумма начального баланса"
            except (ValueError, TypeError):
                errors['initial_balance'] = "Начальный баланс должен быть числом"
        
        # Кредитный лимит (для кредитных карт)
        credit_limit = data.get('credit_limit')
        if credit_limit is not None:
            try:
                val = safe_float(credit_limit)
                if val < 0:
                    errors['credit_limit'] = "Кредитный лимит не может быть отрицательным"
            except (ValueError, TypeError):
                errors['credit_limit'] = "Кредитный лимит должен быть числом"
        
        # День платежа
        payment_due_day = data.get('payment_due_day')
        if payment_due_day is not None:
            try:
                val = safe_int(payment_due_day)
                if val < 1 or val > 31:
                    errors['payment_due_day'] = "День платежа должен быть от 1 до 31"
            except (ValueError, TypeError):
                errors['payment_due_day'] = "День платежа должен быть целым числом"
        
        # Минимальный платеж (%)
        min_payment_percent = data.get('min_payment_percent')
        if min_payment_percent is not None:
            try:
                val = safe_float(min_payment_percent)
                if val < 0 or val > 100:
                    errors['min_payment_percent'] = "Минимальный платеж должен быть от 0 до 100%"
            except (ValueError, TypeError):
                errors['min_payment_percent'] = "Минимальный платеж должен быть числом"
        
        return errors
    
    # --- Вспомогательные методы ---
    
    def _account_to_dict(self, account: Account) -> Dict[str, Any]:
        """Преобразует объект Account в словарь для View."""
        return {
            'id': account.id,
            'name': account.name,
            'type': account.type,
            'initial_balance': account.initial_balance,
            'current_balance': account.current_balance,
            'credit_limit': getattr(account, 'credit_limit', 0.0),
            'payment_due_day': getattr(account, 'payment_due_day', 1),
            'min_payment_percent': getattr(account, 'min_payment_percent', 5.0),
            'currency': getattr(account, 'currency', 'RUB'),
            'is_system': getattr(account, 'is_system', False),
            'is_active': getattr(account, 'is_active', True),
            'created_at': getattr(account, 'created_at', None),
        }
    
    def _dict_to_account(self, data: Dict[str, Any], existing: Optional[Account] = None) -> Account:
        """
        Преобразует словарь в объект Account.
        Если передан existing, обновляет его поля.
        """
        from core.db.models import Account
        
        # Базовые поля
        fields = {
            'name': safe_str(data.get('name', '')) if 'name' in data else None,
            'type': data.get('type') if 'type' in data else None,
            'initial_balance': safe_float(data.get('initial_balance')) if 'initial_balance' in data else None,
            'current_balance': safe_float(data.get('current_balance')) if 'current_balance' in data else None,
            'credit_limit': safe_float(data.get('credit_limit')) if 'credit_limit' in data else None,
            'payment_due_day': safe_int(data.get('payment_due_day')) if 'payment_due_day' in data else None,
            'min_payment_percent': safe_float(data.get('min_payment_percent')) if 'min_payment_percent' in data else None,
            'currency': safe_str(data.get('currency', 'RUB')) if 'currency' in data else None,
            'is_system': bool(data.get('is_system')) if 'is_system' in data else None,
            'is_active': bool(data.get('is_active', True)) if 'is_active' in data else None,
        }
        
        # Убираем None значения
        fields = {k: v for k, v in fields.items() if v is not None}
        
        if existing:
            # Обновляем существующий объект
            for key, value in fields.items():
                setattr(existing, key, value)
            return existing
        else:
            # Создаем новый объект
            # Устанавливаем значения по умолчанию для отсутствующих полей
            defaults = {
                'initial_balance': 0.0,
                'current_balance': 0.0,
                'credit_limit': 0.0,
                'payment_due_day': 1,
                'min_payment_percent': 5.0,
                'currency': 'RUB',
                'is_system': False,
                'is_active': True,
            }
            for key, default in defaults.items():
                if key not in fields:
                    fields[key] = default
            
            # Обязательные поля
            if 'name' not in fields:
                fields['name'] = ''
            if 'type' not in fields:
                fields['type'] = 'Bank Account'
            
            return Account(**fields)