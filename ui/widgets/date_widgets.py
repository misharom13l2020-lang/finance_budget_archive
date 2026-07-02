# ui/widgets/date_widgets.py просто скопирован из в1 на pyside6
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QDateEdit, QToolButton, QCalendarWidget,
    QDialog, QVBoxLayout, QPushButton, QLabel, QFrame
)
from PySide6.QtCore import Qt, Signal, QDate, QSize
from PySide6.QtGui import QFont, QPalette, QColor
from datetime import date, timedelta

class DateNavigator(QWidget):
    """Виджет навигации по датам с кнопками перелистывания"""
    date_changed = Signal(QDate)
    
    def __init__(self, parent=None, default_date=None):
        super().__init__(parent)
        self._init_ui(default_date)
        self._setup_style()
    
    def _init_ui(self, default_date):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Кнопка быстрого перехода к сегодняшней дате
        today_btn = QToolButton()
        today_btn.setText("Сегодня")
        today_btn.setToolTip("Перейти к сегодняшней дате")
        today_btn.clicked.connect(self._go_to_today)
        today_btn.setFixedHeight(26)
        today_btn.setMinimumWidth(70)
        layout.addWidget(today_btn)
        
        # Кнопка предыдущего дня
        self.prev_btn = QToolButton()
        self.prev_btn.setText("◀")
        self.prev_btn.clicked.connect(self._prev_day)
        self.prev_btn.setToolTip("Предыдущий день")
        self.prev_btn.setFixedSize(26, 26)
        layout.addWidget(self.prev_btn)
        
        # Поле ввода даты
        self.date_edit = QDateEdit(default_date or QDate.currentDate())
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setFixedHeight(26)
        self.date_edit.setMinimumWidth(100)
        self.date_edit.dateChanged.connect(self._on_date_changed)
        layout.addWidget(self.date_edit)
        
        # Кнопка следующего дня
        self.next_btn = QToolButton()
        self.next_btn.setText("▶")
        self.next_btn.clicked.connect(self._next_day)
        self.next_btn.setToolTip("Следующий день")
        self.next_btn.setFixedSize(26, 26)
        layout.addWidget(self.next_btn)
        
        # Кнопка календаря
        calendar_btn = QToolButton()
        calendar_btn.setText("📅")
        calendar_btn.clicked.connect(self._show_calendar_popup)
        calendar_btn.setToolTip("Открыть календарь")
        calendar_btn.setFixedSize(26, 26)
        layout.addWidget(calendar_btn)
        
        layout.addStretch()
    
    def _setup_style(self):
        self.setStyleSheet("""
            QToolButton {
                border: 1px solid #ced4da;
                border-radius: 3px;
                background-color: white;
                font-size: 12px;
            }
            QToolButton:hover {
                background-color: #e9ecef;
            }
            QDateEdit {
                border: 1px solid #ced4da;
                border-radius: 3px;
                padding: 4px;
                font-size: 12px;
                background-color: white;
            }
            QDateEdit:focus {
                border: 1px solid #80bdff;
            }
            QDateEdit::drop-down {
                width: 20px;
                border-left: 1px solid #ced4da;
            }
        """)
    
    def _go_to_today(self):
        """Переходит к сегодняшней дате"""
        self.date_edit.setDate(QDate.currentDate())
    
    def _prev_day(self):
        """Переходит к предыдущему дню"""
        current_date = self.date_edit.date()
        prev_date = current_date.addDays(-1)
        self.date_edit.setDate(prev_date)
    
    def _next_day(self):
        """Переходит к следующему дню"""
        current_date = self.date_edit.date()
        next_date = current_date.addDays(1)
        self.date_edit.setDate(next_date)
    
    def _show_calendar_popup(self):
        """Показывает всплывающий календарь"""
        calendar_dialog = CalendarPopup(self)
        if calendar_dialog.exec():
            selected_date = calendar_dialog.selected_date()
            if selected_date:
                self.date_edit.setDate(selected_date)
    
    def _on_date_changed(self, date):
        """Обрабатывает изменение даты"""
        self.date_changed.emit(date)
    
    def get_date(self):
        """Возвращает текущую дату"""
        return self.date_edit.date()
    
    def set_date(self, date):
        """Устанавливает дату"""
        self.date_edit.setDate(date)
    
    def get_date_string(self, format="yyyy-MM-dd"):
        """Возвращает дату в виде строки"""
        return self.date_edit.date().toString(format)

