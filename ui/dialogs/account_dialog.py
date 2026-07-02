# ui/dialogs/account_dialog.py
"""
Диалог управления счетами на PySide6 с архитектурой MVP.
"""
import logging
from datetime import datetime, date

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QLineEdit, QComboBox, QPushButton, QFrame, QMessageBox,
    QScrollArea, QTextEdit, QProgressBar, QGroupBox, QGridLayout,
    QHeaderView, QSplitter, QMenu, QApplication, QWidget,
    QDialogButtonBox, QStatusBar, QProgressDialog, QRadioButton
)
from PySide6.QtCore import Qt, Signal, QTimer, QDate, QThread
from PySide6.QtGui import QFont, QColor, QAction

from core.database import DatabaseManager  # для обратной совместимости
from core.db import Database
from ui.presenters.account_presenter import AccountPresenter
from ui.widgets.window_utils import center_window_relative
from ui.widgets.colored_button import CompactButton, ColoredButton
from ui.styles.theme_manager import ThemeManager
from utils.parsers import parse_int, parse_float
import config

logger = logging.getLogger(__name__)


class AccountManagementDialog(QDialog):
    """Диалог управления счетами на PySide6"""
    
    data_updated = Signal()

    
    def __init__(self, parent, db):
        """
        Инициализация диалога.
        
        Args:
            parent: родительское окно
            db: экземпляр DatabaseManager (старый) или Database (новый)
        """
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Управление Счетами")
        self.resize(500, 640)

        
        
        center_window_relative(self, parent)
        
        # Загрузка стилей из внешнего файла
        self._load_styles()
        
        # Определяем тип базы данных и создаем презентер
        self._init_database(db)
        self.presenter = AccountPresenter(self.database)
        self._connect_presenter_signals()
        
        self.editing_account_id = None
        self.current_accounts = []
        
        self._init_ui()
        self._load_accounts()
        
    def _init_database(self, db):
        """
        Инициализирует базу данных в зависимости от типа переданного объекта.
        Сохраняет self.database как экземпляр Database (новой архитектуры).
        """
        from core.database import DatabaseManager
        from core.db import Database
        
        if isinstance(db, Database):
            self.database = db
            logger.debug("Используется новая база данных (Database)")
        elif isinstance(db, DatabaseManager):
            # Создаем новый экземпляр Database с тем же путем
            self.database = Database('budget.db')
            logger.debug("Создана новая база данных из DatabaseManager")
        else:
            raise TypeError(f"Неизвестный тип базы данных: {type(db)}")
    
    def _connect_presenter_signals(self):
        """Подключает сигналы презентера к слою View."""
        self.presenter.accounts_loaded.connect(self._on_accounts_loaded)
        self.presenter.account_added.connect(self._on_account_added)
        self.presenter.account_updated.connect(self._on_account_updated)
        self.presenter.account_deleted.connect(self._on_account_deleted)
        self.presenter.error_occurred.connect(self._on_presenter_error)
        self.presenter.validation_failed.connect(self._on_validation_failed)
    
    # --- Обработчики сигналов презентера ---
    
    def _on_accounts_loaded(self, accounts):
        """Обрабатывает загруженные счета от презентера."""
        self.current_accounts = accounts  # список объектов Account
        self._refresh_table_with_accounts(accounts)
    
    def _on_account_added(self, account):
        """Обрабатывает добавление нового счета."""
        # Добавляем счет в текущий список
        self.current_accounts.append(account)
        # Обновляем таблицу
        self._refresh_table_with_accounts(self.current_accounts)
        # Показываем статус
        self.show_status(f"Счет '{account.name}' добавлен", "success")
        # Эмитируем сигнал обновления данных для внешних потребителей
        self.data_updated.emit()
    
    def _on_account_updated(self, account):
        """Обрабатывает обновление счета."""
        # Обновляем счет в текущем списке
        for i, acc in enumerate(self.current_accounts):
            if acc.id == account.id:
                self.current_accounts[i] = account
                break
        # Обновляем таблицу
        self._refresh_table_with_accounts(self.current_accounts)
        # Показываем статус
        self.show_status(f"Счет '{account.name}' обновлен", "success")
        # Эмитируем сигнал обновления данных
        self.data_updated.emit()
    
    def _on_account_deleted(self, account_id):
        """Обрабатывает удаление счета."""
        # Удаляем счет из текущего списка
        self.current_accounts = [acc for acc in self.current_accounts if acc.id != account_id]
        # Обновляем таблицу
        self._refresh_table_with_accounts(self.current_accounts)
        # Показываем статус
        self.show_status(f"Счет удален", "success")
        # Эмитируем сигнал обновления данных
        self.data_updated.emit()
    
    def _on_presenter_error(self, error_msg):
        """Обрабатывает ошибку от презентера."""
        self.show_status(error_msg, "error")
        QMessageBox.warning(self, "Ошибка", error_msg)
    
    def _on_validation_failed(self, errors):
        """Обрабатывает ошибки валидации."""
        error_text = "\n".join([f"{field}: {msg}" for field, msg in errors.items()])
        self.show_status("Ошибки валидации", "error")
        QMessageBox.warning(self, "Ошибки валидации", error_text)
    
    def _refresh_table_with_accounts(self, accounts):
        """Обновляет таблицу на основе переданного списка счетов."""
        # Временно используем старый метод _refresh_table, но с переданными accounts
        # Для простоты сохраним accounts в self.current_accounts и вызовем _refresh_table,
        # который должен использовать self.current_accounts.
        # Однако _refresh_table загружает данные из БД, поэтому нужно его модифицировать.
        # Пока что оставим как есть, но позже заменим.
        self.current_accounts = accounts
        self._refresh_table()
    
    def _load_styles(self):
        """Загружает стили из внешнего QSS файла"""
        try:
            import os
            # Используем путь из конфигурации
            styles_dir = config.STYLES_DIR
            style_path = os.path.join(styles_dir, 'account_dialog.qss')
            # Нормализуем путь относительно текущей рабочей директории
            style_path = os.path.normpath(style_path)
            if os.path.exists(style_path):
                with open(style_path, 'r', encoding='utf-8') as f:
                    stylesheet = f.read()
                self.setStyleSheet(stylesheet)
            else:
                # Fallback к встроенным стилям, если файл не найден
                self.setStyleSheet("""
                    QDialog {
                        background-color: #f8f9fa;
                        font-family: 'Segoe UI', Arial, sans-serif;
                        font-size: 12px;
                    }
                """)
                logger.warning(f"Файл стилей не найден: {style_path}")
        except Exception as e:
            logger.error(f"Ошибка загрузки стилей: {e}")
            # Используем минимальные стили
            self.setStyleSheet("QDialog { background-color: #f8f9fa; }")

    def _init_ui(self):
        """Инициализация интерфейса"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 1. Таблица счетов
        tree_group = QGroupBox("Счета")
        tree_layout = QVBoxLayout(tree_group)
        
        self.accounts_tree = QTreeWidget()
        self.accounts_tree.setHeaderLabels(["Название", "Тип", "Баланс"])
        
        # Настройка колонок
        header = self.accounts_tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        self.accounts_tree.setAlternatingRowColors(True)
        self.accounts_tree.itemSelectionChanged.connect(self._on_account_select)
        
        # Контекстное меню
        self.accounts_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.accounts_tree.customContextMenuRequested.connect(self._show_context_menu)
        
        tree_layout.addWidget(self.accounts_tree)
        main_layout.addWidget(tree_group)
        
        # 2. Форма добавления/редактирования
        form_group = QGroupBox("Добавить/Редактировать счет")
        form_layout = QGridLayout(form_group)
        
        row = 0
        
        # Название
        form_layout.addWidget(QLabel("Название:"), row, 0)
        self.name_input = QLineEdit()
        self.name_input.setFixedHeight(26)
        form_layout.addWidget(self.name_input, row, 1)
        row += 1
        
        # Тип
        self.type_label = QLabel("Тип:")
        form_layout.addWidget(self.type_label, row, 0)
        self.type_combo = QComboBox()
        self.type_combo.setFixedHeight(26)
        self.type_combo.addItems(["Cash", "Bank Account", "Credit Card"])
        self.type_combo.currentTextChanged.connect(self._on_type_change)
        form_layout.addWidget(self.type_combo, row, 1)
        row += 1
        
        # Начальный баланс
        self.initial_balance_label = QLabel("Начальный баланс:")
        form_layout.addWidget(self.initial_balance_label, row, 0)
        self.initial_balance_input = QLineEdit("0.00")
        self.initial_balance_input.setFixedHeight(26)
        form_layout.addWidget(self.initial_balance_input, row, 1)
        row += 1
        
        # Кредитный лимит
        self.credit_limit_label = QLabel("Кредитный лимит:")
        form_layout.addWidget(self.credit_limit_label, row, 0)
        self.credit_limit_input = QLineEdit("0.00")
        self.credit_limit_input.setFixedHeight(26)
        form_layout.addWidget(self.credit_limit_input, row, 1)
        row += 1
        
        # День платежа
        self.payment_day_label = QLabel("День платежа (1-31):")
        form_layout.addWidget(self.payment_day_label, row, 0)
        self.payment_day_input = QLineEdit("1")
        self.payment_day_input.setFixedHeight(26)
        form_layout.addWidget(self.payment_day_input, row, 1)
        row += 1
        
        # Мин. платеж
        self.min_payment_label = QLabel("Мин. платеж (%):")
        form_layout.addWidget(self.min_payment_label, row, 0)
        self.min_payment_input = QLineEdit("5.0")
        self.min_payment_input.setFixedHeight(26)
        form_layout.addWidget(self.min_payment_input, row, 1)
        row += 1
        
        # Валюта
        form_layout.addWidget(QLabel("Валюта:"), row, 0)
        self.currency_combo = QComboBox()
        self.currency_combo.setFixedHeight(26)
        self.currency_combo.addItems(["RUB", "USD", "EUR", "GBP", "CNY", "JPY"])
        form_layout.addWidget(self.currency_combo, row, 1)
        row += 1
        
        # Кнопки формы
        button_layout = QHBoxLayout()
        
        self.add_button = ColoredButton("Добавить", "#4CAF50")
        self.add_button.clicked.connect(self._add_account)
        button_layout.addWidget(self.add_button)
        
        self.edit_button = CompactButton("Сохранить")
        self.edit_button.clicked.connect(self._edit_account)
        self.edit_button.setEnabled(False)
        button_layout.addWidget(self.edit_button)
        
        self.cancel_button = CompactButton("Отмена")
        self.cancel_button.clicked.connect(self._reset_form)
        self.cancel_button.setEnabled(False)
        button_layout.addWidget(self.cancel_button)
        
        form_layout.addLayout(button_layout, row, 0, 1, 2)
        
        main_layout.addWidget(form_group)
        
        # 4. Кнопки управления диалогом
        dialog_buttons = QDialogButtonBox()
        close_button = dialog_buttons.addButton("Закрыть", QDialogButtonBox.RejectRole)
        close_button.clicked.connect(self.accept)
        
        main_layout.addWidget(dialog_buttons)
        
        # 5. Статус-бар
        self.status_bar = QLabel("Готово")
        self.status_bar.setProperty("class", "status")
        self.status_bar.setFixedHeight(26)
        main_layout.addWidget(self.status_bar)
        
        self.setLayout(main_layout)
        
        # Инициализация полей кредитной карты
        self._on_type_change()
        
    def _on_type_change(self):
        """Показывает/скрывает поля для кредитной карты"""
        acc_type = self.type_combo.currentText()
        is_credit_card = acc_type == "Credit Card"
        
        # Показываем/скрываем поля
        self.credit_limit_label.setVisible(is_credit_card)
        self.credit_limit_input.setVisible(is_credit_card)
        self.payment_day_label.setVisible(is_credit_card)
        self.payment_day_input.setVisible(is_credit_card)
        self.min_payment_label.setVisible(is_credit_card)
        self.min_payment_input.setVisible(is_credit_card)
    
    def _load_accounts(self):
        """Загружает счета через презентер."""
        self.presenter.load_accounts(active_only=True, include_system=True)
        
    def _tuple_to_dict(self, account_data):
        """Преобразует данные счета в словарь (для совместимости)"""
        # Если уже словарь, возвращаем как есть
        if isinstance(account_data, dict):
            return account_data
            
        # Если кортеж или список, преобразуем в словарь
        # Это запасной вариант на случай неправильных данных
        account_dict = {
            'id': 0,
            'name': 'Неизвестный',
            'type': 'Cash',
            'initial_balance': 0.0,
            'current_balance': 0.0,
            'currency': 'RUB',
            'is_system': False
        }
        
        try:
            if isinstance(account_data, (tuple, list)):
                if len(account_data) > 0:
                    account_dict['id'] = account_data[0]
                if len(account_data) > 1:
                    account_dict['name'] = account_data[1] or 'Без названия'
                if len(account_data) > 2:
                    account_dict['type'] = account_data[2] or 'Cash'
                if len(account_data) > 3:
                    account_dict['initial_balance'] = float(account_data[3]) if account_data[3] is not None else 0.0
                if len(account_data) > 4:
                    account_dict['current_balance'] = float(account_data[4]) if account_data[4] is not None else 0.0
                if len(account_data) > 12:
                    account_dict['currency'] = account_data[12] or 'RUB'
                    account_dict['is_system'] = bool(account_data[11]) if len(account_data) > 11 else False
        except Exception as e:
            logger.error(f"Ошибка преобразования account_data в словарь: {e}")
            
        return account_dict
        
    def _on_account_select(self):
        """Обработчик выбора счета"""
        selected_items = self.accounts_tree.selectedItems()
        
        if not selected_items:
            self._reset_form()
            return
        
        item = selected_items[0]
        account_id = item.data(0, Qt.UserRole)
        is_system = item.data(0, Qt.UserRole + 1)
        
        # Находим данные счета
        account = None
        for acc in self.current_accounts:
            if acc.id == account_id:
                account = acc
                break
        
        if not account:
            self.show_status("Данные счета не найдены", "error")
            return
        
        # Заполняем форму
        self.name_input.setText(account.name)
        
        # Для системных счетов (Counterparty) скрываем поле типа
        if account.type == 'Counterparty' or account.is_system:
            self.type_label.setVisible(False)
            self.type_combo.setVisible(False)
        else:
            self.type_label.setVisible(True)
            self.type_combo.setVisible(True)
            self.type_combo.setCurrentText(account.type)
            self.type_combo.setEnabled(True)
            
        # Начальный баланс только для просмотра при редактировании
        self.initial_balance_label.setText(f"Начальный баланс: {account.initial_balance:.2f}")
        self.initial_balance_input.setVisible(False)
        
        self.currency_combo.setCurrentText(account.currency or 'RUB')
        
        # Для кредитных карт
        if account.type == 'Credit Card':
            self.credit_limit_input.setText(f"{account.credit_limit or 0.0:.2f}")
            self.payment_day_input.setText(str(account.payment_due_day or 1))
            self.min_payment_input.setText(f"{account.min_payment_percent or 5.0:.2f}")
        
        # Переключаем режим на редактирование
        self.editing_account_id = account_id
        self.add_button.setEnabled(False)
        self.edit_button.setEnabled(True)
        self.cancel_button.setEnabled(True)
        
        self.show_status(f"Редактирование: {account.name}", "info")

    def _refresh_table(self, accounts=None):
        """
        Обновляет таблицу счетов.
        
        Args:
            accounts: список объектов Account. Если None, используется self.current_accounts.
        """
        try:
            # Показываем статус загрузки
            self.show_status("Обновление таблицы...", "info")
            QApplication.processEvents()
            
            # Сохраняем текущее состояние
            scroll_pos = self.accounts_tree.verticalScrollBar().value()
            selected_ids = []
            selected_items = self.accounts_tree.selectedItems()
            for item in selected_items:
                selected_ids.append(item.data(0, Qt.UserRole))
            
            # Очищаем дерево
            self.accounts_tree.clear()
            
            # Определяем данные для отображения
            if accounts is not None:
                self.current_accounts = accounts
            display_accounts = self.current_accounts
            
            if not display_accounts:
                self.show_status("Нет счетов", "info")
                return
            
            # Отключаем обновление виджета для ускорения
            self.accounts_tree.setUpdatesEnabled(False)
            
            # Заполняем таблицу порциями для лучшей отзывчивости
            for i, account in enumerate(display_accounts):
                # Создаем элемент
                item = QTreeWidgetItem([
                    account.name or 'Без названия',
                    account.type or 'Cash',
                    f"{account.current_balance or 0.0:.2f} {account.currency or 'RUB'}"
                ])
                
                # Настройка внешнего вида
                balance = account.current_balance or 0.0
                if balance < 0:
                    item.setForeground(2, QColor("#dc3545"))
                elif balance > 0:
                    item.setForeground(2, QColor("#28a745"))
                
                if account.is_system:
                    item.setForeground(0, QColor("#6c757d"))
                
                item.setData(0, Qt.UserRole, account.id or 0)
                item.setData(0, Qt.UserRole + 1, account.is_system or False)
                
                # Восстанавливаем выделение
                if account.id in selected_ids:
                    item.setSelected(True)
                
                self.accounts_tree.addTopLevelItem(item)
                
                # Обновляем прогресс каждые 50 счетов
                if i % 50 == 0:
                    QApplication.processEvents()
            
            # Включаем обновление виджета
            self.accounts_tree.setUpdatesEnabled(True)
            
            # Восстанавливаем скролл
            self.accounts_tree.verticalScrollBar().setValue(scroll_pos)
            
            # Обновляем таблицу
            self.accounts_tree.viewport().update()
            
            self.show_status(f"Отображено: {len(display_accounts)} счетов", "success")
            
        except Exception as e:
            self.show_status(f"Ошибка: {str(e)[:100]}", "error")
            logger.error(f"Ошибка обновления таблицы: {e}")
        
    def _add_account(self):
        """Добавляет новый счет"""
        try:
            # Валидация
            name = self.name_input.text().strip()
            if not name:
                self.show_status("Введите название счета", "warning")
                return
            
            acc_type = self.type_combo.currentText()
            
            # Проверка дубликатов (опционально, для быстрого ответа)
            for acc in self.current_accounts:
                if acc.name.lower() == name.lower():
                    self.show_status(f"Счет '{name}' уже существует", "error")
                    return
            
            # Получение данных
            initial_balance = parse_float(self.initial_balance_input.text(), raise_error=True)
            
            # Подготовка данных для БД
            account_data = {
                'name': name,
                'type': acc_type,
                'initial_balance': initial_balance,
                'current_balance': initial_balance,
                'currency': self.currency_combo.currentText(),
                'is_active': True,
                'is_system': False
            }
            
            # Для кредитных карт
            if acc_type == "Credit Card":
                account_data['credit_limit'] = parse_float(self.credit_limit_input.text(), raise_error=True)
                account_data['payment_due_day'] = parse_int(self.payment_day_input.text(), raise_error=True)
                account_data['min_payment_percent'] = parse_float(self.min_payment_input.text(), raise_error=True)
            
            # Вызов презентера
            self.presenter.add_account(account_data)
            
        except ValueError as e:
            self.show_status(f"Некорректное число: {str(e)}", "error")
        except Exception as e:
            self.show_status(f"Ошибка: {str(e)}", "error")
            logger.error(f"Ошибка добавления счета: {e}")

    def _edit_account(self):
        """Редактирует существующий счет"""
        if not self.editing_account_id:
            self.show_status("Не выбран счет для редактирования", "warning")
            return
        
        try:
            # Находим счет для проверки системности
            current_account = None
            for acc in self.current_accounts:
                if acc.id == self.editing_account_id:
                    current_account = acc
                    break
            
            if not current_account:
                self.show_status("Счет не найден", "error")
                return
            
            is_system = current_account.is_system or False
            
            # Валидация
            name = self.name_input.text().strip()
            if not name:
                self.show_status("Введите название счета", "warning")
                return
            
            # Проверка дубликатов
            for acc in self.current_accounts:
                if (acc.name.lower() == name.lower() and
                    acc.id != self.editing_account_id):
                    self.show_status(f"Счет '{name}' уже существует", "error")
                    return
            
            # Подготовка данных для обновления
            account_data = {
                'name': name,
                'currency': self.currency_combo.currentText()
            }
            
            # Для несистемных счетов можно менять тип
            if not is_system and self.type_combo.isVisible():
                account_data['type'] = self.type_combo.currentText()
                
                # Для кредитных карт
                if account_data['type'] == "Credit Card":
                    account_data['credit_limit'] = parse_float(self.credit_limit_input.text(), raise_error=True)
                    account_data['payment_due_day'] = parse_int(self.payment_day_input.text(), raise_error=True)
                    account_data['min_payment_percent'] = parse_float(self.min_payment_input.text(), raise_error=True)
                else:
                    # Для не-кредитных карт обнуляем кредитные поля
                    account_data['credit_limit'] = 0.0
                    account_data['payment_due_day'] = 1
                    account_data['min_payment_percent'] = 5.0
            
            # Вызов презентера
            self.presenter.update_account(self.editing_account_id, account_data)
            
        except ValueError as e:
            self.show_status(f"Некорректное число: {str(e)}", "error")
        except Exception as e:
            self.show_status(f"Ошибка: {str(e)}", "error")
            logger.error(f"Ошибка редактирования счета: {e}")

           
    def _reset_form(self):
        """Сбрасывает форму в исходное состояние"""
        self.name_input.clear()
        self.type_combo.setCurrentIndex(1)  # Bank Account
        self.type_label.setVisible(True)
        self.type_combo.setVisible(True)
        self.type_combo.setEnabled(True)
        
        # Восстанавливаем начальный баланс как редактируемое поле
        self.initial_balance_label.setText("Начальный баланс:")
        self.initial_balance_input.setVisible(True)
        self.initial_balance_input.setText("0.00")
        
        self.credit_limit_input.setText("0.00")
        self.payment_day_input.setText("1")
        self.min_payment_input.setText("5.0")
        self.currency_combo.setCurrentText("RUB")
        
        self.editing_account_id = None
        self.add_button.setEnabled(True)
        self.edit_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        
        # Снимаем выделение в дереве
        self.accounts_tree.clearSelection()
        self._on_type_change()
        
    def _show_context_menu(self, position):
        """Показывает контекстное меню"""
        menu = QMenu(self)
        
        # Только если что-то выбрано
        selected_items = self.accounts_tree.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        account_id = item.data(0, Qt.UserRole)
        is_system = item.data(0, Qt.UserRole + 1)
        
        # Редактировать
        edit_action = menu.addAction("✏️ Редактировать")
        edit_action.triggered.connect(self._on_account_select)
        
        # Удалить (только для несистемных счетов)
        if not is_system:
            delete_action = menu.addAction("🗑️ Удалить")
            delete_action.triggered.connect(self._delete_selected_accounts)
        
        menu.addSeparator()
        
        # Статистика
        stats_action = menu.addAction("📊 Статистика")
        stats_action.triggered.connect(self._show_account_stats)

        menu.addSeparator()
        
        # Обновить список
        refresh_action = menu.addAction("🔄 Обновить список")
        refresh_action.triggered.connect(self._load_accounts)
        
        menu.exec_(self.accounts_tree.viewport().mapToGlobal(position))
    
    def _delete_selected_accounts(self):
        """Удаляет выбранные счета"""
        selected_items = self.accounts_tree.selectedItems()
        if not selected_items:
            self.show_status("Выберите счета для удаления", "warning")
            return
        
        # Фильтруем только несистемные счета
        non_system_items = []
        for item in selected_items:
            if not item.data(0, Qt.UserRole + 1):  # несистемный
                non_system_items.append(item)
        
        if not non_system_items:
            self.show_status("Выбранные счета являются системными и не могут быть удалены", "warning")
            return
        
        # Подтверждение
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить {len(non_system_items)} счетов?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        success_count = 0
        blocked_count = 0
        error_count = 0
        
        # Используем список для удаления
        items_to_delete = non_system_items.copy()
        
        for item in items_to_delete:
            account_id = item.data(0, Qt.UserRole)
            account_name = item.text(0)
            
            # Вызов презентера
            result = self.presenter.delete_account(account_id)
            
            if result.get('success', False):
                success_count += 1
                self.show_status(f"Удален: {account_name}", "info")
            else:
                # Счет имеет операции - нельзя удалить
                if not result.get('can_delete', True):
                    blocked_count += 1
                    # Показываем сообщение о том, что счет имеет операции
                    self._show_cannot_delete_message({
                        'account_name': account_name,
                        'operations': result.get('operations', []),
                        'total_operations': result.get('total_operations', 0)
                    })
                else:
                    error_count += 1
                    self.show_status(f"Ошибка удаления счета '{account_name}': {result.get('message', 'Неизвестная ошибка')}", "error")
        
        # Показываем итог
        self._show_delete_result(success_count, error_count, blocked_count)
    
    def _show_cannot_delete_message(self, result_info):
        """Показывает сообщение о невозможности удаления"""
        try:
            account_name = result_info.get('account_name', 'Счет')
            operations = result_info.get('operations', [])
            total_operations = result_info.get('total_operations', 0)
            
            # Безопасное создание HTML
            operations_html = ""
            for op in operations:
                # Проверяем что op это строка
                if isinstance(op, str):
                    op_text = op.replace('<', '&lt;').replace('>', '&gt;')
                    operations_html += f'<li>{op_text}</li>'
                else:
                    operations_html += f'<li>{str(op)}</li>'
            
            html_text = f"""
                <h3 style='color: #dc3545;'>❌ Счет нельзя удалить</h3>
                <p>Счет <b>{account_name.replace('<', '&lt;').replace('>', '&gt;')}</b> имеет связанные операции:</p>
                <ul>
                    {operations_html}
                </ul>
                <p><b>Всего операций:</b> {total_operations}</p>
                <p style='color: #6c757d;'>
                    Для удаления счета необходимо сначала удалить все связанные операции 
                    или перенести их на другие счета.
                </p>
            """
            
            # Показываем диалог с деталями
            details_dialog = QDialog(self)
            details_dialog.setWindowTitle("Нельзя удалить счет")
            details_dialog.resize(450, 350)
            
            layout = QVBoxLayout(details_dialog)
            
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setHtml(html_text)
            
            layout.addWidget(text_edit)
            
            button_box = QDialogButtonBox(QDialogButtonBox.Ok)
            button_box.accepted.connect(details_dialog.accept)
            layout.addWidget(button_box)
            
            details_dialog.exec()
            
        except Exception as e:
            # Упрощенное сообщение в случае ошибки форматирования
            QMessageBox.warning(
                self,
                "Невозможно удалить счет",
                f"Счет '{result_info.get('account_name', 'Неизвестный')}' имеет связанные операции и не может быть удален.\n\n"
                f"Всего операций: {result_info.get('total_operations', 0)}"
            )
        
    
    def _show_delete_result(self, success, error, blocked, system=0):
        """Показывает результат удаления"""
        messages = []
        if success > 0:
            messages.append(f"✅ Удалено: {success}")
        if blocked > 0:
            messages.append(f"🚫 Заблокировано: {blocked}")
        if error > 0:
            messages.append(f"❌ Ошибок: {error}")
        if system > 0:
            messages.append(f"⚠️ Системных: {system}")
        
        if messages:
            self.show_status(" | ".join(messages), "info" if success > 0 else "warning")
    
    def _show_account_stats(self):
        """Показывает статистику по выбранному счету"""
        selected_items = self.accounts_tree.selectedItems()
        if not selected_items:
            self.show_status("Выберите счет для статистики", "warning")
            return
        
        item = selected_items[0]
        account_id = item.data(0, Qt.UserRole)
        account_name = item.text(0)
        
        try:
            # Получаем данные счета
            account_obj = self.database.accounts.get_by_id(account_id)
            if account_obj is None:
                self.show_status("Данные счета не найдены", "error")
                return
            account_data = account_obj.to_dict()
            
            # Получаем транзакции
            transactions = self.database.transactions.get_transactions(filters={'account_id': account_id, 'exclude_corrections': True})
            
            # Получаем переводы
            transfers = self.database.transfers.get_transfers(filters={'account_id': account_id})
            
            # Вычисляем статистику
            total_income = 0.0
            total_expense = 0.0
            transaction_count = len(transactions)
            
            for t in transactions:
                amount = t['amount']
                if t['type'] == 'income':
                    total_income += amount
                elif t['type'] == 'expense':
                    total_expense += abs(amount)
            
            transfers_in = 0
            transfers_out = 0
            
            for t in transfers:
                if t['to_account_id'] == account_id:
                    transfers_in += 1
                elif t['from_account_id'] == account_id:
                    transfers_out += 1
            
            # Формируем сообщение
            stats_text = f"📊 Статистика счета: {account_data['name']}\n\n"
            stats_text += f"💰 Текущий баланс: {account_data['current_balance']:.2f} {account_data['currency']}\n"
            stats_text += f"📈 Всего доходов: {total_income:.2f} {account_data['currency']}\n"
            stats_text += f"📉 Всего расходов: {total_expense:.2f} {account_data['currency']}\n"
            stats_text += f"🔄 Чистый поток: {total_income - total_expense:.2f} {account_data['currency']}\n\n"
            
            stats_text += f"📋 Количество операций:\n"
            stats_text += f"   • Транзакций: {transaction_count}\n"
            stats_text += f"   • Входящих переводов: {transfers_in}\n"
            stats_text += f"   • Исходящих переводов: {transfers_out}\n"
            stats_text += f"   • Всего: {transaction_count + transfers_in + transfers_out}\n\n"
            
            stats_text += f"🗓️ Тип счета: {account_data['type']}\n"
            
            if account_data['type'] == 'Credit Card':
                stats_text += f"💳 Кредитный лимит: {account_data.get('credit_limit', 0.0):.2f} {account_data['currency']}\n"
                stats_text += f"📅 День платежа: {account_data.get('payment_due_day', 1)}\n"
                stats_text += f"📊 Мин. платеж: {account_data.get('min_payment_percent', 5.0):.1f}%\n"
            
            # Дата создания
            created_at = account_data.get('created_at', '')
            if created_at:
                if isinstance(created_at, str):
                    stats_text += f"📅 Создан: {created_at[:10]}\n"
            
            # Показываем диалог
            stats_dialog = QDialog(self)
            stats_dialog.setWindowTitle(f"Статистика: {account_data['name']}")
            stats_dialog.resize(400, 400)
            
            layout = QVBoxLayout(stats_dialog)
            
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setPlainText(stats_text)
            text_edit.setFont(QFont("Consolas", 10))
            
            layout.addWidget(text_edit)
            
            button_box = QDialogButtonBox(QDialogButtonBox.Ok)
            button_box.accepted.connect(stats_dialog.accept)
            layout.addWidget(button_box)
            
            stats_dialog.exec()
            
        except Exception as e:
            self.show_status(f"Ошибка статистики: {str(e)[:50]}", "error")
            logger.error(f"Ошибка показа статистики: {e}")
    
    # --- Вспомогательные методы ---
    
    def show_status(self, message, message_type="info"):
        """Показывает сообщение в статус-баре"""
        # Устанавливаем CSS классы для стилизации
        class_name = f"status status-{message_type} status-bold"
        self.status_bar.setProperty("class", class_name)
        self.status_bar.setText(message)
        # Принудительно обновляем стиль после изменения свойства
        self.status_bar.style().unpolish(self.status_bar)
        self.status_bar.style().polish(self.status_bar)
        
        # Автоматический сброс через 3 секунды
        if message_type != "error":  # Ошибки не сбрасываем автоматически
            QTimer.singleShot(3000, self._reset_status)
    
    def _reset_status(self):
        """Сбрасывает статус-бар"""
        self.status_bar.setText("Готово")
        self.status_bar.setProperty("class", "status")
        self.status_bar.style().unpolish(self.status_bar)
        self.status_bar.style().polish(self.status_bar)


# Алиас для обратной совместимости
AccountDialog = AccountManagementDialog
