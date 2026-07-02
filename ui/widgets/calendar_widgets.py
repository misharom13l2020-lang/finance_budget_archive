# ui/widgets/calendar_widgets.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QLabel, QGridLayout, QFrame, QDialog, QLineEdit)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QFont
import calendar
from datetime import date


class TtkCalendar(QWidget):
    """Кастомный календарь"""
    
    date_selected = Signal(QDate)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.russian_months = {
            1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
            5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
            9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
        }
        
        self.current_date = QDate.currentDate()
        self.selected_date = None
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setFixedWidth(30)
        self.prev_btn.clicked.connect(self.prev_month)
        header_layout.addWidget(self.prev_btn)
        
        self.month_label = QLabel()
        self.month_label.setFont(QFont("", 10, QFont.Bold))
        self.month_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.month_label, 1)
        
        self.year_label = QLabel()
        self.year_label.setFont(QFont("", 10, QFont.Bold))
        self.year_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.year_label, 1)
        
        self.next_btn = QPushButton("▶")
        self.next_btn.setFixedWidth(30)
        self.next_btn.clicked.connect(self.next_month)
        header_layout.addWidget(self.next_btn)
        
        layout.addLayout(header_layout)
        
        # Days grid
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(2)
        
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        for i, day in enumerate(days):
            label = QLabel(day)
            label.setAlignment(Qt.AlignCenter)
            label.setFont(QFont("", 8, QFont.Bold))
            self.grid_layout.addWidget(label, 0, i)
            
        self.day_buttons = []
        for row in range(6):
            row_buttons = []
            for col in range(7):
                btn = QPushButton()
                btn.setFixedSize(30, 30)
                btn.setFont(QFont("", 8))
                btn.clicked.connect(lambda checked, r=row, c=col: self.select_date(r, c))
                self.grid_layout.addWidget(btn, row + 1, col)
                row_buttons.append(btn)
            self.day_buttons.append(row_buttons)
            
        layout.addLayout(self.grid_layout)
        self.setLayout(layout)
        
        self.update_calendar()
        
    def update_calendar(self):
        year = self.current_date.year()
        month = self.current_date.month()
        
        self.month_label.setText(self.russian_months[month])
        self.year_label.setText(str(year))
        
        cal = calendar.Calendar(firstweekday=0)
        month_days = cal.monthdatescalendar(year, month)
        
        for row_idx, week in enumerate(month_days):
            for col_idx, day_date in enumerate(week):
                btn = self.day_buttons[row_idx][col_idx]
                day = day_date.day
                btn.setText(str(day))
                btn.day_date = day_date
                
                if day_date.month == month:
                    btn.setEnabled(True)
                    btn.setStyleSheet("")
                else:
                    btn.setEnabled(False)
                    btn.setStyleSheet("color: gray;")
                    
    def prev_month(self):
        self.current_date = self.current_date.addMonths(-1)
        self.update_calendar()
        
    def next_month(self):
        self.current_date = self.current_date.addMonths(1)
        self.update_calendar()
        
    def select_date(self, row, col):
        btn = self.day_buttons[row][col]
        if btn.isEnabled():
            selected_date = btn.day_date
            qdate = QDate(selected_date.year, selected_date.month, selected_date.day)
            self.selected_date = qdate
            self.date_selected.emit(qdate)


class TtkDateEntry(QWidget):
    """Виджет для ввода даты с календарным попапом"""
    
    date_changed = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.calendar_dialog = None
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.date_input = QLineEdit()
        self.date_input.setFixedWidth(100)
        self.date_input.setText(date.today().strftime('%Y-%m-%d'))
        self.date_input.textChanged.connect(self.date_changed)
        layout.addWidget(self.date_input)
        
        self.calendar_btn = QPushButton("📅")
        self.calendar_btn.setFixedWidth(30)
        self.calendar_btn.clicked.connect(self.show_calendar)
        layout.addWidget(self.calendar_btn)
        
        self.setLayout(layout)
        
    def get_date(self):
        return self.date_input.text()
        
    def set_date(self, date_str):
        self.date_input.setText(date_str)
        
    def show_calendar(self):
        if self.calendar_dialog is None or not self.calendar_dialog.isVisible():
            self.calendar_dialog = CalendarDialog(self)
            self.calendar_dialog.date_selected.connect(self.on_date_selected)
            
        pos = self.mapToGlobal(self.calendar_btn.pos())
        pos.setY(pos.y() + self.calendar_btn.height())
        self.calendar_dialog.move(pos)
        self.calendar_dialog.exec()
        
    def on_date_selected(self, qdate):
        date_str = qdate.toString('yyyy-MM-dd')
        self.set_date(date_str)
        self.date_changed.emit(date_str)
        
        
class CalendarDialog(QDialog):
    date_selected = Signal(QDate)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup)
        
        layout = QVBoxLayout()
        
        self.calendar = TtkCalendar()
        self.calendar.date_selected.connect(self.on_date_selected)
        layout.addWidget(self.calendar)
        
        today_btn = QPushButton("Сегодня")
        today_btn.clicked.connect(self.select_today)
        layout.addWidget(today_btn)
        
        self.setLayout(layout)
        
    def on_date_selected(self, qdate):
        self.date_selected.emit(qdate)
        self.accept()
        
    def select_today(self):
        self.calendar.selected_date = QDate.currentDate()
        self.date_selected.emit(QDate.currentDate())
        self.accept()