class DateRangeSelector(QWidget):
    """Виджет выбора диапазона дат"""
    range_changed = Signal(QDate, QDate)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._setup_style()
    
    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        layout.addWidget(QLabel("С:"))
        
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setDisplayFormat("dd.MM.yyyy")
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate().addDays(-30))
        self.start_date_edit.setFixedHeight(26)
        self.start_date_edit.setMinimumWidth(100)
        self.start_date_edit.dateChanged.connect(self._on_date_changed)
        layout.addWidget(self.start_date_edit)
        
        layout.addWidget(QLabel("по:"))
        
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setDisplayFormat("dd.MM.yyyy")
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setFixedHeight(26)
        self.end_date_edit.setMinimumWidth(100)
        self.end_date_edit.dateChanged.connect(self._on_date_changed)
        layout.addWidget(self.end_date_edit)
        
        # Кнопки быстрого выбора периода
        quick_buttons_layout = QHBoxLayout()
        quick_buttons_layout.setSpacing(4)
        
        periods = [
            ("Сегодня", 0),
            ("Неделя", 7),
            ("Месяц", 30),
            ("3 месяца", 90),
            ("Год", 365)
        ]
        
        for text, days in periods:
            btn = QPushButton(text)
            btn.setFixedHeight(24)
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 11px;
                    padding: 2px 6px;
                    border: 1px solid #ced4da;
                    border-radius: 3px;
                    background-color: #f8f9fa;
                }
                QPushButton:hover {
                    background-color: #e9ecef;
                }
            """)
            if days == 0:
                btn.clicked.connect(self._set_today)
            else:
                btn.clicked.connect(lambda checked, d=days: self._set_period(d))
            quick_buttons_layout.addWidget(btn)
        
        layout.addLayout(quick_buttons_layout)
        layout.addStretch()
    
    def _setup_style(self):
        self.setStyleSheet("""
            QDateEdit {
                border: 1px solid #ced4da;
                border-radius: 3px;
                padding: 4px;
                font-size: 12px;
                background-color: white;
            }
            QDateEdit:focus {
                border: 1px solid #80bdff;
            }
            QLabel {
                font-size: 12px;
                color: #495057;
            }
        """)
    
    def _set_today(self):
        """Устанавливает период на сегодня"""
        today = QDate.currentDate()
        self.start_date_edit.setDate(today)
        self.end_date_edit.setDate(today)
    
    def _set_period(self, days):
        """Устанавливает период на указанное количество дней"""
        end_date = QDate.currentDate()
        start_date = end_date.addDays(-days)
        self.start_date_edit.setDate(start_date)
        self.end_date_edit.setDate(end_date)
    
    def _on_date_changed(self):
        """Обрабатывает изменение даты"""
        self.range_changed.emit(
            self.start_date_edit.date(),
            self.end_date_edit.date()
        )
    
    def get_dates(self):
        """Возвращает выбранные даты"""
        return self.start_date_edit.date(), self.end_date_edit.date()
    
    def set_dates(self, start_date, end_date):
        """Устанавливает даты"""
        self.start_date_edit.setDate(start_date)
        self.end_date_edit.setDate(end_date)

class CalendarPopup(QDialog):
    """Всплывающий календарь для выбора даты"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выбор даты")
        self.setModal(True)
        self.resize(300, 250)
        self._init_ui()
        self._setup_style()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Календарь
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        layout.addWidget(self.calendar)
        
        # Панель кнопок
        button_layout = QHBoxLayout()
        
        today_btn = QPushButton("Сегодня")
        today_btn.clicked.connect(self._set_today)
        button_layout.addWidget(today_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setDefault(True)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
    
    def _setup_style(self):
        self.setStyleSheet("""
            CalendarPopup {
                background-color: white;
            }
            QCalendarWidget {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
            QCalendarWidget QWidget {
                alternate-background-color: #f8f9fa;
            }
            QCalendarWidget QToolButton {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 3px;
                padding: 4px;
                font-weight: bold;
                color: #212529;
                min-width: 50px;
                max-width: 100px;
            }
            QCalendarWidget QToolButton:hover {
                background-color: #e9ecef;
            }
            QCalendarWidget QToolButton#qt_calendar_monthbutton,
            QCalendarWidget QToolButton#qt_calendar_yearbutton {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 3px;
                padding: 4px 8px;
                font-weight: bold;
                color: #212529;
                min-width: 60px;
                max-width: 120px;
            }
            QCalendarWidget QSpinBox {
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 3px;
                padding: 4px;
                min-width: 60px;
            }
            QCalendarWidget QMenu {
                background-color: white;
                border: 1px solid #dee2e6;
                min-width: 120px;
            }
            QCalendarWidget QAbstractItemView {
                selection-background-color: #007bff;
                selection-color: white;
                border: 1px solid #dee2e6;
            }
            QPushButton {
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
                min-width: 80px;
                border: 1px solid #ced4da;
                background-color: #f8f9fa;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
            QPushButton:default {
                background-color: #007bff;
                color: white;
                border: none;
            }
            QPushButton:default:hover {
                background-color: #0056b3;
            }
        """)
        
        # Настраиваем цвета календаря
        palette = self.calendar.palette()
        palette.setColor(QPalette.Highlight, QColor("#007bff"))
        palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        self.calendar.setPalette(palette)
        
    def _set_today(self):
        """Устанавливает сегодняшнюю дату"""
        self.calendar.setSelectedDate(QDate.currentDate())
    
    def selected_date(self):
        """Возвращает выбранную дату"""
        return self.calendar.selectedDate()

class DateUtils:
    """Утилиты для работы с датами"""
    
    @staticmethod
    def get_period_dates(period_name):
        """Возвращает даты начала и конца для заданного периода"""
        today = date.today()
        
        if period_name == "Сегодня":
            date_from = today
            date_to = today
        elif period_name == "Вчера":
            yesterday = today - timedelta(days=1)
            date_from = yesterday
            date_to = yesterday
        elif period_name == "Эта неделя":
            start_of_week = today - timedelta(days=today.weekday())
            date_from = start_of_week
            date_to = today
        elif period_name == "Прошлая неделя":
            start_of_last_week = today - timedelta(days=today.weekday() + 7)
            end_of_last_week = start_of_last_week + timedelta(days=6)
            date_from = start_of_last_week
            date_to = end_of_last_week
        elif period_name == "Этот месяц":
            date_from = today.replace(day=1)
            date_to = today
        elif period_name == "Прошлый месяц":
            first_day_of_month = today.replace(day=1)
            last_month = first_day_of_month - timedelta(days=1)
            date_from = last_month.replace(day=1)
            date_to = last_month
        elif period_name == "Этот год":
            date_from = today.replace(month=1, day=1)
            date_to = today
        elif period_name == "Прошлый год":
            last_year = today.replace(year=today.year - 1)
            date_from = last_year.replace(month=1, day=1)
            date_to = last_year.replace(month=12, day=31)
        else:  # "За все время"
            date_from = None
            date_to = None
        
        return date_from, date_to
    
    @staticmethod
    def format_date(date_obj, format="%Y-%m-%d"):
        """Форматирует дату в строку"""
        if not date_obj:
            return None
        return date_obj.strftime(format)
    
    @staticmethod
    def parse_date(date_str, format="%Y-%m-%d"):
        """Парсит строку в дату"""
        try:
            return datetime.strptime(date_str, format).date()
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def get_month_name(month_num):
        """Возвращает название месяца по номеру"""
        months = [
            "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
        ]
        return months[month_num - 1] if 1 <= month_num <= 12 else ""