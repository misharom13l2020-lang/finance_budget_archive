# ui/dialogs/transfer_dialog.py
"""
Диалог управления переводами между счетами
Переведено на PySide6 с улучшениями и адаптацией под словари БД
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QRadioButton, QButtonGroup, QGroupBox, QTabWidget,
    QTreeWidget, QTreeWidgetItem, QDateEdit, QMessageBox, QHeaderView,
    QWidget, QFormLayout, QScrollArea, QMenu, QCompleter
)
from PySide6.QtCore import Qt, Signal, QDate, QStringListModel
from PySide6.QtGui import QFont

from core.database import DatabaseManager
from ui.widgets.window_utils import center_window_relative


class TransferDialog(QDialog):
    """Диалог для управления переводами между счетами"""
    
    data_updated = Signal()
    
    def __init__(self, parent=None, db_manager=None, accounts_data=None):
        super().__init__(parent)
        self.parent = parent
        self.db = db_manager or DatabaseManager.get_instance()
        self.accounts_data = accounts_data or {}
        
        # Инициализация переменных
        self.current_account_id = None
        self.last_selected_date = QDate.currentDate()
        
        # Фильтры
        self.current_filters = {
            "account_id": None,
            "counterparty": None,
            "date_from": None,
            "date_to": None
        }
        
        # Модель для автодополнения контрагентов
        self.counterparty_model = QStringListModel()
        self.counterparty_completer = None
        
        self.setup_ui()
        self._update_counterparties_list()
        
    def _normalize_counterparty_name(self, name: str) -> str:
        """Нормализует имя контрагента для единообразия.
        
        Применяет:
        - Удаление лишних пробелов
        - Приведение к заглавным буквам каждого слова (title case)
        
        Args:
            name: Исходное имя контрагента
            
        Returns:
            Нормализованное имя
        """
        if not name:
            return ''
        
        # Удаляем лишние пробелы
        normalized = ' '.join(part.strip() for part in name.split())
        # Приводим к заглавным буквам каждого слова
        normalized = normalized.title()
        
        return normalized
        
    def setup_ui(self):
        """Настройка интерфейса"""
        self.setWindowTitle("Управление Переводами")
        self.resize(650, 350)
        
        # center_window_relative(self, parent)
        
        if self.parent:
            center_window_relative(self, self.parent)
        
        main_layout = QVBoxLayout()
        
        # Создаем вкладки
        self.tab_widget = QTabWidget()
        
        # Вкладка добавления перевода
        add_tab = QWidget()
        self._create_add_transfer_tab(add_tab)
        self.tab_widget.addTab(add_tab, "Добавить перевод")
        
        # Вкладка просмотра переводов
        view_tab = QWidget()
        self._create_view_transfers_tab(view_tab)
        self.tab_widget.addTab(view_tab, "Все переводы")
        
        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)
        
    def _create_add_transfer_tab(self, parent):
        """Создает вкладку для добавления переводов"""
        layout = QVBoxLayout()
        
        # Группа для типа перевода
        type_group = QGroupBox("Тип перевода")
        type_layout = QHBoxLayout()
        
        self.transfer_type_group = QButtonGroup(self)
        self.internal_radio = QRadioButton("Между моими счетами")
        self.external_radio = QRadioButton("Внешний перевод")
        self.internal_radio.setChecked(True)
        
        self.transfer_type_group.addButton(self.internal_radio, 0)
        self.transfer_type_group.addButton(self.external_radio, 1)
        self.transfer_type_group.buttonClicked.connect(self._update_transfer_type)
        
        type_layout.addWidget(self.internal_radio)
        type_layout.addWidget(self.external_radio)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # Форма для данных перевода
        form_layout = QFormLayout()
        
        # Дата и Сумма в одной строке по горизонтали
        date_amount_layout = QHBoxLayout()
        date_amount_layout.setSpacing(10)
        
        # Дата
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(self.last_selected_date)
        self.date_input.setDisplayFormat("dd.MM.yyyy")
        self.date_input.setFixedHeight(26)
        self.date_input.setFixedWidth(80)
        
        # Сумма
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("0.00")
        self.amount_input.setFixedHeight(26)
        self.amount_input.setFixedWidth(100)
        
        date_amount_layout.addWidget(QLabel("Дата:"))
        date_amount_layout.addWidget(self.date_input)
        date_amount_layout.addWidget(QLabel("Сумма:"))
        date_amount_layout.addWidget(self.amount_input)
        date_amount_layout.addStretch()
        
        date_amount_widget = QWidget()
        date_amount_widget.setLayout(date_amount_layout)
        form_layout.addRow("", date_amount_widget)
        
        # Фреймы для разных типов переводов
        self.internal_frame = QGroupBox("Внутренний перевод")
        internal_form = QFormLayout()
        
        self.from_account_combo = QComboBox()
        self.from_account_combo.setFixedHeight(26)
        self.from_account_combo.setMinimumWidth(150)
        self.from_account_combo.setMaximumWidth(300)
        self.to_account_combo = QComboBox()
        self.to_account_combo.setFixedHeight(26)
        self.to_account_combo.setMinimumWidth(150)
        self.to_account_combo.setMaximumWidth(300)
        self._populate_accounts_combo(self.from_account_combo)
        self._populate_accounts_combo(self.to_account_combo)
        
        # Счета рядом по горизонтали
        accounts_layout = QHBoxLayout()
        accounts_layout.addWidget(self.from_account_combo)
        accounts_layout.addWidget(self.to_account_combo)
        accounts_widget = QWidget()
        accounts_widget.setLayout(accounts_layout)
        internal_form.addRow("Со счета → На счет:", accounts_widget)
        
        self.internal_frame.setLayout(internal_form)
        layout.addWidget(self.internal_frame)
        
        self.external_frame = QGroupBox("Внешний перевод")
        external_form = QFormLayout()
        
        # Направление внешнего перевода
        direction_group = QButtonGroup(self)
        self.incoming_radio = QRadioButton("Мне перевели")
        self.outgoing_radio = QRadioButton("Я перевел")
        self.incoming_radio.setChecked(True)
        
        direction_layout = QHBoxLayout()
        direction_layout.addWidget(self.incoming_radio)
        direction_layout.addWidget(self.outgoing_radio)
        direction_widget = QWidget()
        direction_widget.setLayout(direction_layout)
        
        direction_group.addButton(self.incoming_radio, 0)
        direction_group.addButton(self.outgoing_radio, 1)
        
        external_form.addRow("Направление:", direction_widget)
        
        # Счет для внешнего перевода
        self.external_account_combo = QComboBox()
        self.external_account_combo.setFixedHeight(26)
        self.external_account_combo.setMinimumWidth(230)
        self._populate_accounts_combo(self.external_account_combo)
        external_form.addRow("Счет:", self.external_account_combo)
        
        # Контрагент
        self.counterparty_input = QLineEdit()
        self.counterparty_input.setFixedHeight(26)
        self.counterparty_input.setMinimumWidth(230)
        self.counterparty_input.setPlaceholderText("Имя контрагента")
        
        # Автодополнение для контрагентов
        self.counterparty_completer = QCompleter()
        self.counterparty_completer.setModel(self.counterparty_model)
        self.counterparty_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.counterparty_completer.setFilterMode(Qt.MatchContains)
        self.counterparty_completer.setCompletionMode(QCompleter.PopupCompletion)
        self.counterparty_input.setCompleter(self.counterparty_completer)
        
        external_form.addRow("Контрагент:", self.counterparty_input)
        
        # Подсказка о регистре
        self.counterparty_hint = QLabel("⚠️ Регистр не учитывается: 'иван' и 'Иван' будут одним контрагентом")
        self.counterparty_hint.setStyleSheet("font-size: 9px; color: gray; font-style: italic;")
        external_form.addRow("", self.counterparty_hint)
        
        self.external_frame.setLayout(external_form)
        layout.addWidget(self.external_frame)
        self.external_frame.hide()
        
        # Описание
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Описание перевода")
        self.description_input.setFixedHeight(26)
        self.description_input.setMinimumWidth(230)
        form_layout.addRow("Описание:", self.description_input)
        
        layout.addLayout(form_layout)
        
        # Кнопки
        button_layout = QHBoxLayout()
        
        self.add_close_button = QPushButton("Добавить и закрыть")
        self.add_close_button.setFixedHeight(26)
        self.add_close_button.setFixedWidth(130)
        self.add_close_button.clicked.connect(self._add_and_close)
        button_layout.addWidget(self.add_close_button)
        
        self.add_more_button = QPushButton("Добавить еще")
        self.add_more_button.setFixedHeight(26)
        self.add_more_button.setFixedWidth(100)
        self.add_more_button.clicked.connect(self._add_more)
        button_layout.addWidget(self.add_more_button)
        
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.setFixedHeight(26)
        self.cancel_button.setFixedWidth(100)
        self.cancel_button.clicked.connect(self.on_close)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        parent.setLayout(layout)
        
    def _create_view_transfers_tab(self, parent):
        """Создает вкладку для просмотра и управления переводами"""
        layout = QVBoxLayout()
        
        # Фильтры
        filter_group = QGroupBox("Фильтры")
        filter_layout = QFormLayout()
        
        # Счет и контрагент в одной строке по горизонтали
        account_counterparty_layout = QHBoxLayout()
        
        # Фильтр по счету
        self.filter_account_combo = QComboBox()
        self.filter_account_combo.setFixedHeight(26)
        self.filter_account_combo.setMaximumWidth(300)
        self.filter_account_combo.setMinimumWidth(150)

        self.filter_account_combo.addItem("Все")
        
        # Загружаем активные счета
        accounts = self.db.get_accounts(active_only=True, include_system=False)
        for account in accounts:
            self.filter_account_combo.addItem(account['name'], account['id'])
        
        self.filter_account_combo.currentIndexChanged.connect(self._apply_filters)
        
        # Фильтр по контрагенту
        self.filter_counterparty_combo = QComboBox()
        self.filter_counterparty_combo.setFixedHeight(26)
        self.filter_counterparty_combo.setMinimumWidth(150)
        self.filter_counterparty_combo.setMaximumWidth(300)
        self.filter_counterparty_combo.currentIndexChanged.connect(self._apply_filters)
        
        account_counterparty_layout.addWidget(QLabel("Счет:"))
        account_counterparty_layout.addWidget(self.filter_account_combo)
        account_counterparty_layout.addSpacing(20)
        account_counterparty_layout.addWidget(QLabel("Контрагент:"))
        account_counterparty_layout.addWidget(self.filter_counterparty_combo)
        account_counterparty_layout.addStretch()
        
        account_counterparty_widget = QWidget()
        account_counterparty_widget.setLayout(account_counterparty_layout)
        filter_layout.addRow("", account_counterparty_widget)
        
        # Фильтр по дате (выравнивание влево)
        date_layout = QHBoxLayout()
        date_layout.setAlignment(Qt.AlignLeft)
        
        self.filter_date_from = QDateEdit()
        self.filter_date_from.setFixedHeight(26) 
        self.filter_date_from.setFixedWidth(80)
        self.filter_date_from.setCalendarPopup(True)
        self.filter_date_from.setDisplayFormat("dd.MM.yyyy")
        self.filter_date_from.dateChanged.connect(self._apply_filters)
        
        self.filter_date_to = QDateEdit()
        self.filter_date_to.setFixedHeight(26) 
        self.filter_date_to.setFixedWidth(80)
        self.filter_date_to.setCalendarPopup(True)
        self.filter_date_to.setDisplayFormat("dd.MM.yyyy")
        self.filter_date_to.setDate(QDate.currentDate())
        self.filter_date_to.dateChanged.connect(self._apply_filters)
        
        date_layout.addWidget(QLabel("Дата от:"))
        date_layout.addWidget(self.filter_date_from)
        date_layout.addWidget(QLabel("до:"))
        date_layout.addWidget(self.filter_date_to)
        
        date_widget = QWidget()
        date_widget.setLayout(date_layout)
        filter_layout.addRow("", date_widget)
        
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        # Таблица переводов
        self.transfers_tree = QTreeWidget()
        self.transfers_tree.setHeaderLabels(["Дата", "Тип", "Сумма", "Откуда", "Куда", "Контрагент", "Описание"])
        self.transfers_tree.setAlternatingRowColors(True)
        
        # Настройка ширины колонок
        header = self.transfers_tree.header()
        header.setSectionResizeMode(QHeaderView.Interactive)
        self.transfers_tree.setColumnWidth(0, 100)  # Дата
        self.transfers_tree.setColumnWidth(1, 80)   # Тип
        self.transfers_tree.setColumnWidth(2, 100)  # Сумма
        self.transfers_tree.setColumnWidth(3, 120)  # Откуда
        self.transfers_tree.setColumnWidth(4, 120)  # Куда
        self.transfers_tree.setColumnWidth(5, 120)  # Контрагент
        self.transfers_tree.setColumnWidth(6, 200)  # Описание
        
        layout.addWidget(self.transfers_tree, 1)
        
        # Настраиваем контекстное меню для таблицы
        self.transfers_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.transfers_tree.customContextMenuRequested.connect(self._show_context_menu)
        
        # Кнопка сброса фильтров
        reset_button = QPushButton("Сбросить фильтры")
        reset_button.setFixedHeight(26)
        reset_button.setFixedWidth(130)
        reset_button.clicked.connect(self._reset_filters)
        layout.addWidget(reset_button)
        
        parent.setLayout(layout)
        
        # Загружаем данные
        self._load_transfers_data()
        
    def _populate_accounts_combo(self, combo):
        """Заполняет комбобокс счетами"""
        combo.clear()
        accounts = self.db.get_accounts(active_only=True, include_system=False)
        
        for account in accounts:
            combo.addItem(account['name'], account['id'])
        
    def _update_counterparties_list(self):
        """Обновляет список контрагентов из базы данных"""
        try:
            counterparties = set()
            
            # Получаем счета контрагентов
            counterparty_accounts = self.db.get_counterparty_accounts()
            
            for account in counterparty_accounts:
                if account['type'] == 'Counterparty':
                    counterparty_name = account['name'].replace("Контрагент:", "").strip()
                    if counterparty_name:
                        # Нормализуем имя для единообразия
                        normalized_name = self._normalize_counterparty_name(counterparty_name)
                        counterparties.add(normalized_name)
            
            counterparties_list = list(counterparties)
            counterparties_list.sort()
            
            # Обновляем комбобокс фильтра
            self.filter_counterparty_combo.clear()
            self.filter_counterparty_combo.addItem("Все")
            self.filter_counterparty_combo.addItems(counterparties_list)
            self.filter_counterparty_combo.setCurrentIndex(0)
            
            # Обновляем модель автодополнения
            if self.counterparty_model:
                self.counterparty_model.setStringList(counterparties_list)
            
        except Exception as e:
            print(f"Error updating counterparties list: {e}")
            
    def _load_transfers_data(self, account_id=None, counterparty=None, date_from=None, date_to=None):
        """Загружает данные в таблицу переводов с учетом фильтров"""
        self.transfers_tree.clear()
        
        try:
            # Подготавливаем фильтры
            filters = {}
            if account_id:
                filters['account_id'] = account_id
            if date_from:
                filters['date_from'] = date_from.toString("yyyy-MM-dd")
            if date_to:
                filters['date_to'] = date_to.toString("yyyy-MM-dd")
            
            # Получаем переводы
            transfers = self.db.get_transfers(filters=filters)
            
            for transfer in transfers:
                transfer_id = transfer['id']
                date = transfer['date']
                amount = transfer['amount']
                from_acc = transfer['from_account_name']
                to_acc = transfer['to_account_name']
                description = transfer.get('description', '')
                
                # Определяем тип перевода и контрагента
                transfer_type = "Внутренний"
                counterparty_name = ""
                
                # Проверяем, является ли один из счетов контрагентом
                from_is_counterparty = transfer.get('from_account_type') == 'Counterparty'
                to_is_counterparty = transfer.get('to_account_type') == 'Counterparty'
                
                if from_is_counterparty or to_is_counterparty:
                    transfer_type = "Внешний"
                    
                    if from_is_counterparty:
                        counterparty_name = from_acc.replace("Контрагент:", "").strip()
                    else:
                        counterparty_name = to_acc.replace("Контрагент:", "").strip()
                
                # Применяем фильтр по контрагенту
                if counterparty and counterparty.lower() not in counterparty_name.lower():
                    continue
                
                # Форматируем дату для отображения
                display_date = QDate.fromString(date, "yyyy-MM-dd").toString("dd.MM.yyyy") if isinstance(date, str) else date
                
                # Добавляем в таблицу
                item = QTreeWidgetItem(self.transfers_tree)
                item.setText(0, display_date)
                item.setText(1, transfer_type)
                item.setText(2, f"{amount:.2f} ₽")
                item.setText(3, from_acc)
                item.setText(4, to_acc)
                item.setText(5, counterparty_name)
                item.setText(6, description)
                item.setData(0, Qt.UserRole, transfer_id)
            
            item_count = self.transfers_tree.topLevelItemCount()
            
        except Exception as e:
            print(f"Error loading transfers data: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить данные о переводах: {str(e)}")
            
    def _apply_filters(self):
        """Применяет фильтры к таблице переводов"""
        try:
            # Фильтр по счету
            account_id = None
            current_account_id = self.filter_account_combo.currentData()
            if current_account_id:
                account_id = current_account_id
            elif self.filter_account_combo.currentText() != "Все":
                # Ищем по имени
                account_name = self.filter_account_combo.currentText()
                accounts = self.db.get_accounts(active_only=True, include_system=False)
                for account in accounts:
                    if account['name'] == account_name:
                        account_id = account['id']
                        break
            
            # Фильтр по контрагенту
            counterparty = None
            if self.filter_counterparty_combo.currentText() != "Все":
                counterparty = self.filter_counterparty_combo.currentText()
            
            # Фильтры по дате
            date_from = self.filter_date_from.date() if self.filter_date_from.date().isValid() else None
            date_to = self.filter_date_to.date() if self.filter_date_to.date().isValid() else None
            
            self._load_transfers_data(account_id, counterparty, date_from, date_to)
            
        except Exception as e:
            print(f"Error applying filters: {e}")
            
    def _reset_filters(self):
        """Сбрасывает все фильтры"""
        self.filter_account_combo.setCurrentIndex(0)
        self.filter_counterparty_combo.setCurrentIndex(0)
        self.filter_date_from.clear()
        self.filter_date_to.setDate(QDate.currentDate())
        self._load_transfers_data()
        
    def _delete_selected_transfer(self):
        """Удаляет выбранный перевод"""
        selected_items = self.transfers_tree.selectedItems()
        
        if not selected_items:
            QMessageBox.information(self, "Удаление", "Выберите перевод для удаления.")
            return
        
        item = selected_items[0]
        transfer_id = item.data(0, Qt.UserRole)
        date = item.text(0)
        amount = item.text(2)
        
        reply = QMessageBox.question(
            self, "Подтверждение удаления",
            f"Вы уверены, что хотите удалить перевод от {date} на сумму {amount}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.db.delete_transfer(transfer_id):
                self.show_status_message("✅ Перевод успешно удален", "success")
                self._load_transfers_data()
                self.data_updated.emit()
                self._update_counterparties_list()
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось удалить перевод.")
                
    def _show_context_menu(self, position):
        """Показывает контекстное меню для переводов"""
        item = self.transfers_tree.itemAt(position)
        if not item:
            return
            
        menu = QMenu(self)
        
        delete_action = menu.addAction("Удалить перевод")
        action = menu.exec_(self.transfers_tree.viewport().mapToGlobal(position))
        
        if action == delete_action:
            self.transfers_tree.setCurrentItem(item)
            self._delete_selected_transfer()
                
    def _update_transfer_type(self):
        """Обновляет видимость полей в зависимости от типа перевода"""
        if self.internal_radio.isChecked():
            self.internal_frame.show()
            self.external_frame.hide()
        else:
            self.internal_frame.hide()
            self.external_frame.show()
            
    def _add_transfer(self):
        """Добавляет перевод и возвращает True при успехе"""
        # Получаем данные из формы
        date = self.date_input.date().toString("yyyy-MM-dd")
        amount_str = self.amount_input.text().strip().replace(',', '.')
        description = self.description_input.text().strip()
        
        # Проверка суммы
        if not amount_str:
            QMessageBox.critical(self, "Ошибка ввода", "Пожалуйста, введите сумму.")
            return False
            
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError("Сумма перевода должна быть положительной.")
        except ValueError as e:
            QMessageBox.critical(self, "Ошибка ввода", f"Некорректная сумма: {e}")
            return False
        
        if self.internal_radio.isChecked():
            # Внутренний перевод
            from_account_id = self.from_account_combo.currentData()
            to_account_id = self.to_account_combo.currentData()
            
            if not from_account_id or not to_account_id:
                QMessageBox.critical(self, "Ошибка ввода", "Пожалуйста, выберите оба счета.")
                return False
                
            if from_account_id == to_account_id:
                QMessageBox.critical(self, "Ошибка ввода", "Счета 'Откуда' и 'Куда' не могут быть одинаковыми.")
                return False
            
            # Добавляем перевод в БД
            transfer_data = {
                'date': date,
                'amount': amount,
                'from_account_id': from_account_id,
                'to_account_id': to_account_id,
                'description': description
            }
            
            try:
                transfer_id = self.db.add_transfer(transfer_data)
                if transfer_id:
                    self.show_status_message("✅ Внутренний перевод успешно добавлен", "success")
                    self.last_selected_date = self.date_input.date()
                    return True
                else:
                    QMessageBox.critical(self, "Ошибка", "Не удалось добавить перевод.")
                    return False
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось добавить перевод: {str(e)}")
                return False
                
        else:
            # Внешний перевод
            account_id = self.external_account_combo.currentData()
            counterparty = self.counterparty_input.text().strip()
            
            if not counterparty:
                QMessageBox.critical(self, "Ошибка ввода", "Введите имя контрагента.")
                return False
                
            if not account_id:
                QMessageBox.critical(self, "Ошибка ввода", "Пожалуйста, выберите счет.")
                return False
            
            # Нормализуем имя контрагента для предотвращения дублирования
            normalized_counterparty = self._normalize_counterparty_name(counterparty)
            
            # Определяем направление
            if self.incoming_radio.isChecked():
                # Нам перевели: контрагент → наш счет
                from_account_id = self.db.create_counterparty_account(normalized_counterparty)
                to_account_id = account_id
            else:
                # Мы перевели: наш счет → контрагент
                from_account_id = account_id
                to_account_id = self.db.create_counterparty_account(normalized_counterparty)
            
            # Добавляем перевод
            transfer_data = {
                'date': date,
                'amount': amount,
                'from_account_id': from_account_id,
                'to_account_id': to_account_id,
                'description': description
            }
            
            try:
                transfer_id = self.db.add_transfer(transfer_data)
                if transfer_id:
                    self.show_status_message("✅ Внешний перевод успешно добавлен", "success")
                    self.last_selected_date = self.date_input.date()
                    self._update_counterparties_list()  # Обновляем список контрагентов
                    return True
                else:
                    QMessageBox.critical(self, "Ошибка", "Не удалось добавить внешний перевод.")
                    return False
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось добавить внешний перевод: {str(e)}")
                return False
                
    def _add_and_close(self):
        """Добавляет перевод и закрывает окно"""
        if self._add_transfer():
            self._update_counterparties_list()
            self.data_updated.emit()
            self.accept()
            
    def _add_more(self):
        """Добавляет перевод и очищает поля для следующего ввода"""
        if self._add_transfer():
            self.amount_input.clear()
            self.description_input.clear()
            self.counterparty_input.clear()
            self.amount_input.setFocus()
            
    def show_status_message(self, message, message_type="info"):
        """Показывает сообщение в статусе родительского окна"""
        if hasattr(self.parent, 'show_status_message'):
            self.parent.show_status_message(message, 3000)
        else:
            print(f"STATUS [{message_type}]: {message}")
            
    def on_close(self):
        """Закрывает диалоговое окно"""
        self.data_updated.emit()
        self.reject()