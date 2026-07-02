# ui/dialogs/date_range_dialog.py
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton
from ui.widgets.date_widgets import DateRangeSelector

class DateRangeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выбор периода")
        self.resize(400, 150)
        
        layout = QVBoxLayout(self)
        
        # Используем DateRangeSelector вместо ручного создания
        self.date_range_selector = DateRangeSelector()
        layout.addWidget(self.date_range_selector)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(ok_btn)
        
        layout.addLayout(buttons_layout)
    
    def get_dates(self):
        """Возвращает выбранные даты"""
        return self.date_range_selector.get_dates()