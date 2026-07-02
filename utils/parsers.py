"""Утилиты для безопасного парсинга чисел и булевых значений."""

import logging
from typing import Any, Optional, Union

from .converters import safe_int, safe_float, safe_bool

logger = logging.getLogger(__name__)


def parse_int(
    value: Any,
    default: int = 0,
    raise_error: bool = False,
    log_error: bool = True
) -> int:
    """Безопасный парсинг целого числа.

    Обрабатывает строки, числа, None и другие типы.
    Поддерживает замену запятой на точку в строковых представлениях.

    Args:
        value: Значение для преобразования
        default: Значение по умолчанию, если преобразование не удалось
        raise_error: Если True, выбрасывает ValueError при ошибке преобразования
        log_error: Если True, логирует ошибку преобразования

    Returns:
        Преобразованное целое число или default

    Raises:
        ValueError: Если raise_error=True и преобразование не удалось
    """
    if value is None:
        return default

    # Для строк выполняем предварительную обработку
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return default
        # Заменяем запятую на точку для корректного парсинга чисел с дробной частью
        # Например, "1,234" -> "1.234"
        processed = stripped.replace(',', '.')
        # Удаляем лишние пробелы вокруг знака минус
        processed = processed.replace(' ', '')
    else:
        processed = value

    if raise_error:
        # Строгий режим: пробуем преобразовать, при ошибке выбрасываем исключение
        try:
            # Прямое преобразование с обработкой строк
            if isinstance(processed, str):
                # Заменяем запятую на точку и удаляем пробелы
                processed_num = processed.replace(',', '.').replace(' ', '')
                # Пробуем преобразовать в float, затем в int (как safe_int)
                return int(float(processed_num))
            else:
                return int(processed)
        except (ValueError, TypeError, AttributeError) as e:
            if log_error:
                logger.debug(f"Ошибка парсинга целого числа: {value!r} -> {e}")
            raise ValueError(f"Некорректное целое число: {value!r}") from e
    else:
        # Безопасный режим: используем safe_int
        try:
            result = safe_int(processed, default=default)
            return result
        except (ValueError, TypeError, AttributeError) as e:
            if log_error:
                logger.debug(f"Ошибка парсинга целого числа: {value!r} -> {e}")
            return default


def parse_float(
    value: Any,
    default: float = 0.0,
    raise_error: bool = False,
    log_error: bool = True
) -> float:
    """Безопасный парсинг вещественного числа.

    Обрабатывает строки, числа, None и другие типы.
    Поддерживает замену запятой на точку в строковых представлениях.

    Args:
        value: Значение для преобразования
        default: Значение по умолчанию, если преобразование не удалось
        raise_error: Если True, выбрасывает ValueError при ошибке преобразования
        log_error: Если True, логирует ошибку преобразования

    Returns:
        Преобразованное вещественное число или default

    Raises:
        ValueError: Если raise_error=True и преобразование не удалось
    """
    if value is None:
        return default

    # Для строк выполняем предварительную обработку
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return default
        # Заменяем запятую на точку
        processed = stripped.replace(',', '.')
        # Удаляем пробелы между цифрами (например, "1 234.56" -> "1234.56")
        # Но оставляем пробел как разделитель тысяч? В проекте используется пробел как разделитель тысяч.
        # Удаляем все пробелы для упрощения
        processed = processed.replace(' ', '')
    else:
        processed = value

    if raise_error:
        # Строгий режим: пробуем преобразовать, при ошибке выбрасываем исключение
        try:
            # Прямое преобразование с обработкой строк
            if isinstance(processed, str):
                # Заменяем запятую на точку и удаляем пробелы
                processed_num = processed.replace(',', '.').replace(' ', '')
                return float(processed_num)
            else:
                return float(processed)
        except (ValueError, TypeError, AttributeError) as e:
            if log_error:
                logger.debug(f"Ошибка парсинга вещественного числа: {value!r} -> {e}")
            raise ValueError(f"Некорректное число: {value!r}") from e
    else:
        # Безопасный режим: используем safe_float
        try:
            result = safe_float(processed, default=default)
            return result
        except (ValueError, TypeError, AttributeError) as e:
            if log_error:
                logger.debug(f"Ошибка парсинга вещественного числа: {value!r} -> {e}")
            return default


def parse_bool(
    value: Any,
    default: bool = False,
    raise_error: bool = False,
    log_error: bool = True
) -> bool:
    """Безопасный парсинг булевого значения.

    Поддерживает строки ('true', 'false', '1', '0', 'да', 'нет'),
    числа (0 -> False, не-0 -> True), булевы значения.

    Args:
        value: Значение для преобразования
        default: Значение по умолчанию, если преобразование не удалось
        raise_error: Если True, выбрасывает ValueError при ошибке преобразования
        log_error: Если True, логирует ошибку преобразования

    Returns:
        Преобразованное булево значение или default

    Raises:
        ValueError: Если raise_error=True и преобразование не удалось
    """
    if value is None:
        return default

    if raise_error:
        # Строгий режим: пробуем преобразовать, при ошибке выбрасываем исключение
        # Повторяем логику safe_bool, но с исключением
        if value is None:
            return default
        # Уже bool
        if isinstance(value, bool):
            return value
        # Числа
        if isinstance(value, (int, float)):
            return bool(value)
        # Строки
        if isinstance(value, str):
            lower = value.lower().strip()
            if lower in ('true', '1', 'yes', 'on', 'да'):
                return True
            elif lower in ('false', '0', 'no', 'off', 'нет'):
                return False
        # Если дошли сюда, значение не распознано
        if log_error:
            logger.debug(f"Ошибка парсинга булевого значения: {value!r}")
        raise ValueError(f"Некорректное булево значение: {value!r}")
    else:
        # Безопасный режим: используем safe_bool
        try:
            result = safe_bool(value, default=default)
            return result
        except (ValueError, TypeError, AttributeError) as e:
            if log_error:
                logger.debug(f"Ошибка парсинга булевого значения: {value!r} -> {e}")
            return default


# Алиасы для обратной совместимости
parse_integer = parse_int
parse_number = parse_float
parse_boolean = parse_bool