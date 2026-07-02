# ui/dialogs/reconciliation_dialog.py
"""
Диалог для массовой сверки балансов всех счетов
Переведено на PySide6 с сохранением функциональности Tkinter версии
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QWidget, QFrame, QMessageBox, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPalette, QColor
from datetime import datetime

from core.database import DatabaseManager
from ui.widgets.window_utils import center_window_relative


class ReconciliationDialog(QDialog):
    """Диалог для массовой сверки балансов всех счетов"""
    
    data_updated = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.db = DatabaseManager.get_instance()
        
        self.account_entries = {}
        self.calculated_balances = {}
        self.difference_labels = {}
        self.total_difference_label = None
        self.result = False
        
        self.setup_ui()
        
    def setup_ui(self):
        """Создание интерфейса диалога"""
        self.setWindowTitle("Сверка Балансов")
        self.resize(650, 550)
        
        # center_window_relative(self, parent)
        
        if self.parent:
            center_window_relative(self, self.parent)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        
        # Инструкция
        instruction_label = QLabel("Введите фактические балансы для всех счетов:")
        instruction_font = QFont()
        instruction_font.setPointSize(10)
        instruction_label.setFont(instruction_font)
        instruction_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(instruction_label)
        
        # Заголовки таблицы
        header_widget = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        labels = ["Счет", "Расчетный", "Фактический", "Разница"]
        widths = [200, 100, 100, 100]
        
        for label, width in zip(labels, widths):
            header_label = QLabel(label)
            header_font = QFont()
            header_font.setBold(True)
            header_label.setFont(header_font)
            header_label.setMinimumWidth(width)
            header_layout.addWidget(header_label)
        
        header_widget.setLayout(header_layout)
        main_layout.addWidget(header_widget)
        
        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)
        
        # Область прокрутки для счетов
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.accounts_widget = QWidget()
        self.accounts_layout = QVBoxLayout()
        self.accounts_layout.setSpacing(5)
        self.accounts_widget.setLayout(self.accounts_layout)
        
        scroll_area.setWidget(self.accounts_widget)
        main_layout.addWidget(scroll_area, 1)
        
        # Создаем таблицу счетов
        self._create_accounts_table()
        
        # Общая разница
        self.total_difference_label = QLabel("Общая разница: 0.00 ₽")
        total_font = QFont()
        total_font.setBold(True)
        total_font.setPointSize(11)
        self.total_difference_label.setFont(total_font)
        self.total_difference_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.total_difference_label)
        
        # Кнопки
        button_layout = QHBoxLayout()
        
        self.reconcile_button = QPushButton("Выполнить сверку")
        self.reconcile_button.setEnabled(False)
        self.reconcile_button.clicked.connect(self._perform_reconciliation)
        button_layout.addWidget(self.reconcile_button)
        
        button_layout.addStretch()
        
        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.on_close)
        button_layout.addWidget(cancel_button)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
    def _create_accounts_table(self):
        """Создает таблицу с полями ввода для каждого счета"""
        # Очищаем существующие виджеты
        while self.accounts_layout.count():
            item = self.accounts_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.account_entries = {}
        self.calculated_balances = {}
        self.difference_labels = {}
        
        # Получаем счета из БД
        accounts = self.db.get_accounts(active_only=True, include_system=False)
        
        # Сортируем счета по имени
        sorted_accounts = sorted(accounts, key=lambda x: x['name'])
        
        for acc in sorted_accounts:
            row_widget = QWidget()
            row_layout = QHBoxLayout()
            row_layout.setSpacing(10)
            
            # Название счета
            account_label = QLabel(acc['name'])
            account_label.setMinimumWidth(200)
            row_layout.addWidget(account_label)
            
            # Расчетный баланс
            calculated_balance = acc['current_balance']
            account_id = acc['id']
            self.calculated_balances[account_id] = calculated_balance
            
            calc_label = QLabel(f"{calculated_balance:.2f} ₽")
            calc_label.setMinimumWidth(100)
            calc_label.setAlignment(Qt.AlignRight)
            row_layout.addWidget(calc_label)
            
            # Поле для фактического баланса
            actual_input = QLineEdit()
            actual_input.setMinimumWidth(100)
            actual_input.setText(f"{calculated_balance:.2f}")
            actual_input.textChanged.connect(
                lambda text, acc_id=account_id: self._on_balance_change(acc_id)
            )
            row_layout.addWidget(actual_input)
            
            # Разница
            diff_label = QLabel("0.00 ₽")
            diff_label.setMinimumWidth(100)
            diff_label.setAlignment(Qt.AlignRight)
            row_layout.addWidget(diff_label)
            
            self.account_entries[account_id] = actual_input
            self.difference_labels[account_id] = diff_label
            
            row_widget.setLayout(row_layout)
            self.accounts_layout.addWidget(row_widget)
        
        # Добавляем растягивающий элемент
        self.accounts_layout.addStretch()
        
    def _on_balance_change(self, account_id):
        """Обрабатывает изменение баланса"""
        self._update_balance(account_id)
        
    def _update_balance(self, account_id):
        """Обновляет разницу для конкретного счета"""
        try:
            actual_text = self.account_entries[account_id].text().replace(',', '.').strip()
            
            if actual_text:
                actual_balance = float(actual_text)
                calculated_balance = self.calculated_balances[account_id]
                difference = actual_balance - calculated_balance
                
                diff_text = f"{difference:+.2f} ₽"
                diff_label = self.difference_labels[account_id]
                diff_label.setText(diff_text)
                
                # Устанавливаем цвет в зависимости от разницы
                palette = diff_label.palette()
                if difference > 0:
                    palette.setColor(QPalette.WindowText, QColor("green"))
                elif difference < 0:
                    palette.setColor(QPalette.WindowText, QColor("red"))
                else:
                    palette.setColor(QPalette.WindowText, QColor("black"))
                diff_label.setPalette(palette)
                
            else:
                self.difference_labels[account_id].setText("0.00 ₽")
                palette = self.difference_labels[account_id].palette()
                palette.setColor(QPalette.WindowText, QColor("black"))
                self.difference_labels[account_id].setPalette(palette)
                
        except (ValueError, TypeError):
            self.difference_labels[account_id].setText("Ошибка")
            palette = self.difference_labels[account_id].palette()
            palette.setColor(QPalette.WindowText, QColor("orange"))
            self.difference_labels[account_id].setPalette(palette)
        
        self._update_total_difference()
        
    def _update_total_difference(self):
        """Обновляет общую разницу и состояние кнопки"""
        total_diff = 0.0
        has_changes = False
        
        for account_id in self.account_entries:
            try:
                actual_text = self.account_entries[account_id].text().replace(',', '.').strip()
                if not actual_text:
                    continue
                    
                actual_balance = float(actual_text)
                calculated_balance = self.calculated_balances[account_id]
                difference = actual_balance - calculated_balance
                
                total_diff += difference
                
                if difference != 0:
                    has_changes = True
                    
            except (ValueError, TypeError):
                has_changes = True
        
        # Обновляем текст общей разницы
        total_text = f"Общая разница: {total_diff:+.2f} ₽"
        self.total_difference_label.setText(total_text)
        
        # Устанавливаем цвет общей разницы
        palette = self.total_difference_label.palette()
        if total_diff > 0:
            palette.setColor(QPalette.WindowText, QColor("green"))
        elif total_diff < 0:
            palette.setColor(QPalette.WindowText, QColor("red"))
        else:
            palette.setColor(QPalette.WindowText, QColor("black"))
        self.total_difference_label.setPalette(palette)
        
        # Обновляем состояние кнопки
        self.reconcile_button.setEnabled(has_changes)
        
    def _perform_reconciliation(self):
        """Выполняет сверку для всех счетов с изменениями"""
        reconciliations = []
        
        for account_id in self.account_entries:
            try:
                actual_text = self.account_entries[account_id].text().replace(',', '.').strip()
                if not actual_text:
                    continue
                    
                actual_balance = float(actual_text)
                calculated_balance = self.calculated_balances[account_id]
                difference = actual_balance - calculated_balance
                
                if difference == 0:
                    continue
                
                # Получаем информацию о счете для логирования
                account_info = self.db.get_account_by_id(account_id)
                account_name = account_info['name'] if account_info else f"ID: {account_id}"
                
                # Создаем корректирующую транзакцию
                if self._create_reconciliation_transaction(account_id, difference, account_name):
                    reconciliations.append({
                        'account': account_name,
                        'difference': difference
                    })
                    
            except (ValueError, TypeError) as e:
                self.logger.error(f"Ошибка при обработке счета {account_id}: {e}")
                continue
        
        if reconciliations:
            # Формируем текст результата
            result_text = "Сверка выполнена для счетов:\n\n"
            for rec in reconciliations:
                sign = "+" if rec['difference'] > 0 else ""
                result_text += f"• {rec['account']}: {sign}{rec['difference']:.2f} ₽\n"
            
            result_text += f"\nВсего обработано: {len(reconciliations)} счетов"
            
            QMessageBox.information(self, "Сверка завершена", result_text)
            self.result = True
            
            # Сигнализируем об обновлении данных
            self.data_updated.emit()
            
            # Закрываем диалог
            self.accept()
                
        else:
            QMessageBox.information(self, "Сверка", "Нет изменений для сверки")
            self.result = False
            self.reject()
            
    def _create_reconciliation_transaction(self, account_id, difference, account_name):
        """Создает корректирующую операцию для сверки баланса"""
        try:
            # Используем метод reconcile_account из DatabaseManager
            transaction_id = self.db.reconcile_account(
                account_id=account_id,
                actual_balance=float(self.account_entries[account_id].text().replace(',', '.')),
                description=f"Сверка баланса: {account_name}"
            )
            
            return transaction_id > 0
            
        except Exception as e:
            print(f"Error in _create_reconciliation_transaction: {e}")
            return False
            
    def on_close(self):
        """Закрывает диалоговое окно"""
        self.data_updated.emit()
        self.reject()