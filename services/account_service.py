"""
Сервис для работы со счетами (бизнес-логика).
Использует новую модульную архитектуру core/db.
"""

import logging
from typing import List, Optional, Tuple, Dict, Any
from core.db.repositories.account_repository import AccountRepository
from core.db.models import Account
from utils.validators import (
    validate_account_name,
    validate_account_type,
    validate_credit_limit,
    validate_payment_day,
    validate_min_payment_percent,
    validate_required_fields,
    validate_positive_number,
    validate_in_range
)
from utils.converters import (
    safe_float,
    safe_int,
    safe_str,
    safe_bool
)

logger = logging.getLogger(__name__)


class AccountService:
    """Сервис для бизнес-логики работы со счетами."""

    def __init__(self, account_repository: AccountRepository):
        """
        Args:
            account_repository: Репозиторий для работы со счетами.
        """
        self.repo = account_repository

    def get_all_accounts(
        self,
        active_only: bool = True,
        include_system: bool = False
    ) -> List[Account]:
        """
        Получить все счета.

        Args:
            active_only: Только активные счета.
            include_system: Включать системные счета.

        Returns:
            Список объектов Account.
        """
        try:
            accounts = self.repo.get_accounts(
                active_only=active_only,
                include_system=include_system
            )
            logger.debug(f"Получено {len(accounts)} счетов")
            return accounts
        except Exception as e:
            logger.error(f"Ошибка при получении счетов: {e}")
            raise

    def get_account_by_id(self, account_id: int) -> Optional[Account]:
        """
        Получить счет по ID.

        Args:
            account_id: ID счета.

        Returns:
            Объект Account или None, если счет не найден.
        """
        try:
            account = self.repo.get_by_id(account_id)
            if account is None:
                logger.debug(f"Счет с ID {account_id} не найден")
            return account
        except Exception as e:
            logger.error(f"Ошибка при получении счета {account_id}: {e}")
            raise

    def create_account(self, account_data: dict) -> Tuple[bool, Any]:
        """
        Создать новый счет.

        Args:
            account_data: Словарь с данными счета.

        Returns:
            Кортеж (успех, результат):
            - (True, Account) при успешном создании
            - (False, str) при ошибке валидации
            - (False, Exception) при ошибке БД
        """
        # Валидация данных
        is_valid, error_msg = self.validate_account_data(account_data)
        if not is_valid:
            logger.warning(f"Валидация не пройдена: {error_msg}")
            return False, error_msg

        try:
            # Преобразование данных в модель Account
            account = self._dict_to_account(account_data)
            # Установка начального баланса
            if account.current_balance == 0.0:
                account.current_balance = account.initial_balance

            # Сохранение в БД
            account_id = self.repo.add(account)
            account.id = account_id
            logger.info(f"Создан новый счет: {account.name} (ID: {account_id})")
            return True, account
        except Exception as e:
            logger.error(f"Ошибка при создании счета: {e}")
            return False, e

    def update_account(self, account_id: int, account_data: dict) -> Tuple[bool, Any]:
        """
        Обновить существующий счет.

        Args:
            account_id: ID обновляемого счета.
            account_data: Словарь с обновляемыми данными.

        Returns:
            Кортеж (успех, результат):
            - (True, Account) при успешном обновлении
            - (False, str) при ошибке валидации или если счет не найден
            - (False, Exception) при ошибке БД
        """
        # Проверка существования счета
        existing = self.get_account_by_id(account_id)
        if existing is None:
            return False, f"Счет с ID {account_id} не найден"

        # Валидация данных (частичное обновление)
        is_valid, error_msg = self.validate_account_data(account_data, partial=True)
        if not is_valid:
            logger.warning(f"Валидация не пройдена: {error_msg}")
            return False, error_msg

        try:
            # Объединяем существующие данные с новыми
            updated_data = existing.to_dict()
            updated_data.update(account_data)
            # Преобразуем в модель
            updated_account = self._dict_to_account(updated_data)
            updated_account.id = account_id

            # Обновляем в БД
            success = self.repo.update(account_id, updated_account)
            if success:
                logger.info(f"Обновлен счет ID {account_id}")
                return True, updated_account
            else:
                return False, "Не удалось обновить счет в БД"
        except Exception as e:
            logger.error(f"Ошибка при обновлении счета {account_id}: {e}")
            return False, e

    def delete_account(self, account_id: int) -> Tuple[bool, Any]:
        """
        Удалить счет с проверкой связанных операций.

        Args:
            account_id: ID удаляемого счета.

        Returns:
            Кортеж (успех, результат):
            - (True, str) при успешном удалении
            - (False, str) при ошибке (счет не найден, есть связанные операции и т.д.)
            - (False, Exception) при ошибке БД
        """
        # Используем встроенную проверку репозитория
        try:
            result = self.repo.delete_account_with_checks(account_id)
            if result.get('success'):
                return True, result.get('message', 'Счет успешно удален')
            else:
                # Если есть связанные операции, возвращаем детали
                if result.get('can_delete') is False:
                    operations = result.get('operations', [])
                    total = result.get('total_operations', 0)
                    msg = result.get('message', '')
                    details = f"{msg}. Связанные операции: {', '.join(operations)}"
                    return False, details
                else:
                    return False, result.get('message', 'Не удалось удалить счет')
        except Exception as e:
            logger.error(f"Ошибка при удалении счета {account_id}: {e}")
            return False, e

    def validate_account_data(self, account_data: dict, partial: bool = False) -> Tuple[bool, str]:
        """
        Валидация данных счета.

        Args:
            account_data: Словарь с данными счета.
            partial: Если True, проверяются только присутствующие поля (для обновления).

        Returns:
            Кортеж (валидно, сообщение об ошибке).
        """
        # Обязательные поля при создании
        required_fields = ['name', 'type']
        if not partial:
            ok, missing = validate_required_fields(account_data, required_fields)
            if not ok:
                return False, f"Отсутствуют обязательные поля: {', '.join(missing)}"

        # Валидация имени
        if 'name' in account_data:
            name = safe_str(account_data['name'])
            ok, msg = validate_account_name(name)
            if not ok:
                return False, f"Некорректное имя счета: {msg}"

        # Валидация типа
        if 'type' in account_data:
            acc_type = safe_str(account_data['type'])
            if not validate_account_type(acc_type):
                return False, f"Недопустимый тип счета: {acc_type}"

        # Валидация начального баланса
        if 'initial_balance' in account_data:
            balance = account_data['initial_balance']
            if not validate_positive_number(balance):
                return False, "Начальный баланс должен быть положительным числом"

        # Валидация кредитного лимита
        if 'credit_limit' in account_data:
            limit = safe_str(account_data['credit_limit'])
            ok, msg = validate_credit_limit(limit)
            if not ok:
                return False, f"Некорректный кредитный лимит: {msg}"

        # Валидация дня платежа
        if 'payment_due_day' in account_data:
            day = safe_str(account_data['payment_due_day'])
            ok, msg = validate_payment_day(day)
            if not ok:
                return False, f"Некорректный день платежа: {msg}"

        # Валидация минимального процента платежа
        if 'min_payment_percent' in account_data:
            percent = safe_str(account_data['min_payment_percent'])
            ok, msg = validate_min_payment_percent(percent)
            if not ok:
                return False, f"Некорректный минимальный процент платежа: {msg}"

        # Валидация валюты (если указана)
        if 'currency' in account_data:
            currency = safe_str(account_data['currency'])
            if currency not in ('RUB', 'USD', 'EUR'):
                return False, f"Недопустимая валюта: {currency}"

        # Валидация флагов
        if 'is_active' in account_data:
            # просто проверяем, что можно преобразовать в bool
            pass
        if 'is_system' in account_data:
            pass

        return True, ""

    def _dict_to_account(self, data: dict) -> Account:
        """
        Преобразовать словарь в объект Account с использованием безопасных конвертеров.

        Args:
            data: Словарь с данными счета.

        Returns:
            Объект Account.
        """
        return Account(
            id=safe_int(data.get('id')),
            name=safe_str(data.get('name', '')),
            type=safe_str(data.get('type', '')),
            initial_balance=safe_float(data.get('initial_balance', 0.0)),
            current_balance=safe_float(data.get('current_balance', 0.0)),
            credit_limit=safe_float(data.get('credit_limit', 0.0)),
            payment_due_day=safe_int(data.get('payment_due_day', 1)),
            min_payment_percent=safe_float(data.get('min_payment_percent', 5.0)),
            last_payment_date=safe_str(data.get('last_payment_date')),
            is_active=safe_bool(data.get('is_active', True)),
            is_system=safe_bool(data.get('is_system', False)),
            currency=safe_str(data.get('currency', 'RUB')),
            created_at=safe_str(data.get('created_at'))
        )

    def get_credit_cards(self) -> List[Account]:
        """
        Получить все кредитные карты.

        Returns:
            Список объектов Account типа 'Credit Card'.
        """
        try:
            return self.repo.get_credit_cards()
        except Exception as e:
            logger.error(f"Ошибка при получении кредитных карт: {e}")
            raise

    def get_counterparty_accounts(self) -> List[Account]:
        """
        Получить все счета контрагентов.

        Returns:
            Список объектов Account типа 'Counterparty'.
        """
        try:
            return self.repo.get_counterparty_accounts()
        except Exception as e:
            logger.error(f"Ошибка при получении счетов контрагентов: {e}")
            raise

    def update_account_balance(self, account_id: int, amount_change: float) -> bool:
        """
        Обновить баланс счета на указанную величину.

        Args:
            account_id: ID счета.
            amount_change: Изменение баланса (может быть отрицательным).

        Returns:
            True если обновление успешно, иначе False.
        """
        try:
            return self.repo.update_account_balance(account_id, amount_change)
        except Exception as e:
            logger.error(f"Ошибка при обновлении баланса счета {account_id}: {e}")
            return False