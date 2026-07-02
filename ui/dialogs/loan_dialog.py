# ui/dialogs/loan_dialog.py
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from datetime import datetime, date, timedelta
import typing
from typing import Optional, List, Dict, Any, Tuple

from core.database import DatabaseManager


class LoanManagementWindow(QDialog):
    """Окно управления займами."""
    
    data_updated = Signal()
    
    def __init__(self, parent=None, db_manager: DatabaseManager = None):
        super().__init__(parent)
        self.db = db_manager or DatabaseManager.get_instance()
        self.parent_window = parent
        self.setWindowTitle("Управление Займами")
        self.setFixedSize(1000, 650)
        
        # Фильтры
        self.current_filters = {
            "loan_type": None,
            "contact_name": None,
            "status": None,
            "date_from": None,
            "date_to": None
        }
        
        self.init_ui()
        self.load_loans()
        self.center_on_parent()
    
    def center_on_parent(self):
        """Центрирует окно относительно родителя."""
        if self.parent_window:
            parent_rect = self.parent_window.frameGeometry()
            self.move(parent_rect.center() - self.rect().center())
    
    def init_ui(self):
        """Инициализация интерфейса."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # --- Фрейм для кнопок управления ---
        button_frame = QFrame()
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(5)
        
        # Кнопка добавления займа
        self.add_loan_btn = QPushButton("Добавить заём")
        self.add_loan_btn.clicked.connect(self._add_loan)
        button_layout.addWidget(self.add_loan_btn)
        
        button_layout.addStretch()
        
        # Кнопка сброса фильтров
        self.reset_filters_btn = QPushButton("Сбросить фильтры")
        self.reset_filters_btn.clicked.connect(self._reset_all_filters)
        button_layout.addWidget(self.reset_filters_btn)
        
        main_layout.addWidget(button_frame)
        
        # --- Таблица займов ---
        self.loans_tree = QTableWidget()
        self.loans_tree.setColumnCount(8)
        self.loans_tree.setHorizontalHeaderLabels([
            "Кому", "Тип", "Сумма", "Остаток", "Статус", 
            "Дата выдачи", "Дата погашения", "Описание"
        ])
        
        # Настройка ширины колонок
        self.loans_tree.setColumnWidth(0, 120)  # Кому
        self.loans_tree.setColumnWidth(1, 80)   # Тип
        self.loans_tree.setColumnWidth(2, 90)   # Сумма
        self.loans_tree.setColumnWidth(3, 90)   # Остаток
        self.loans_tree.setColumnWidth(4, 80)   # Статус
        self.loans_tree.setColumnWidth(5, 100)  # Дата выдачи
        self.loans_tree.setColumnWidth(6, 100)  # Дата погашения
        self.loans_tree.setColumnWidth(7, 150)  # Описание
        
        # Настройка таблицы
        self.loans_tree.setSelectionBehavior(QTableWidget.SelectRows)
        self.loans_tree.setSelectionMode(QTableWidget.SingleSelection)
        self.loans_tree.setAlternatingRowColors(True)
        self.loans_tree.verticalHeader().setVisible(False)
        
        # Контекстное меню
        self.loans_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.loans_tree.customContextMenuRequested.connect(self._show_context_menu)
        
        main_layout.addWidget(self.loans_tree)
        
        # --- Строка статуса ---
        self.status_bar = QLabel("Готово.")
        self.status_bar.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        main_layout.addWidget(self.status_bar)
    
    def _show_context_menu(self, position):
        """Показывает контекстное меню для таблицы."""
        menu = QMenu()
        
        selected_rows = self.loans_tree.selectionModel().selectedRows()
        
        # Всегда доступные действия
        add_payment_action = menu.addAction("💳 Добавить платеж")
        add_payment_action.triggered.connect(self._add_payment)
        
        view_details_action = menu.addAction("📋 Детали займа")
        view_details_action.triggered.connect(self._view_details)
        
        menu.addSeparator()
        
        if selected_rows:
            edit_action = menu.addAction("✏️ Редактировать")
            edit_action.triggered.connect(self._edit_loan)
            
            delete_action = menu.addAction("🗑️ Удалить")
            delete_action.triggered.connect(self._delete_selected_loan)
            
            menu.addSeparator()
            
            reminder_action = menu.addAction("📅 Напомнить о платеже")
            reminder_action.triggered.connect(self._set_payment_reminder)
        
        menu.exec_(self.loans_tree.viewport().mapToGlobal(position))
    
    def load_loans(self):
        """Загружает займы из БД с учетом фильтров."""
        self.loans_tree.setRowCount(0)
        
        # Создаем фильтры для новой БД
        filters = {}
        if self.current_filters["loan_type"]:
            filters["loan_type"] = self.current_filters["loan_type"]
        if self.current_filters["contact_name"]:
            filters["contact_name"] = self.current_filters["contact_name"]
        if self.current_filters["status"]:
            filters["status"] = self.current_filters["status"]
        
        # Фильтр по дате нужно обрабатывать отдельно
        date_from = self.current_filters["date_from"]
        date_to = self.current_filters["date_to"]
        
        loans = self.db.get_loans(filters)
        
        if not loans:
            self.show_status_message("Нет данных о займах.", 3000)
            return
        
        for row, loan in enumerate(loans):
            # loan это dict из новой БД
            outstanding_amount = loan.get('outstanding_amount', 0.0)
            status = "Активный" if float(outstanding_amount) > 0 else "Закрытый"
            
            self.loans_tree.insertRow(row)
            
            # Заполняем ячейки
            items = [
                QTableWidgetItem(loan.get('contact_name', '')),
                QTableWidgetItem(loan.get('loan_type', '')),
                QTableWidgetItem(f"{loan.get('loan_amount', 0.0):.2f}"),
                QTableWidgetItem(f"{outstanding_amount:.2f}"),
                QTableWidgetItem(status),
                QTableWidgetItem(loan.get('issue_date', '')),
                QTableWidgetItem(loan.get('due_date', '') or ''),
                QTableWidgetItem(loan.get('description', '') or '')
            ]
            
            for col, item in enumerate(items):
                item.setData(Qt.UserRole, loan.get('id'))  # Сохраняем ID в данных
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # Только для чтения
                self.loans_tree.setItem(row, col, item)
    
    def get_selected_loan_id(self) -> Optional[int]:
        """Возвращает ID выбранного займа."""
        selected_rows = self.loans_tree.selectionModel().selectedRows()
        if not selected_rows:
            return None
        
        row = selected_rows[0].row()
        item = self.loans_tree.item(row, 0)  # Берем первую ячейку строки
        if item:
            return item.data(Qt.UserRole)
        return None
    
    def _add_loan(self):
        """Открывает диалог добавления займа."""
        dialog = AddLoanDialog(self, self.db)
        if dialog.exec_() == QDialog.Accepted:
            self.show_status_message("Заём успешно добавлен.", 3000)
            self.load_loans()
            self._refresh_parent_data()
    
    def _edit_loan(self):
        """Открывает диалог редактирования займа."""
        loan_id = self.get_selected_loan_id()
        if not loan_id:
            QMessageBox.information(self, "Редактирование", 
                                  "Выберите заём для редактирования.")
            return
        
        loan = self.db.get_loan_by_id(loan_id)
        if not loan:
            QMessageBox.critical(self, "Ошибка", 
                               "Не удалось получить данные займа.")
            return
        
        dialog = EditLoanDialog(self, self.db, loan)
        if dialog.exec_() == QDialog.Accepted:
            self.show_status_message("Заём успешно обновлен.", 3000)
            self.load_loans()
            self._refresh_parent_data()
    
    def _add_payment(self):
        """Открывает диалог добавления платежа."""
        loan_id = self.get_selected_loan_id()
        if not loan_id:
            QMessageBox.information(self, "Платёж", 
                                  "Выберите заём для добавления платежа.")
            return
        
        loan = self.db.get_loan_by_id(loan_id)
        if not loan:
            QMessageBox.critical(self, "Ошибка", 
                               "Не удалось получить данные займа.")
            return
        
        # Получаем счета
        accounts = self.db.get_accounts(active_only=True, include_system=False)
        
        dialog = AddPaymentDialog(self, self.db, loan, accounts)
        if dialog.exec_() == QDialog.Accepted:
            self.show_status_message("Платёж успешно добавлен.", 3000)
            self.load_loans()
            self._refresh_parent_data()
    
    def _view_details(self):
        """Открывает диалог просмотра деталей займа."""
        loan_id = self.get_selected_loan_id()
        if not loan_id:
            QMessageBox.information(self, "Детали", 
                                  "Выберите заём для просмотра деталей.")
            return
        
        loan = self.db.get_loan_by_id(loan_id)
        if not loan:
            QMessageBox.critical(self, "Ошибка", 
                               "Не удалось получить данные займа.")
            return
        
        dialog = LoanDetailsDialog(self, self.db, loan)
        dialog.exec_()
    
    def _delete_selected_loan(self):
        """Удаляет выбранный займ."""
        loan_id = self.get_selected_loan_id()
        if not loan_id:
            QMessageBox.information(self, "Удаление", 
                                  "Выберите заём для удаления.")
            return
        
        loan = self.db.get_loan_by_id(loan_id)
        if not loan:
            QMessageBox.critical(self, "Ошибка", 
                               "Не удалось получить данные займа.")
            return
        
        # Подтверждение удаления
        reply = QMessageBox.question(
            self, "Подтверждение удаления",
            f"Вы уверены, что хотите удалить заём с контрагентом '{loan['contact_name']}'?\n"
            f"Все связанные платежи также будут удалены.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Удаляем все платежи сначала
                payments = self.db.get_loan_payments(loan_id)
                for payment in payments:
                    # Для отката балансов нужно удалять через специальный метод
                    # Временное решение - просто удаляем платежи
                    self.db._execute_query(
                        "DELETE FROM loan_payments WHERE id = ?",
                        (payment['id'],)
                    )
                
                # Удаляем сам займ
                success = self.db._execute_query(
                    "DELETE FROM loans WHERE id = ?",
                    (loan_id,)
                )
                
                if success:
                    self.show_status_message("Заём успешно удален.", 3000)
                    self.load_loans()
                    self._refresh_parent_data()
                else:
                    QMessageBox.critical(self, "Ошибка", 
                                       "Не удалось удалить заём.")
                    
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", 
                                   f"Ошибка при удалении: {str(e)}")
    
    def _reset_all_filters(self):
        """Сбрасывает все примененные фильтры."""
        self.current_filters = {
            "loan_type": None,
            "contact_name": None,
            "status": None,
            "date_from": None,
            "date_to": None
        }
        self.load_loans()
        self.show_status_message("Все фильтры сброшены.", 1500)
    
    def _set_payment_reminder(self):
        """Устанавливает напоминание о платеже."""
        QMessageBox.information(self, "В разработке", 
                              "Данная функция в разработке")
    
    def _refresh_parent_data(self):
        """Обновляет данные в родительском окне."""
        if hasattr(self.parent_window, 'refresh_data'):
            self.parent_window.refresh_data()
    
    def show_status_message(self, message: str, duration_ms: int = 3000):
        """Показывает сообщение в строке статуса."""
        self.status_bar.setText(message)
        QTimer.singleShot(duration_ms, lambda: self.status_bar.setText("Готово."))


class AddLoanDialog(QDialog):
    """Диалог для добавления нового займа."""
    
    def __init__(self, parent=None, db_manager: DatabaseManager = None):
        super().__init__(parent)
        self.db = db_manager or DatabaseManager.get_instance()
        self.setWindowTitle("Добавить заём")
        self.setFixedSize(350, 400)
        
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Форма ввода
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # Счет
        self.account_combo = QComboBox()
        self._load_accounts()
        form_layout.addRow("Счёт:", self.account_combo)
        
        # Контрагент
        self.contact_input = QLineEdit()
        form_layout.addRow("Контрагент:", self.contact_input)
        
        # Тип займа
        self.loan_type_combo = QComboBox()
        self.loan_type_combo.addItems(["issued", "received"])
        form_layout.addRow("Тип займа:", self.loan_type_combo)
        
        # Сумма займа
        self.amount_input = QLineEdit()
        self.amount_input.setValidator(QDoubleValidator(0, 9999999, 2))
        form_layout.addRow("Сумма займа:", self.amount_input)
        
        # Дата выдачи
        self.issue_date_input = QDateEdit()
        self.issue_date_input.setDate(QDate.currentDate())
        self.issue_date_input.setCalendarPopup(True)
        form_layout.addRow("Дата выдачи:", self.issue_date_input)
        
        # Дата погашения
        self.due_date_input = QDateEdit()
        self.due_date_input.setCalendarPopup(True)
        self.due_date_input.setDate(QDate.currentDate().addMonths(1))
        form_layout.addRow("Дата погашения:", self.due_date_input)
        
        # Описание
        self.description_input = QLineEdit()
        form_layout.addRow("Описание:", self.description_input)
        
        layout.addLayout(form_layout)
        layout.addStretch()
        
        # Кнопки
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _load_accounts(self):
        """Загружает счета в комбобокс."""
        accounts = self.db.get_accounts(active_only=True, include_system=False)
        for account in accounts:
            self.account_combo.addItem(account['name'], account['id'])
    
    def on_accept(self):
        """Обработчик принятия диалога."""
        # Валидация
        if not self.contact_input.text().strip():
            QMessageBox.critical(self, "Ошибка", 
                               "Введите имя контрагента.")
            return
        
        try:
            amount = float(self.amount_input.text())
            if amount <= 0:
                raise ValueError
        except:
            QMessageBox.critical(self, "Ошибка", 
                               "Введите корректную сумму займа.")
            return
        
        # Подготовка данных
        loan_data = {
            'account_id': self.account_combo.currentData(),
            'contact_name': self.contact_input.text().strip(),
            'loan_type': self.loan_type_combo.currentText(),
            'loan_amount': amount,
            'issue_date': self.issue_date_input.date().toString('yyyy-MM-dd'),
            'due_date': self.due_date_input.date().toString('yyyy-MM-dd'),
            'description': self.description_input.text().strip()
        }
        
        try:
            # Добавление займа
            loan_id = self.db.add_loan(loan_data)
            if loan_id:
                self.accept()
            else:
                QMessageBox.critical(self, "Ошибка", 
                                   "Не удалось добавить заём.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", 
                               f"Ошибка при добавлении займа: {str(e)}")


class EditLoanDialog(QDialog):
    """Диалог для редактирования займа."""
    
    def __init__(self, parent=None, db_manager: DatabaseManager = None, loan_data: Dict = None):
        super().__init__(parent)
        self.db = db_manager or DatabaseManager.get_instance()
        self.loan_data = loan_data
        self.setWindowTitle("Редактировать заём")
        self.setFixedSize(400, 400)
        
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Информация о займе (только для чтения)
        info_group = QGroupBox("Информация о займе (не редактируется)")
        info_layout = QFormLayout()
        
        info_layout.addRow("Тип:", QLabel(self.loan_data.get('loan_type', '')))
        info_layout.addRow("Сумма:", QLabel(f"{self.loan_data.get('loan_amount', 0):.2f} ₽"))
        info_layout.addRow("Остаток:", QLabel(f"{self.loan_data.get('outstanding_amount', 0):.2f} ₽"))
        info_layout.addRow("Дата выдачи:", QLabel(self.loan_data.get('issue_date', '')))
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Редактируемые поля
        form_group = QGroupBox("Редактируемые поля")
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # Контрагент
        self.contact_input = QLineEdit(self.loan_data.get('contact_name', ''))
        form_layout.addRow("Контрагент:", self.contact_input)
        
        # Дата погашения
        due_date = self.loan_data.get('due_date')
        if due_date:
            date_parts = [int(x) for x in due_date.split('-')]
            q_date = QDate(date_parts[0], date_parts[1], date_parts[2])
        else:
            q_date = QDate.currentDate()
        
        self.due_date_input = QDateEdit(q_date)
        self.due_date_input.setCalendarPopup(True)
        form_layout.addRow("Дата погашения:", self.due_date_input)
        
        # Описание
        self.description_input = QLineEdit(self.loan_data.get('description', ''))
        form_layout.addRow("Описание:", self.description_input)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Подсказка
        hint = QLabel("💡 Можно изменить только контрагента, дату погашения и описание")
        hint.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(hint)
        
        layout.addStretch()
        
        # Кнопки
        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.on_save)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def on_save(self):
        """Обработчик сохранения."""
        if not self.contact_input.text().strip():
            QMessageBox.critical(self, "Ошибка", 
                               "Введите имя контрагента.")
            return
        
        # Подготовка данных для обновления
        update_data = {
            'contact_name': self.contact_input.text().strip(),
            'due_date': self.due_date_input.date().toString('yyyy-MM-dd'),
            'description': self.description_input.text().strip()
        }
        
        try:
            success = self.db.update_loan(self.loan_data['id'], update_data)
            if success:
                self.accept()
            else:
                QMessageBox.critical(self, "Ошибка", 
                                   "Не удалось обновить заём.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", 
                               f"Ошибка при обновлении займа: {str(e)}")


class AddPaymentDialog(QDialog):
    """Диалог для добавления платежа по займу."""
    
    def __init__(self, parent=None, db_manager: DatabaseManager = None, 
                 loan_data: Dict = None, accounts: List[Dict] = None):
        super().__init__(parent)
        self.db = db_manager or DatabaseManager.get_instance()
        self.loan_data = loan_data
        self.accounts = accounts or []
        self.setWindowTitle("Добавить платёж по займу")
        self.setFixedSize(450, 500)
        
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Информация о займе
        info_group = QGroupBox("Информация о займе")
        info_layout = QFormLayout()
        
        info_layout.addRow("Контрагент:", QLabel(self.loan_data.get('contact_name', '')))
        info_layout.addRow("Тип:", QLabel(self.loan_data.get('loan_type', '')))
        info_layout.addRow("Сумма займа:", QLabel(f"{self.loan_data.get('loan_amount', 0):.2f} ₽"))
        info_layout.addRow("Остаток долга:", 
                          QLabel(f"{self.loan_data.get('outstanding_amount', 0):.2f} ₽"))
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Данные платежа
        form_group = QGroupBox("Данные платежа")
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        contact_name = self.loan_data.get('contact_name', '')
        loan_type = self.loan_data.get('loan_type', '')
        
        if loan_type == 'issued':
            # Для ВЫДАННЫХ займов
            form_layout.addRow("От кого (контрагент):", QLabel(contact_name))
            
            # Получаем имя счета займа
            account_name = self._get_account_name(self.loan_data.get('account_id'))
            form_layout.addRow("На наш счёт:", QLabel(account_name))
            
        else:  # 'received'
            # Для ПОЛУЧЕННЫХ займов
            self.from_account_combo = QComboBox()
            self._load_accounts_combo()
            form_layout.addRow("С нашего счёта:", self.from_account_combo)
            
            form_layout.addRow("Кому (контрагент):", QLabel(contact_name))
        
        # Дата платежа
        self.date_input = QDateEdit(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        form_layout.addRow("Дата платежа:", self.date_input)
        
        # Сумма платежа
        self.amount_input = QLineEdit()
        self.amount_input.setValidator(QDoubleValidator(0, 9999999, 2))
        form_layout.addRow("Сумма платежа:", self.amount_input)
        
        # Описание
        self.description_input = QLineEdit()
        form_layout.addRow("Описание:", self.description_input)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Подсказка
        if loan_type == "issued":
            hint_text = "💡 ВЫДАННЫЙ заём: получаем возврат денег от заемщика"
        else:
            hint_text = "💡 ПОЛУЧЕННЫЙ заём: возвращаем деньги кредитору"
        
        hint = QLabel(hint_text)
        hint.setStyleSheet("color: blue; font-size: 9pt;")
        layout.addWidget(hint)
        
        layout.addStretch()
        
        # Кнопки
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _load_accounts_combo(self):
        """Загружает счета в комбобокс."""
        for account in self.accounts:
            self.from_account_combo.addItem(account['name'], account['id'])
    
    def _get_account_name(self, account_id: int) -> str:
        """Возвращает имя счета по ID."""
        for account in self.accounts:
            if account['id'] == account_id:
                return account['name']
        return "Неизвестный счет"
    
    def on_accept(self):
        """Обработчик принятия диалога."""
        # Валидация
        try:
            amount = float(self.amount_input.text())
            if amount <= 0:
                raise ValueError("Сумма должна быть положительной.")
            
            outstanding = self.loan_data.get('outstanding_amount', 0)
            if amount > outstanding:
                QMessageBox.critical(
                    self, "Ошибка",
                    f"Сумма платежа ({amount:.2f} ₽) превышает "
                    f"остаток долга ({outstanding:.2f} ₽)."
                )
                return
                
        except ValueError as e:
            QMessageBox.critical(self, "Ошибка", 
                               f"Некорректная сумма: {str(e)}")
            return
        
        # Подготовка данных платежа
        payment_data = {
            'loan_id': self.loan_data['id'],
            'payment_date': self.date_input.date().toString('yyyy-MM-dd'),
            'payment_amount': amount,
            'description': self.description_input.text().strip()
        }
        
        try:
            payment_id = self.db.add_loan_payment(payment_data)
            if payment_id:
                self.accept()
            else:
                QMessageBox.critical(self, "Ошибка", 
                                   "Не удалось добавить платёж.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", 
                               f"Ошибка при добавлении платежа: {str(e)}")


class LoanDetailsDialog(QDialog):
    """Диалог для просмотра деталей займа с историей платежей."""
    
    def __init__(self, parent=None, db_manager: DatabaseManager = None, 
                 loan_data: Dict = None):
        super().__init__(parent)
        self.db = db_manager or DatabaseManager.get_instance()
        self.loan_data = loan_data
        self.setWindowTitle(f"Детали займа: {loan_data.get('contact_name', '')}")
        self.setFixedSize(800, 600)
        
        self.init_ui()
        self.load_payments()
    
    def init_ui(self):
        """Инициализация интерфейса."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Информация о займе
        info_group = QGroupBox("Информация о займе")
        info_layout = QFormLayout()
        
        info_text = f"""Контрагент: {self.loan_data.get('contact_name', '')}
Тип займа: {self.loan_data.get('loan_type', '')}
Общая сумма: {self.loan_data.get('loan_amount', 0):.2f} ₽
Остаток долга: {self.loan_data.get('outstanding_amount', 0):.2f} ₽
Дата выдачи: {self.loan_data.get('issue_date', '')}"""
        
        due_date = self.loan_data.get('due_date')
        if due_date:
            info_text += f"\nДата погашения: {due_date}"
        
        description = self.loan_data.get('description')
        if description:
            info_text += f"\nОписание: {description}"
        
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_layout.addRow(info_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # История платежей
        payments_group = QGroupBox("История платежей")
        payments_layout = QVBoxLayout()
        
        # Таблица платежей
        self.payments_table = QTableWidget()
        self.payments_table.setColumnCount(4)
        self.payments_table.setHorizontalHeaderLabels([
            "ID", "Дата", "Сумма", "Описание"
        ])
        
        self.payments_table.setColumnWidth(0, 50)
        self.payments_table.setColumnWidth(1, 100)
        self.payments_table.setColumnWidth(2, 100)
        self.payments_table.setColumnWidth(3, 400)
        
        self.payments_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.payments_table.setSelectionMode(QTableWidget.SingleSelection)
        self.payments_table.verticalHeader().setVisible(False)
        
        # Контекстное меню для таблицы платежей
        self.payments_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.payments_table.customContextMenuRequested.connect(
            self._show_payments_context_menu
        )
        
        payments_layout.addWidget(self.payments_table)
        payments_group.setLayout(payments_layout)
        layout.addWidget(payments_group)
        
        # Итоговая информация
        total_frame = QFrame()
        total_layout = QHBoxLayout(total_frame)
        
        self.total_paid_label = QLabel("Всего выплачено: 0.00 ₽")
        self.total_paid_label.setStyleSheet("font-weight: bold;")
        
        self.outstanding_label = QLabel(
            f"Остаток: {self.loan_data.get('outstanding_amount', 0):.2f} ₽"
        )
        self.outstanding_label.setStyleSheet("font-weight: bold;")
        
        total_layout.addWidget(self.total_paid_label)
        total_layout.addStretch()
        total_layout.addWidget(self.outstanding_label)
        
        layout.addWidget(total_frame)
        
        # Кнопка закрытия
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _show_payments_context_menu(self, position):
        """Показывает контекстное меню для таблицы платежей."""
        menu = QMenu()
        
        selected_rows = self.payments_table.selectionModel().selectedRows()
        if selected_rows:
            delete_action = menu.addAction("🗑️ Удалить платеж")
            delete_action.triggered.connect(self._delete_selected_payment)
            
            print_action = menu.addAction("🖨️ Печать квитанции")
            print_action.triggered.connect(self._print_receipt)
        
        menu.exec_(self.payments_table.viewport().mapToGlobal(position))
    
    def load_payments(self):
        """Загружает платежи по займу."""
        self.payments_table.setRowCount(0)
        
        payments = self.db.get_loan_payments(self.loan_data['id'])
        total_paid = 0.0
        
        for row, payment in enumerate(payments):
            self.payments_table.insertRow(row)
            
            items = [
                QTableWidgetItem(str(payment.get('id', ''))),
                QTableWidgetItem(payment.get('payment_date', '')),
                QTableWidgetItem(f"{payment.get('payment_amount', 0):.2f} ₽"),
                QTableWidgetItem(payment.get('description', '') or '')
            ]
            
            for col, item in enumerate(items):
                item.setData(Qt.UserRole, payment.get('id'))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.payments_table.setItem(row, col, item)
            
            total_paid += float(payment.get('payment_amount', 0))
        
        # Обновляем итоги
        new_outstanding = float(self.loan_data.get('loan_amount', 0)) - total_paid
        self.total_paid_label.setText(f"Всего выплачено: {total_paid:.2f} ₽")
        self.outstanding_label.setText(f"Остаток долга: {new_outstanding:.2f} ₽")
    
    def get_selected_payment_id(self) -> Optional[int]:
        """Возвращает ID выбранного платежа."""
        selected_rows = self.payments_table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        
        row = selected_rows[0].row()
        item = self.payments_table.item(row, 0)
        if item:
            return item.data(Qt.UserRole)
        return None
    
    def _delete_selected_payment(self):
        """Удаляет выбранный платеж."""
        payment_id = self.get_selected_payment_id()
        if not payment_id:
            QMessageBox.information(self, "Удаление", 
                                  "Выберите платеж для удаления.")
            return
        
        # Получаем данные платежа для подтверждения
        row = self.payments_table.currentRow()
        payment_date = self.payments_table.item(row, 1).text()
        payment_amount = self.payments_table.item(row, 2).text()
        
        reply = QMessageBox.question(
            self, "Подтверждение удаления",
            f"Вы уверены, что хотите удалить платеж от {payment_date} "
            f"на сумму {payment_amount}?\n"
            f"Балансы счетов будут восстановлены.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Временно удаляем напрямую, т.к. нет специального метода
                success = self.db.delete_loan_payment(payment_id)
                
                if success:
                    QMessageBox.information(self, "Успех", 
                                          "Платёж успешно удален.")
                    self.load_payments()
                    # Обновляем основное окно
                    if hasattr(self.parent(), 'load_loans'):
                        self.parent().load_loans()
                else:
                    QMessageBox.critical(self, "Ошибка", 
                                       "Не удалось удалить платёж.")
                    
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", 
                                   f"Ошибка при удалении: {str(e)}")
    
    def _print_receipt(self):
        """Печатает квитанцию об оплате."""
        payment_id = self.get_selected_payment_id()
        if payment_id:
            QMessageBox.information(self, "Печать", 
                                  f"Печать квитанции для платежа {payment_id}")


# Для поддержки старого импорта
def center_window_relative(window, parent=None):
    """Совместимость со старым кодом."""
    pass