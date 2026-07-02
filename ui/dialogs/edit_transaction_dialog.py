# ui/dialogs/edit_transaction_dialog.py
"""
Диалог редактирования транзакции
Переведено на PySide6 с сохранением функциональности Tkinter версии
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QGroupBox, QFormLayout, QMessageBox, QDateEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from datetime import datetime

from core.database import DatabaseManager
from ui.widgets.window_utils import center_window_relative
from ui.widgets.date_widgets import DateNavigator, DateUtils
from ui.widgets.calendar_widgets import TtkDateEntry


class EditTransactionDialog(QDialog):
    """Диалог редактирования транзакции"""
    
    data_updated = Signal()
    
    def __init__(self, parent=None, db_manager=None, transaction_data=None):
        super().__init__(parent)
        self.parent = parent
        self.db = db_manager
        self.transaction_data = transaction_data
        
        self.category_id_by_display_name = {}
        
        self.setWindowTitle("Редактировать транзакцию")
        self.resize(500, 550)
        
        self.transaction_id = transaction_data.get('id')
        
        self.setup_ui()
        self._load_transaction_data()
        
    def setup_ui(self):
        """Создает интерфейс диалога"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        
        # ID транзакции
        id_label = QLabel(f"ID транзакции: {self.transaction_id}")
        id_font = QFont()
        id_font.setItalic(True)
        id_label.setFont(id_font)
        id_label.setAlignment(Qt.AlignLeft)
        main_layout.addWidget(id_label)
        
        # Форма редактирования
        form_group = QGroupBox("Редактировать данные")
        form_layout = QFormLayout()
        
        # Дата
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("dd.MM.yyyy")
        form_layout.addRow("Дата:", self.date_input)
        
        # Тип
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Доход", "Расход", "Корректировка"])
        self.type_combo.currentTextChanged.connect(self._on_type_change)
        form_layout.addRow("Тип:", self.type_combo)
        
        # Сумма
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("0.00")
        form_layout.addRow("Сумма:", self.amount_input)
        
        # Количество
        self.quantity_input = QLineEdit()
        self.quantity_input.setText("1.0")
        form_layout.addRow("Количество:", self.quantity_input)
        
        # Категория
        self.category_combo = QComboBox()
        form_layout.addRow("Категория:", self.category_combo)
        
        # Счет
        self.account_combo = QComboBox()
        form_layout.addRow("Счет:", self.account_combo)
        
        # Описание
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Описание транзакции")
        form_layout.addRow("Описание:", self.description_input)
        
        form_group.setLayout(form_layout)
        main_layout.addWidget(form_group)
        
        # Кнопки сохранения/отмены
        button_layout = QHBoxLayout()
        
        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self._save_changes)
        button_layout.addWidget(save_button)
        
        button_layout.addStretch()
        
        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        main_layout.addLayout(button_layout)
        
        # Кнопка удаления
        delete_button = QPushButton("🗑️ Удалить эту транзакцию")
        delete_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                font-weight: bold;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        delete_button.clicked.connect(self._delete_transaction)
        main_layout.addWidget(delete_button)
        
        # Дополнительная информация
        info_group = QGroupBox("Дополнительная информация")
        info_layout = QVBoxLayout()
        
        self.info_label = QLabel()
        info_label_font = QFont()
        info_label_font.setPointSize(9)
        self.info_label.setFont(info_label_font)
        self.info_label.setAlignment(Qt.AlignLeft)
        self.info_label.setWordWrap(True)
        
        info_layout.addWidget(self.info_label)
        info_group.setLayout(info_layout)
        main_layout.addWidget(info_group)
        
        self.setLayout(main_layout)
    
    def _load_transaction_data(self):
        """Загружает данные транзакции в форму"""
        # Получаем данные из словаря
        date = self.transaction_data.get('date')
        amount = self.transaction_data.get('amount', 0.0)
        trans_type = self.transaction_data.get('type', '')
        category_name = self.transaction_data.get('category_name', '')
        description = self.transaction_data.get('description', '')
        account_name = self.transaction_data.get('account_name', '')
        account_id = self.transaction_data.get('account_id')
        quantity = self.transaction_data.get('quantity', 1.0)
        
        # Устанавливаем дату
        try:
            date_qdate = datetime.strptime(date, "%Y-%m-%d").date()
            self.date_input.setDate(date_qdate)
        except (ValueError, TypeError):
            self.date_input.setDate(datetime.now().date())
        
        # Устанавливаем тип
        type_mapping = {'income': 'Доход', 'expense': 'Расход', 'корректировка': 'Корректировка'}
        py_type = type_mapping.get(trans_type, trans_type.capitalize())
        index = self.type_combo.findText(py_type)
        if index >= 0:
            self.type_combo.setCurrentIndex(index)
        
        # Устанавливаем сумму
        display_amount = amount
        if trans_type == 'expense':
            display_amount = -amount
        
        self.amount_input.setText(f"{display_amount:.2f}")
        
        # Устанавливаем количество
        self.quantity_input.setText(f"{quantity:.1f}")
        
        # Устанавливаем описание
        if description:
            self.description_input.setText(description)
        
        # Обновляем комбобоксы
        self._update_category_combo()
        self._update_account_combo()
        
        # Устанавливаем категорию
        if category_name:
            # Ищем категорию в отображаемых именах
            for i in range(self.category_combo.count()):
                display_name = self.category_combo.itemText(i)
                # Убираем отступы для сравнения
                clean_name = display_name.strip()
                if clean_name == category_name:
                    self.category_combo.setCurrentIndex(i)
                    break
        
        # Устанавливаем счет
        if account_name:
            index = self.account_combo.findText(account_name)
            if index >= 0:
                self.account_combo.setCurrentIndex(index)
        
        self.original_type = trans_type
        self.original_amount = amount
        
        self._update_additional_info()
    
    def _update_category_combo(self):
        """Обновляет список категорий в зависимости от типа"""
        self.category_id_by_display_name.clear()
        self.category_combo.clear()
        
        trans_type = self.type_combo.currentText().lower()
        
        if trans_type == 'доход':
            categories = self.db.get_categories(type='income', include_subcategories=True)
        elif trans_type == 'расход':
            categories = self.db.get_categories(type='expense', include_subcategories=True)
        else:
            categories = self.db.get_categories(include_subcategories=True)
        
        for cat in categories:
            # Преобразуем кортеж в словарь для удобства
            if isinstance(cat, tuple):
                cat_dict = {
                    'id': cat[0],
                    'name': cat[1],
                    'type': cat[2],
                    'parent_id': cat[4] if len(cat) > 4 else None
                }
            else:
                cat_dict = cat
            
            level = 0
            parent_id = cat_dict.get('parent_id')
            
            # Определяем уровень вложенности
            while parent_id:
                level += 1
                parent_found = False
                for c in categories:
                    c_id = c[0] if isinstance(c, tuple) else c.get('id')
                    if c_id == parent_id:
                        parent_id = c[4] if isinstance(c, tuple) else c.get('parent_id')
                        parent_found = True
                        break
                if not parent_found:
                    break
            
            indent = "    " * level
            display_name = f"{indent}{cat_dict['name']}"
            self.category_combo.addItem(display_name)
            self.category_id_by_display_name[display_name] = cat_dict['id']
    
    def _update_account_combo(self):
        """Обновляет список счетов"""
        self.account_combo.clear()
        
        accounts = self.db.get_accounts()
        for account in accounts:
            if isinstance(account, tuple):
                account_id = account[0]
                account_name = account[1]
            else:
                account_id = account.get('id')
                account_name = account.get('name')
            
            self.account_combo.addItem(account_name, account_id)
    
    def _on_type_change(self, text):
        """Обновляет список категорий при изменении типа"""
        self._update_category_combo()
    
    def _update_additional_info(self):
        """Обновляет дополнительную информацию"""
        date = self.transaction_data.get('date')
        amount = self.transaction_data.get('amount', 0.0)
        trans_type = self.transaction_data.get('type', '')
        category_name = self.transaction_data.get('category_name', '')
        account_name = self.transaction_data.get('account_name', '')
        quantity = self.transaction_data.get('quantity', 1.0)
        
        ui_amount = amount
        if trans_type == 'expense':
            ui_amount = -amount
        
        info_text = f"• Дата создания: {date}\n"
        info_text += f"• Сумма в БД: {amount:.2f} ₽\n"
        info_text += f"• Сумма для редактирования: {ui_amount:.2f} ₽\n"
        
        if trans_type == 'expense':
            info_text += "• Формат отображения расходов:\n"
            info_text += "  - Положительное число = обычный расход\n"
            info_text += "  - Отрицательное число = возврат покупки\n"
        
        if quantity != 1.0:
            price_per_unit = ui_amount / quantity
            info_text += f"• Цена за единицу: {price_per_unit:.2f} ₽\n"
        
        info_text += f"• Счет: {account_name}\n"
        info_text += f"• Категория: {category_name}"
        
        self.info_label.setText(info_text)
    
    def _save_changes(self):
        """Сохраняет изменения транзакции"""
        try:
            # Проверяем дату
            date_qdate = self.date_input.date()
            date_str = date_qdate.toString("yyyy-MM-dd")
            
            if not date_qdate.isValid():
                QMessageBox.critical(self, "Ошибка", "Введите корректную дату.")
                return
            
            # Определяем тип транзакции
            type_mapping = {
                'Доход': 'income',
                'Расход': 'expense', 
                'Корректировка': 'корректировка'
            }
            trans_type = type_mapping.get(self.type_combo.currentText(), self.type_combo.currentText().lower())
            
            # Проверяем сумму
            amount_str = self.amount_input.text().strip().replace(',', '.')
            try:
                ui_amount = float(amount_str)
            except ValueError:
                QMessageBox.critical(self, "Ошибка", "Некорректная сумма.")
                return
            
            if trans_type == 'expense':
                db_amount = -ui_amount
            else:
                db_amount = ui_amount
            
            # Проверяем количество
            quantity_str = self.quantity_input.text().strip().replace(',', '.')
            try:
                quantity = float(quantity_str)
                if quantity <= 0:
                    raise ValueError("Количество должно быть положительным.")
            except ValueError as e:
                QMessageBox.critical(self, "Ошибка", f"Некорректное количество: {e}")
                return
            
            # Проверяем категорию
            category_display = self.category_combo.currentText()
            if not category_display:
                QMessageBox.critical(self, "Ошибка", "Выберите категорию.")
                return
            
            category_id = self.category_id_by_display_name.get(category_display)
            
            if category_id is None:
                # Ищем категорию по имени (без отступов)
                category_name = category_display.strip()
                for cat in self.db.get_categories():
                    if isinstance(cat, dict):
                        cat_name = cat.get('name')
                        cat_id = cat.get('id')
                    else:
                        cat_name = cat[1] if len(cat) > 1 else ''
                        cat_id = cat[0]
                    
                    if cat_name == category_name:
                        category_id = cat_id
                        break
            
            if category_id is None:
                QMessageBox.critical(self, "Ошибка", "Категория не найдена.")
                return
            
            # Проверяем счет
            account_id = self.account_combo.currentData()
            if not account_id:
                QMessageBox.critical(self, "Ошибка", "Выберите счет.")
                return
            
            # Получаем описание
            description = self.description_input.text().strip()
            
            # Формируем словарь с данными для обновления
            transaction_data = {
                'date': date_str,
                'amount': db_amount,
                'type': trans_type,
                'category_id': category_id,
                'description': description,
                'account_id': account_id,
                'quantity': quantity
            }
            
            # Удаляем пустые значения (если метод ожидает только заполненные поля)
            transaction_data = {k: v for k, v in transaction_data.items() if v is not None}
            
            # Обновляем транзакцию в БД
            if self.db.update_transaction(
                transaction_id=self.transaction_id,
                transaction_data=transaction_data
            ):
                # Формируем сообщение об успехе
                if trans_type == 'expense':
                    if ui_amount > 0:
                        msg = f"✅ Расход обновлен: {ui_amount:.2f} ₽"
                    else:
                        msg = f"✅ Возврат покупки обновлен: {abs(ui_amount):.2f} ₽"
                elif trans_type == 'income':
                    msg = f"✅ Доход обновлен: {db_amount:.2f} ₽"
                else:
                    msg = f"✅ Корректировка обновлена: {db_amount:.2f} ₽"
                
                QMessageBox.information(self, "Успех", msg)
                
                # Сигнализируем об обновлении данных
                self.data_updated.emit()
                
                self.accept()
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось обновить транзакцию.")
                
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка: {str(e)}")
            print(f"DEBUG: Error saving transaction: {e}")
            
    def _delete_transaction(self):
        """Удаляет текущую транзакцию"""
        reply = QMessageBox.question(
            self, "Подтверждение удаления",
            f"Вы уверены, что хотите удалить эту транзакцию (ID: {self.transaction_id})?\n\n"
            f"Эта операция необратима.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.db.delete_transaction(self.transaction_id):
                QMessageBox.information(self, "Успех", "Транзакция удалена.")
                
                # Сигнализируем об обновлении данных
                self.data_updated.emit()
                
                self.accept()
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось удалить транзакцию.")