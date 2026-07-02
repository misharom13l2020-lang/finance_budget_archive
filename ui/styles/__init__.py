"""Модуль для работы со стилями приложения."""

import os
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QApplication
from .theme_manager import ThemeManager


def get_styles_path() -> Path:
    """Возвращает путь к директории со стилями."""
    return Path(__file__).parent


def load_global_styles() -> str:
    """
    Загружает глобальные стили из файла global.qss.
    
    Returns:
        Строка с содержимым файла global.qss.
        
    Raises:
        FileNotFoundError: если файл global.qss не найден.
    """
    styles_path = get_styles_path() / "global.qss"
    if not styles_path.exists():
        raise FileNotFoundError(f"Файл стилей не найден: {styles_path}")
    
    with open(styles_path, "r", encoding="utf-8") as f:
        return f.read()


def load_stylesheet(filename: str) -> str:
    """
    Загружает стили из указанного файла в директории стилей.
    
    Args:
        filename: имя файла стилей (например, "account_dialog.qss")
        
    Returns:
        Строка с содержимым файла стилей.
        
    Raises:
        FileNotFoundError: если файл не найден.
    """
    styles_path = get_styles_path() / filename
    if not styles_path.exists():
        raise FileNotFoundError(f"Файл стилей не найден: {styles_path}")
    
    with open(styles_path, "r", encoding="utf-8") as f:
        return f.read()


def apply_global_styles(app: Optional[QApplication] = None) -> None:
    """
    Применяет глобальные стили ко всему приложению.
    
    Args:
        app: экземпляр QApplication. Если None, используется QApplication.instance()
    """
    if app is None:
        app = QApplication.instance()
        if app is None:
            raise RuntimeError("Нет активного экземпляра QApplication")
    
    try:
        stylesheet = load_global_styles()
        app.setStyleSheet(stylesheet)
    except FileNotFoundError as e:
        print(f"Предупреждение: не удалось загрузить глобальные стили: {e}")
        # Применяем минимальные стили по умолчанию
        app.setStyleSheet("")


def apply_stylesheet(widget, filename: str) -> None:
    """
    Применяет стили из файла к конкретному виджету.
    
    Args:
        widget: виджет Qt, к которому применяются стили
        filename: имя файла стилей
    """
    try:
        stylesheet = load_stylesheet(filename)
        widget.setStyleSheet(stylesheet)
    except FileNotFoundError as e:
        print(f"Предупреждение: не удалось загрузить стили {filename}: {e}")


def get_available_styles() -> list[str]:
    """Возвращает список доступных файлов стилей в директории."""
    styles_dir = get_styles_path()
    return [f.name for f in styles_dir.glob("*.qss") if f.is_file()]


# Предопределенные цветовые константы для использования в коде
COLORS = {
    "primary": "#2c3e50",
    "primary_light": "#34495e",
    "primary_dark": "#1a252f",
    "secondary": "#3498db",
    "secondary_light": "#5dade2",
    "secondary_dark": "#21618c",
    "success": "#27ae60",
    "success_light": "#2ecc71",
    "success_dark": "#1e8449",
    "danger": "#e74c3c",
    "danger_light": "#ec7063",
    "danger_dark": "#c0392b",
    "warning": "#f39c12",
    "warning_light": "#f5b041",
    "warning_dark": "#d68910",
    "info": "#17a2b8",
    "info_light": "#48c9b0",
    "info_dark": "#138496",
    "background": "#f8f9fa",
    "surface": "#ffffff",
    "border": "#dee2e6",
    "text": "#212529",
    "text_secondary": "#6c757d",
    "disabled": "#adb5bd",
}


def get_color(name: str) -> str:
    """
    Возвращает цвет по имени из палитры.
    
    Args:
        name: имя цвета (например, "primary", "success_light")
        
    Returns:
        Строка с hex-значением цвета.
        
    Raises:
        KeyError: если цвет с таким именем не найден.
    """
    if name not in COLORS:
        raise KeyError(f"Цвет '{name}' не найден. Доступные цвета: {list(COLORS.keys())}")
    return COLORS[name]


__all__ = ['ThemeManager']
