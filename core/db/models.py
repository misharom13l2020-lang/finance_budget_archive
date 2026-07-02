"""
Модели данных (dataclass) для сущностей базы данных.
Соответствуют структуре таблиц в SQLite.
"""

from dataclasses import dataclass, field, asdict, fields
from typing import Optional, List, Any, Dict
from datetime import datetime, date as date_type


@dataclass
class BaseModel:
    """Базовый класс для всех моделей с общими полями и методами."""
    id: Optional[int] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать модель в словарь, исключая None значения."""
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModel':
        """Создать экземпляр модели из словаря."""
        # Фильтруем только поля, которые есть в классе
        field_names = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in field_names}
        return cls(**filtered)

    def __post_init__(self):
        """Базовая валидация после инициализации."""
        pass


@dataclass
class Account(BaseModel):
    """Модель счёта."""
    name: str = ""
    type: str = ""  # 'Cash', 'Bank Account', 'Credit Card', 'Counterparty'
    initial_balance: float = 0.0
    current_balance: float = 0.0
    credit_limit: float = 0.0
    payment_due_day: int = 1
    min_payment_percent: float = 5.0
    last_payment_date: Optional[str] = None
    is_active: bool = True
    is_system: bool = False
    currency: str = "RUB"

    def __post_init__(self):
        """Валидация счёта."""
        super().__post_init__()
        if self.type not in ('Cash', 'Bank Account', 'Credit Card', 'Counterparty'):
            raise ValueError(f"Недопустимый тип счёта: {self.type}")
        if self.currency not in ('RUB', 'USD', 'EUR'):
            # Можно расширить список валют
            pass


@dataclass
class Category(BaseModel):
    """Модель категории доходов/расходов."""
    name: str = ""
    type: str = ""  # 'income' или 'expense'
    budget_amount_monthly: float = 0.0
    parent_id: Optional[int] = None
    color: str = "#3498db"
    icon: str = ""
    is_system: bool = False

    def __post_init__(self):
        """Валидация категории."""
        super().__post_init__()
        if self.type not in ('income', 'expense'):
            raise ValueError(f"Недопустимый тип категории: {self.type}")
        if self.parent_id is not None and self.parent_id == self.id:
            raise ValueError("Категория не может быть родителем самой себя")


@dataclass
class Transaction(BaseModel):
    """Модель транзакции."""
    date: str = ""  # YYYY-MM-DD
    amount: float = 0.0
    type: str = ""  # 'income', 'expense', 'refund', 'correct'
    category_id: Optional[int] = None
    description: str = ""
    account_id: int = 0
    quantity: float = 1.0
    unit_price: Optional[float] = None  # вычисляемое поле
    original_transaction_id: Optional[int] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        """Валидация транзакции."""
        super().__post_init__()
        if self.type not in ('income', 'expense', 'refund', 'correct'):
            raise ValueError(f"Недопустимый тип транзакции: {self.type}")
        if self.type in ('income', 'expense', 'refund') and self.category_id is None:
            raise ValueError(f"Для типа '{self.type}' должна быть указана категория")
        if self.type == 'correct' and self.category_id is not None:
            raise ValueError("Для корректирующей транзакции категория не указывается")
        if self.type == 'refund' and self.original_transaction_id is None:
            raise ValueError("Для возврата должен быть указан original_transaction_id")
        # Проверка даты формата YYYY-MM-DD
        if self.date and not (len(self.date) == 10 and self.date[4] == '-' and self.date[7] == '-'):
            raise ValueError(f"Некорректный формат даты: {self.date}, ожидается YYYY-MM-DD")


@dataclass
class Transfer(BaseModel):
    """Модель перевода между счетами."""
    date: str = ""  # YYYY-MM-DD
    amount: float = 0.0
    from_account_id: int = 0
    to_account_id: int = 0
    description: str = ""

    def __post_init__(self):
        """Валидация перевода."""
        super().__post_init__()
        if self.from_account_id == self.to_account_id:
            raise ValueError("Счёт отправителя и получателя не могут совпадать")
        if self.amount <= 0:
            raise ValueError("Сумма перевода должна быть положительной")
        if self.date and not (len(self.date) == 10 and self.date[4] == '-' and self.date[7] == '-'):
            raise ValueError(f"Некорректный формат даты: {self.date}, ожидается YYYY-MM-DD")


@dataclass
class Budget(BaseModel):
    """Модель бюджета на месяц."""
    category_id: int = 0
    month_year: str = ""  # YYYY-MM
    planned_amount: float = 0.0
    actual_amount: float = 0.0

    def __post_init__(self):
        """Валидация бюджета."""
        super().__post_init__()
        if not (len(self.month_year) == 7 and self.month_year[4] == '-'):
            raise ValueError(f"Некорректный формат месяца: {self.month_year}, ожидается YYYY-MM")
        if self.planned_amount < 0:
            raise ValueError("Планируемая сумма не может быть отрицательной")
        if self.actual_amount < 0:
            raise ValueError("Фактическая сумма не может быть отрицательной")


@dataclass
class Loan(BaseModel):
    """Модель займа."""
    account_id: int = 0
    counterparty_account_id: int = 0
    contact_name: str = ""
    loan_type: str = ""  # 'issued' (выдан), 'received' (получен)
    loan_amount: float = 0.0
    outstanding_amount: float = 0.0
    interest_rate: float = 0.0
    issue_date: str = ""  # YYYY-MM-DD
    due_date: Optional[str] = None
    description: str = ""
    status: str = "active"  # 'active', 'paid', 'default'

    def __post_init__(self):
        """Валидация займа."""
        super().__post_init__()
        if self.loan_type not in ('issued', 'received'):
            raise ValueError(f"Недопустимый тип займа: {self.loan_type}")
        if self.status not in ('active', 'paid', 'default'):
            raise ValueError(f"Недопустимый статус: {self.status}")
        if self.loan_amount <= 0:
            raise ValueError("Сумма займа должна быть положительной")
        if self.outstanding_amount < 0 or self.outstanding_amount > self.loan_amount:
            raise ValueError("Непогашенная сумма должна быть в пределах от 0 до суммы займа")
        if self.issue_date and not (len(self.issue_date) == 10 and self.issue_date[4] == '-' and self.issue_date[7] == '-'):
            raise ValueError(f"Некорректный формат даты выдачи: {self.issue_date}")
        if self.due_date and not (len(self.due_date) == 10 and self.due_date[4] == '-' and self.due_date[7] == '-'):
            raise ValueError(f"Некорректный формат даты погашения: {self.due_date}")


@dataclass
class LoanPayment(BaseModel):
    """Модель платежа по займу."""
    loan_id: int = 0
    payment_date: str = ""  # YYYY-MM-DD
    payment_amount: float = 0.0
    interest_amount: float = 0.0
    principal_amount: float = 0.0
    description: str = ""

    def __post_init__(self):
        """Валидация платежа."""
        super().__post_init__()
        if self.payment_amount <= 0:
            raise ValueError("Сумма платежа должна быть положительной")
        if self.interest_amount < 0 or self.principal_amount < 0:
            raise ValueError("Суммы процентов и основного долга не могут быть отрицательными")
        if abs(self.interest_amount + self.principal_amount - self.payment_amount) > 0.01:
            raise ValueError("Сумма платежа должна равняться сумме процентов и основного долга")
        if self.payment_date and not (len(self.payment_date) == 10 and self.payment_date[4] == '-' and self.payment_date[7] == '-'):
            raise ValueError(f"Некорректный формат даты платежа: {self.payment_date}")