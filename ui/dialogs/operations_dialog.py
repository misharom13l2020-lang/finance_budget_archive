# ui/dialogs/operations_dialog.py - Исправленная версия
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QLineEdit, QComboBox, QPushButton, QFrame, QMessageBox,
    QScrollArea, QTextEdit, QProgressBar, QGroupBox, QGridLayout,
    QHeaderView, QSplitter, QMenu, QApplication, QWidget
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer, QDate
from PySide6.QtGui import QFont, QColor, QAction, QPalette
from datetime import datetime, date, timedelta
from PySide6.QtWidgets import QDateEdit, QFormLayout, QToolButton
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QMenu, QInputDialog
from PySide6.QtCore import Qt, QPoint
from datetime import date, timedelta
from PySide6.QtGui import QFont, QColor, QAction, QPalette, QKeyEvent, QIcon
from datetime import datetime, date, timedelta



from core.database import DatabaseManager
from ui.dialogs.edit_transaction_dialog import EditTransactionDialog
from ui.dialogs.date_range_dialog import DateRangeDialog
from ui.dialogs.account_dialog import AccountManagementDialog
from ui.dialogs.category_dialog import CategoryManagementDialog
from ui.dialogs.transfer_dialog import TransferDialog
from ui.dialogs.reconciliation_dialog import ReconciliationDialog
from ui.dialogs.loan_dialog import LoanManagementWindow
from ui.dialogs.credit_cards_window import CreditCardsWindow
from ui.widgets.date_widgets import DateNavigator, DateUtils
from ui.widgets.window_utils import center_window_relative



class CompactButton(QPushButton):
    """Компактная кнопка с минимальным размером"""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                font-weight: 500;
                font-size: 12px;
                margin: 1px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.setFixedHeight(26)


class FilterButton(QPushButton):
    """Компактная кнопка для фильтров"""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 11px;
                margin: 1px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        self.setFixedHeight(26)


class HeaderFilterWidget(QWidget):
    """Виджет фильтра в заголовке таблицы"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ced4da;
                border-radius: 2px;
                padding: 2px;
                font-size: 10px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 1px solid #80bdff;
            }
            QComboBox {
                border: 1px solid #ced4da;
                border-radius: 2px;
                padding: 2px;
                font-size: 10px;
                background-color: white;
            }
        """)


class OperationsDialog(QDialog):
    data_updated = Signal()
    
    def __init__(self, parent, db: DatabaseManager, accounts_data=None):
        super().__init__(parent)
        self.parent = parent
        self.db = db
        self.setWindowTitle("Операции")
        self.resize(1200, 600)
        
        center_window_relative(self, parent)
        
        # Стиль для всего диалога
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
            }
            QTreeWidget {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 3px;
                alternate-background-color: #f8f9fa;
                font-size: 11px;
            }
            QTreeWidget::item {
                padding: 2px;
                min-height: 22px;
            }
            QTreeWidget::item:selected {
                background-color: #e3f2fd;
                color: black;
            }
            QLabel {
                color: #495057;
                font-size: 12px;
            }
        """)
        
        self.accounts_data = accounts_data or {}
        self.current_filters = {
            "date_from": None, "date_to": None, "trans_type": None,
            "category_id": None, "account_id": None, "description_text": None
        }
        self.category_id_by_display_name = {}
        self.category_filter_mapping = {} 
        self.input_category_id_by_display_name = {}
        
        # Хранилище открытых окон (чтобы не открывать несколько раз)
        self.open_windows = {}
        
        self._init_ui()
        self._load_all_data()
        self._update_display()
        self._setup_keyboard_shortcuts()
        self._create_filter_menus()
        
    def _init_ui(self):
        """Инициализация интерфейса."""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 1. Панель операций (горизонтальная)
        operations_panel = QHBoxLayout()
        operations_panel.setSpacing(8)
        
        buttons = [
            ("🏦 Счета", self._open_account_management, "#2196F3"),
            ("📊 Категории", self._open_category_management, "#9C27B0"),
            ("📤 Переводы", self._open_transfer_dialog, "#FF9800"),
            ("🔍 Сверка", self._open_reconciliation_dialog, "#607D8B"),
            ("💰 Займы", self._open_loan_management, "#795548"),
            ("💳 Кредитные карты", self._open_credit_cards, "#E91E63")
        ]
        
        for text, callback, color in buttons:
            btn = CompactButton(text)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    border: none;
                    border-radius: 3px;
                    padding: 4px 12px;
                    font-weight: 500;
                    font-size: 11px;
                    margin: 0px;
                    min-width: 80px;
                }}
                QPushButton:hover {{
                    background-color: {self._darken_color(color)};
                }}
                QPushButton:pressed {{
                    background-color: {self._darken_color(color, 30)};
                }}
            """)
            btn.setFixedHeight(26)
            btn.clicked.connect(callback)
            operations_panel.addWidget(btn)
        
        operations_panel.addStretch()
        main_layout.addLayout(operations_panel)
        
        # 2. Панель фильтров
        filter_panel = QHBoxLayout()
        filter_panel.setSpacing(6)
        
        # Фильтр по типу
        filter_panel.addWidget(QLabel("Тип:"))
        self.type_filter_combo = QComboBox()
        self.type_filter_combo.addItems(["Все", "Доход", "Расход", "Возврат"])
        self.type_filter_combo.currentTextChanged.connect(self._apply_filters)
        self.type_filter_combo.setFixedHeight(26)
        self.type_filter_combo.setMinimumWidth(80)
        filter_panel.addWidget(self.type_filter_combo)
        
        # Фильтр по категории
        filter_panel.addWidget(QLabel("Категория:"))
        self.category_filter_combo = QComboBox()
        self.category_filter_combo.addItem("Все категории")
        self.category_filter_combo.currentTextChanged.connect(self._apply_filters)
        self.category_filter_combo.setFixedHeight(26)
        self.category_filter_combo.setMinimumWidth(150)
        filter_panel.addWidget(self.category_filter_combo)
        
        # Фильтр по счету
        filter_panel.addWidget(QLabel("Счет:"))
        self.account_filter_combo = QComboBox()
        self.account_filter_combo.addItem("Все счета")
        self.account_filter_combo.currentTextChanged.connect(self._apply_filters)
        self.account_filter_combo.setFixedHeight(26)
        self.account_filter_combo.setMinimumWidth(120)
        filter_panel.addWidget(self.account_filter_combo)
        
        # Фильтр по периоду
        filter_panel.addWidget(QLabel("Период:"))
        self.period_combo = QComboBox()
        self.period_combo.addItems([
            "За все время", "Сегодня", "Вчера", "Эта неделя", "Прошлая неделя",
            "Этот месяц", "Прошлый месяц", "Этот год", "Прошлый год", "Выбрать период..."
        ])
        self.period_combo.currentIndexChanged.connect(self._apply_period_filter)
        self.period_combo.setFixedHeight(26)
        self.period_combo.setMinimumWidth(120)
        filter_panel.addWidget(self.period_combo)
        
        # Поиск
        filter_panel.addWidget(QLabel("Поиск:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("по описанию...")
        self.search_input.textChanged.connect(self._apply_filters)
        self.search_input.setFixedHeight(26)
        self.search_input.setMinimumWidth(150)
        filter_panel.addWidget(self.search_input)
        
        # Кнопка сброса
        reset_btn = FilterButton("Сбросить фильтры")
        reset_btn.clicked.connect(self._reset_all_filters)
        reset_btn.setFixedHeight(26)
        filter_panel.addWidget(reset_btn)
        
        filter_panel.addStretch()
        main_layout.addLayout(filter_panel)
        
        # 3. Форма ввода новой операции (одна строка)
        input_panel = QHBoxLayout()
        input_panel.setSpacing(8)
        
        input_panel.addWidget(QLabel("Новая операция:"))
        
        # Дата с навигацией
        self.date_navigator = DateNavigator(default_date=QDate.currentDate())
        self.date_navigator.setFixedHeight(26)
        input_panel.addWidget(self.date_navigator)
        
        # Сумма
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("Сумма")
        self.amount_input.setFixedHeight(26)
        self.amount_input.setMinimumWidth(100)
        input_panel.addWidget(self.amount_input)
        
        # Тип
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Расход", "Доход"])
        self.type_combo.currentTextChanged.connect(self._update_category_and_account_combos)
        self.type_combo.setFixedHeight(26)
        self.type_combo.setMinimumWidth(80)
        input_panel.addWidget(self.type_combo)
        
        # Категория
        self.category_combo = QComboBox()
        self.category_combo.setFixedHeight(26)
        self.category_combo.setMinimumWidth(150)
        input_panel.addWidget(self.category_combo)
        
        # Счет
        self.account_combo = QComboBox()
        self.account_combo.setFixedHeight(26)
        self.account_combo.setMinimumWidth(120)
        input_panel.addWidget(self.account_combo)
        
        # Описание
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Описание...")
        self.description_input.setFixedHeight(26)
        self.description_input.setMinimumWidth(200)
        input_panel.addWidget(self.description_input)
        
        # Кнопка добавления
        add_button = CompactButton("Добавить")
        add_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 16px;
                font-weight: bold;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        add_button.setFixedHeight(26)
        add_button.clicked.connect(self._add_transaction)
        input_panel.addWidget(add_button)
        
        input_panel.addStretch()
        main_layout.addLayout(input_panel)
        
        # 4. Таблица транзакций
        self.transactions_tree = QTreeWidget()
        self.transactions_tree.setHeaderLabels(["Дата", "Тип", "Сумма", "Количество", "Категория", "Счет", "Описание"])
        
        # Настройка колонок
        header = self.transactions_tree.header()
        header.setStretchLastSection(True)
        header.setDefaultAlignment(Qt.AlignCenter)
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        
        # Размеры колонок
        self.transactions_tree.setColumnWidth(0, 110)   # Дата
        self.transactions_tree.setColumnWidth(1, 80)    # Тип
        self.transactions_tree.setColumnWidth(2, 100)   # Сумма
        self.transactions_tree.setColumnWidth(3, 80)    # Количество
        self.transactions_tree.setColumnWidth(4, 150)   # Категория
        self.transactions_tree.setColumnWidth(5, 120)   # Счет
        
        # Включаем расширенный выбор
        self.transactions_tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        
        # Включаем сортировку
        self.transactions_tree.setSortingEnabled(True)
        
        # Устанавливаем начальную сортировку по дате (колонка 0) в порядке убывания
        self.transactions_tree.sortItems(0, Qt.DescendingOrder)
        header.setSortIndicator(0, Qt.DescendingOrder)
        
        # Альтернативные цвета строк
        self.transactions_tree.setAlternatingRowColors(True)
        
        # Контекстное меню
        self.transactions_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.transactions_tree.customContextMenuRequested.connect(self._show_transactions_context_menu)
        
        # Обработка клавиши Shift для множественного выбора
        self.transactions_tree.installEventFilter(self)
        
        main_layout.addWidget(self.transactions_tree, 1)
        
        # 5. Панель итогов и кнопок
        summary_panel = QHBoxLayout()
        summary_panel.setSpacing(8)
        
        self.summary_label = QLabel("Операций: 0")
        self.summary_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: #495057;
                font-size: 12px;
                padding: 4px 10px;
                background-color: #e9ecef;
                border-radius: 3px;
                border: 1px solid #dee2e6;
            }
        """)
        summary_panel.addWidget(self.summary_label)
        
        summary_panel.addStretch()
        
        # Кнопка экспорта
        export_btn = CompactButton("Экспорт")
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 12px;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        export_btn.setFixedHeight(26)
        export_btn.clicked.connect(self._export_data)
        summary_panel.addWidget(export_btn)
        
        # Кнопка закрытия
        close_button = CompactButton("Закрыть")
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 16px;
                font-weight: 500;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        close_button.setFixedHeight(26)
        close_button.clicked.connect(self.accept)
        summary_panel.addWidget(close_button)
        
        main_layout.addLayout(summary_panel)
        
        # 6. Строка статуса
        self.status_bar = QLabel("Готово")
        self.status_bar.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-size: 11px;
                padding: 4px 8px;
                background-color: #f8f9fa;
                border-radius: 2px;
                border-top: 1px solid #dee2e6;
            }
        """)
        self.status_bar.setFixedHeight(26)
        main_layout.addWidget(self.status_bar)
        
        self.setLayout(main_layout)
        
        # Установка фокуса
        QTimer.singleShot(100, lambda: self.amount_input.setFocus())
        
        # Не модальное окно
        self.setModal(False)
    
    def _darken_color(self, hex_color, percent=20):
        """Затемняет hex-цвет на указанный процент"""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        r = max(0, min(255, int(r * (100 - percent) / 100)))
        g = max(0, min(255, int(g * (100 - percent) / 100)))
        b = max(0, min(255, int(b * (100 - percent) / 100)))
        
        return f'#{r:02x}{g:02x}{b:02x}'
    
    # --- Методы загрузки данных ---
    
   
    def _update_category_filter_combo(self):
        """Обновляет комбобокс фильтра категорий с иерархическим отображением."""
        try:
            # Сохраняем текущий выбор
            current_text = self.category_filter_combo.currentText()
            
            # Блокируем сигналы, чтобы не вызвать _apply_filters
            self.category_filter_combo.blockSignals(True)
            self.category_filter_combo.clear()
            self.category_filter_combo.addItem("Все категории")
            
            # Сбрасываем словарь соответствия для фильтра
            self.category_id_by_display_name = {}
            
            # Определяем, какой тип сейчас выбран в фильтре
            filter_type = None
            type_text = self.type_filter_combo.currentText()
            if type_text == "Доход":
                filter_type = "income"
            elif type_text == "Расход":
                filter_type = "expense"
            
            # Загружаем категории для фильтра
            all_categories = []
            
            try:
                if filter_type:
                    # Загружаем только категории выбранного типа
                    try:
                        all_categories = self.db.get_category_hierarchy(type=filter_type)
                    except Exception as e:
                        print(f"Ошибка загрузки категорий {filter_type}: {e}")
                        # Пробуем альтернативный метод
                        all_categories = self.db.get_categories(type=filter_type, include_subcategories=True)
                else:
                    # Если выбран "Все", загружаем все категории
                    try:
                        # 1. Загружаем категории расходов
                        expense_cats = self.db.get_category_hierarchy(type="expense")
                        if expense_cats:
                            all_categories.extend(expense_cats)
                    except Exception as e:
                        print(f"Ошибка загрузки категорий расходов: {e}")
                    
                    try:
                        # 2. Загружаем категории доходов
                        income_cats = self.db.get_category_hierarchy(type="income")
                        if income_cats:
                            all_categories.extend(income_cats)
                    except Exception as e:
                        print(f"Ошибка загрузки категорий доходов: {e}")
            except Exception as e:
                print(f"Критическая ошибка загрузки категорий: {e}")
                # Разблокируем сигналы и выходим
                self.category_filter_combo.blockSignals(False)
                return
            
            # Если не удалось загрузить иерархию, пробуем получить все категории
            if not all_categories:
                try:
                    if filter_type:
                        all_categories = self.db.get_categories(type=filter_type, include_subcategories=True)
                    else:
                        all_categories = self.db.get_categories(include_subcategories=True)
                except:
                    all_categories = []
            
            # Добавляем категории с иерархическим отображением
            if all_categories:
                # Сортируем: сначала по типу (расходы, потом доходы), потом по пути
                if isinstance(all_categories[0], dict) and 'path' in all_categories[0]:
                    # Добавляем метку типа для группировки только если показываем все категории
                    if not filter_type:
                        for cat in all_categories:
                            cat_type = cat.get('type', 'expense')
                            if cat_type == 'income':
                                cat['path'] = f"Доходы > {cat.get('path', cat.get('name', ''))}"
                            else:
                                cat['path'] = f"Расходы > {cat.get('path', cat.get('name', ''))}"
                    
                    all_categories.sort(key=lambda x: x.get('path', x.get('name', '')))
                    
                    for cat in all_categories:
                        cat_id = cat.get('id')
                        name = cat.get('name', '')
                        path = cat.get('path', name)
                        level = cat.get('level', 0)
                        
                        if not cat_id or not name:
                            continue
                        
                        # Создаем визуальное отображение с иерархией
                        # Учитываем уровень + 1 из-за добавленной группировки
                        if not filter_type:
                            display_level = level + 1
                            indent = '  ' * display_level
                        else:
                            display_level = level
                            indent = '  ' * display_level
                        
                        # Для корневых категорий группировки (Доходы/Расходы) показываем без маркера
                        if not filter_type and level == 0:
                            display_text = f"  {name}"
                        else:
                            display_text = f"{indent}• {name}"
                        
                        # Добавляем в комбобокс фильтра
                        self.category_filter_combo.addItem(display_text)
                        self.category_id_by_display_name[display_text] = cat_id
                
                elif isinstance(all_categories[0], dict) and 'level' in all_categories[0]:
                    # Если показываем все категории, группируем по типу
                    if not filter_type:
                        expense_cats = [c for c in all_categories if c.get('type', 'expense') == 'expense']
                        income_cats = [c for c in all_categories if c.get('type') == 'income']
                        
                        # Добавляем группировку "Расходы"
                        if expense_cats:
                            self.category_filter_combo.addItem("  Расходы")
                            expense_cats.sort(key=lambda x: (x.get('level', 0), x.get('name', '')))
                            
                            for cat in expense_cats:
                                cat_id = cat.get('id')
                                name = cat.get('name', '')
                                level = cat.get('level', 0)
                                
                                if not cat_id or not name:
                                    continue
                                
                                # Визуализация иерархии с отступом
                                if level == 0:
                                    display_text = f"    • {name}"
                                elif level == 1:
                                    display_text = f"      • {name}"
                                elif level == 2:
                                    display_text = f"        • {name}"
                                else:
                                    indent = '      ' + '  ' * level
                                    display_text = f"{indent}• {name}"
                                
                                self.category_filter_combo.addItem(display_text)
                                self.category_id_by_display_name[display_text] = cat_id
                        
                        # Добавляем группировку "Доходы"
                        if income_cats:
                            self.category_filter_combo.addItem("  Доходы")
                            income_cats.sort(key=lambda x: (x.get('level', 0), x.get('name', '')))
                            
                            for cat in income_cats:
                                cat_id = cat.get('id')
                                name = cat.get('name', '')
                                level = cat.get('level', 0)
                                
                                if not cat_id or not name:
                                    continue
                                
                                # Визуализация иерархии с отступом
                                if level == 0:
                                    display_text = f"    • {name}"
                                elif level == 1:
                                    display_text = f"      • {name}"
                                elif level == 2:
                                    display_text = f"        • {name}"
                                else:
                                    indent = '      ' + '  ' * level
                                    display_text = f"{indent}• {name}"
                                
                                self.category_filter_combo.addItem(display_text)
                                self.category_id_by_display_name[display_text] = cat_id
                    else:
                        # Показываем категории только выбранного типа
                        all_categories.sort(key=lambda x: (x.get('level', 0), x.get('name', '')))
                        
                        for cat in all_categories:
                            cat_id = cat.get('id')
                            name = cat.get('name', '')
                            level = cat.get('level', 0)
                            
                            if not cat_id or not name:
                                continue
                            
                            # Визуализация иерархии с отступом
                            if level == 0:
                                display_text = f"  • {name}"
                            elif level == 1:
                                display_text = f"    • {name}"
                            elif level == 2:
                                display_text = f"      • {name}"
                            else:
                                indent = '    ' + '  ' * level
                                display_text = f"{indent}• {name}"
                            
                            self.category_filter_combo.addItem(display_text)
                            self.category_id_by_display_name[display_text] = cat_id
                
                else:
                    # Простой список без иерархии
                    if not filter_type:
                        # Группируем по типу если показываем все
                        expense_cats = []
                        income_cats = []
                        
                        for cat in all_categories:
                            if isinstance(cat, dict):
                                cat_id = cat.get('id')
                                name = cat.get('name', '')
                                cat_type = cat.get('type', 'expense')
                            else:
                                continue
                            
                            if not cat_id or not name:
                                continue
                            
                            if cat_type == 'income':
                                income_cats.append((cat_id, name))
                            else:
                                expense_cats.append((cat_id, name))
                        
                        # Добавляем расходы
                        if expense_cats:
                            self.category_filter_combo.addItem("  Расходы")
                            expense_cats.sort(key=lambda x: x[1])
                            for cat_id, name in expense_cats:
                                self.category_filter_combo.addItem(f"    • {name}")
                                self.category_id_by_display_name[f"    • {name}"] = cat_id
                        
                        # Добавляем доходы
                        if income_cats:
                            self.category_filter_combo.addItem("  Доходы")
                            income_cats.sort(key=lambda x: x[1])
                            for cat_id, name in income_cats:
                                self.category_filter_combo.addItem(f"    • {name}")
                                self.category_id_by_display_name[f"    • {name}"] = cat_id
                    else:
                        # Показываем только категории выбранного типа
                        for cat in all_categories:
                            if isinstance(cat, dict):
                                cat_id = cat.get('id')
                                name = cat.get('name', '')
                            else:
                                continue
                            
                            if not cat_id or not name:
                                continue
                            
                            self.category_filter_combo.addItem(f"  • {name}")
                            self.category_id_by_display_name[f"  • {name}"] = cat_id
            
            # Восстанавливаем предыдущий выбор, если он есть
            if current_text and current_text != "Все категории":
                index = self.category_filter_combo.findText(current_text)
                if index >= 0:
                    self.category_filter_combo.setCurrentIndex(index)
            
            # Разблокируем сигналы
            self.category_filter_combo.blockSignals(False)
            
        except Exception as e:
            print(f"Ошибка обновления фильтра категорий: {e}")
            # Все равно разблокируем сигналы
            try:
                self.category_filter_combo.blockSignals(False)
            except:
                pass 
           
    def _update_category_and_account_combos(self):
        """Обновляет списки категорий и счетов с иерархией для ВВОДА НОВЫХ ОПЕРАЦИЙ."""
        try:
            current_type = self.type_combo.currentText().lower()
            
            # Определяем тип для БД
            db_type = None
            if current_type == "доход":
                db_type = "income"
            elif current_type == "расход":
                db_type = "expense"
            # Для возвратов не обновляем здесь - это отдельная операция
            
            # Очищаем комбобокс категорий
            self.category_combo.clear()
            
            # Сбрасываем словарь соответствия ДЛЯ ВВОДА
            self.input_category_id_by_display_name = {}
            
            # Загружаем категории только если это не возврат
            if current_type in ["доход", "расход"]:
                categories = []
                try:
                    # Получаем иерархию категорий только для выбранного типа
                    if db_type:
                        categories = self.db.get_category_hierarchy(type=db_type)
                    else:
                        # Если тип не выбран, показываем все категории
                        categories = self.db.get_category_hierarchy()
                except Exception as e:
                    print(f"Ошибка загрузки категорий: {e}")
                    try:
                        if db_type:
                            categories = self.db.get_categories(type=db_type, include_subcategories=True)
                        else:
                            categories = self.db.get_categories(include_subcategories=True)
                    except:
                        categories = []
                
                # Если категорий нет, показываем сообщение
                if not categories:
                    self.category_combo.addItem("Нет доступных категорий")
                    self.show_status_message(f"Нет категорий для типа: {current_type}", 2000, "warning")
                else:
                    # Строим структурированный список категорий
                    # Сортируем: сначала по типу, потом по пути (для иерархии)
                    if isinstance(categories[0], dict) and 'path' in categories[0]:
                        # Используем путь для сортировки (например: "Продукты > Молоко")
                        categories.sort(key=lambda x: (
                            x.get('type', ''),
                            x.get('path', x.get('name', ''))
                        ))
                        
                        for cat in categories:
                            cat_id = cat.get('id')
                            name = cat.get('name', '')
                            path = cat.get('path', name)
                            level = cat.get('level', 0)
                            
                            if not cat_id or not name:
                                continue
                            
                            # Создаем визуальное отображение с иерархией
                            # Используем точки для отступов подкатегорий
                            if level > 0:
                                # Используем точки для отступов
                                indent = '  ' * level  # Двойные пробелы для каждого уровня
                                display_text = f"{indent}• {name}"
                            else:
                                display_text = f"• {name}"  # Основные категории с маркером
                            
                            # Добавляем в комбобокс
                            self.category_combo.addItem(display_text)
                            self.input_category_id_by_display_name[display_text] = cat_id
                    
                    elif isinstance(categories[0], dict) and 'level' in categories[0]:
                        # Сортируем по уровню и имени
                        categories.sort(key=lambda x: (x.get('level', 0), x.get('name', '')))
                        
                        for cat in categories:
                            cat_id = cat.get('id')
                            name = cat.get('name', '')
                            level = cat.get('level', 0)
                            
                            if not cat_id or not name:
                                continue
                            
                            # Визуализация иерархии с точками
                            if level == 0:
                                display_text = f"• {name}"
                            elif level == 1:
                                display_text = f"  • {name}"
                            elif level == 2:
                                display_text = f"    • {name}"
                            else:
                                indent = '  ' * level
                                display_text = f"{indent}• {name}"
                            
                            self.category_combo.addItem(display_text)
                            self.input_category_id_by_display_name[display_text] = cat_id
                    
                    else:
                        # Простой список без иерархии
                        for cat in categories:
                            if isinstance(cat, dict):
                                cat_id = cat.get('id')
                                name = cat.get('name', '')
                            else:
                                continue
                            
                            if not cat_id or not name:
                                continue
                            
                            self.category_combo.addItem(name)
                            self.input_category_id_by_display_name[name] = cat_id
                
                # НЕ обновляем общий словарь category_id_by_display_name - он для фильтра
                
                # Обновляем список счетов с группировкой
                self._update_accounts_combo()
                
                # Выбираем первые элементы
                if self.category_combo.count() > 0:
                    self.category_combo.setCurrentIndex(0)
                if self.account_combo.count() > 0:
                    self.account_combo.setCurrentIndex(0)
                
                # ВАЖНО: При изменении типа в комбобоксе ввода НЕ обновляем фильтры
                # и таблицу - это нужно только при изменении фильтров
                # Если хотите автоматически применять фильтр по типу при выборе в комбобоксе ввода,
                # раскомментируйте следующую строку:
                # self._apply_filters()  # Но это может быть неудобно для пользователя
            
        except Exception as e:
            print(f"Ошибка обновления комбобоксов: {e}")
            self.show_status_message(f"Ошибка загрузки списков: {str(e)[:30]}", 2000, "error")
        
    def _apply_filters(self):
        """Применяет все установленные фильтры."""
        try:
            # Тип операции
            trans_type = None
            type_text = self.type_filter_combo.currentText()
            if type_text == "Доход":
                trans_type = "income"
            elif type_text == "Расход":
                trans_type = "expense"
            elif type_text == "Возврат":
                trans_type = "refund"  # Добавляем обработку возвратов
            
            # Блокируем сигналы категорий перед обновлением списка
            self.category_filter_combo.blockSignals(True)
            
            # Обновляем фильтр категорий в зависимости от выбранного типа
            self._update_category_filter_combo_for_filter(trans_type)
            
            # Категория - используем словарь category_id_by_display_name
            category_id = None
            category_text = self.category_filter_combo.currentText()
            if category_text != "Все категории":
                # Ищем ID категории в словаре, который заполняется в _update_category_filter_combo()
                category_id = self.category_id_by_display_name.get(category_text)
                if not category_id:
                    # Если не нашли по точному совпадению, пробуем найти без лишних пробелов
                    for key, value in self.category_id_by_display_name.items():
                        if key.strip() == category_text.strip():
                            category_id = value
                            break
            
            # Разблокируем сигналы
            self.category_filter_combo.blockSignals(False)
            
            # Счет
            account_id = None
            account_text = self.account_filter_combo.currentText()
            if account_text != "Все счета":
                for acc_id, info in self.accounts_data.items():
                    if info['name'] == account_text:
                        account_id = acc_id
                        break
            
            # Поиск (без учета регистра)
            description_text = self.search_input.text().strip() or None
            
            # Обновляем фильтры
            self.current_filters.update({
                "trans_type": trans_type,
                "category_id": category_id,
                "account_id": account_id,
                "description_text": description_text
            })
            
            # ВАЖНО: Обновляем отображение таблицы
            self._update_display()
            
        except Exception as e:
            print(f"Ошибка применения фильтров: {e}")
            # Все равно разблокируем сигналы
            try:
                self.category_filter_combo.blockSignals(False)
            except:
                pass
                
    def _update_category_filter_combo_for_filter(self, filter_type=None):
        """Обновляет комбобокс фильтра категорий для фильтрации."""
        try:
            # Сохраняем текущий выбор
            current_text = self.category_filter_combo.currentText()
            
            self.category_filter_combo.clear()
            self.category_filter_combo.addItem("Все категории")
            
            # Сбрасываем словарь соответствия для фильтра
            self.category_id_by_display_name = {}
            
            # Определяем, какой тип сейчас выбран в фильтре
            if filter_type == "income":
                db_type = "income"
            elif filter_type == "expense":
                db_type = "expense"
            elif filter_type == "refund":
                # Для возвратов показываем все категории (они могут быть и доходами и расходами)
                db_type = None
            else:
                db_type = None
            
            # Загружаем категории для фильтра
            all_categories = []
            
            try:
                if db_type:
                    # Загружаем только категории выбранного типа
                    try:
                        all_categories = self.db.get_category_hierarchy(type=db_type)
                    except Exception as e:
                        print(f"Ошибка загрузки категорий {db_type}: {e}")
                        # Пробуем альтернативный метод
                        all_categories = self.db.get_categories(type=db_type, include_subcategories=True)
                else:
                    # Если выбран "Все" или "Возврат", загружаем все категории
                    try:
                        # 1. Загружаем категории расходов
                        expense_cats = self.db.get_category_hierarchy(type="expense")
                        if expense_cats:
                            all_categories.extend(expense_cats)
                    except Exception as e:
                        print(f"Ошибка загрузки категорий расходов: {e}")
                    
                    try:
                        # 2. Загружаем категории доходов
                        income_cats = self.db.get_category_hierarchy(type="income")
                        if income_cats:
                            all_categories.extend(income_cats)
                    except Exception as e:
                        print(f"Ошибка загрузки категорий доходов: {e}")
            except Exception as e:
                print(f"Критическая ошибка загрузки категорий: {e}")
                return
            
            # Если не удалось загрузить иерархию, пробуем получить все категории
            if not all_categories:
                try:
                    if db_type:
                        all_categories = self.db.get_categories(type=db_type, include_subcategories=True)
                    else:
                        all_categories = self.db.get_categories(include_subcategories=True)
                except:
                    all_categories = []
            
            # Добавляем категории с иерархическим отображением
            if all_categories:
                # Сортируем: сначала по типу (расходы, потом доходы), потом по пути
                if isinstance(all_categories[0], dict) and 'path' in all_categories[0]:
                    # Добавляем метку типа для группировки только если показываем все категории
                    if not db_type:
                        for cat in all_categories:
                            cat_type = cat.get('type', 'expense')
                            if cat_type == 'income':
                                cat['path'] = f"Доходы > {cat.get('path', cat.get('name', ''))}"
                            else:
                                cat['path'] = f"Расходы > {cat.get('path', cat.get('name', ''))}"
                    
                    all_categories.sort(key=lambda x: x.get('path', x.get('name', '')))
                    
                    for cat in all_categories:
                        cat_id = cat.get('id')
                        name = cat.get('name', '')
                        path = cat.get('path', name)
                        level = cat.get('level', 0)
                        
                        if not cat_id or not name:
                            continue
                        
                        # Создаем визуальное отображение с иерархией
                        # Учитываем уровень + 1 из-за добавленной группировки
                        if not db_type:
                            display_level = level + 1
                            indent = '  ' * display_level
                        else:
                            display_level = level
                            indent = '  ' * display_level
                        
                        # Для корневых категорий группировки (Доходы/Расходы) показываем без маркера
                        if not db_type and level == 0:
                            display_text = f"  {name}"
                        else:
                            display_text = f"{indent}• {name}"
                        
                        # Добавляем в комбобокс фильтра
                        self.category_filter_combo.addItem(display_text)
                        self.category_id_by_display_name[display_text] = cat_id
                
                else:
                    # Простой список без иерархии
                    if not db_type:
                        # Группируем по типу если показываем все
                        expense_cats = []
                        income_cats = []
                        
                        for cat in all_categories:
                            if isinstance(cat, dict):
                                cat_id = cat.get('id')
                                name = cat.get('name', '')
                                cat_type = cat.get('type', 'expense')
                            else:
                                continue
                            
                            if not cat_id or not name:
                                continue
                            
                            if cat_type == 'income':
                                income_cats.append((cat_id, name))
                            else:
                                expense_cats.append((cat_id, name))
                        
                        # Добавляем расходы
                        if expense_cats:
                            self.category_filter_combo.addItem("  Расходы")
                            expense_cats.sort(key=lambda x: x[1])
                            for cat_id, name in expense_cats:
                                self.category_filter_combo.addItem(f"    • {name}")
                                self.category_id_by_display_name[f"    • {name}"] = cat_id
                        
                        # Добавляем доходы
                        if income_cats:
                            self.category_filter_combo.addItem("  Доходы")
                            income_cats.sort(key=lambda x: x[1])
                            for cat_id, name in income_cats:
                                self.category_filter_combo.addItem(f"    • {name}")
                                self.category_id_by_display_name[f"    • {name}"] = cat_id
                    else:
                        # Показываем только категории выбранного типа
                        for cat in all_categories:
                            if isinstance(cat, dict):
                                cat_id = cat.get('id')
                                name = cat.get('name', '')
                            else:
                                continue
                            
                            if not cat_id or not name:
                                continue
                            
                            self.category_filter_combo.addItem(f"  • {name}")
                            self.category_id_by_display_name[f"  • {name}"] = cat_id
            
            # Восстанавливаем предыдущий выбор, если он есть
            if current_text and current_text != "Все категории":
                index = self.category_filter_combo.findText(current_text)
                if index >= 0:
                    self.category_filter_combo.setCurrentIndex(index)
            
        except Exception as e:
            print(f"Ошибка обновления фильтра категорий: {e}")
            
        
    def _load_all_data(self):
        """Загружает все данные из БД."""
        try:
            # Загрузка счетов через новый API
            accounts = self.db.get_accounts()
            self.accounts_data = {}
            
            if accounts:
                for acc in accounts:
                    # Всегда работаем со словарями
                    if isinstance(acc, dict):
                        acc_id = acc.get('id')
                        acc_name = acc.get('name', 'Без названия')
                        acc_type = acc.get('type', 'Cash')
                        balance = float(acc.get('current_balance', 0))
                    else:
                        continue  # Пропускаем некорректные данные
                    
                    if acc_id is not None:
                        self.accounts_data[acc_id] = {
                            'id': acc_id,
                            'name': acc_name,
                            'type': acc_type,
                            'balance': balance
                        }
            
            # Обновляем фильтр счетов (блокируем сигналы)
            self.account_filter_combo.blockSignals(True)
            self.account_filter_combo.clear()
            self.account_filter_combo.addItem("Все счета")
            self.account_filter_combo.addItems([info['name'] for info in self.accounts_data.values()])
            self.account_filter_combo.blockSignals(False)
            
            # Обновляем комбобокс фильтра категорий (блокируем сигналы)
            self.category_filter_combo.blockSignals(True)
            self._update_category_filter_combo_for_filter(self.current_filters.get("trans_type"))
            self.category_filter_combo.blockSignals(False)
            
            # Обновляем комбобоксы для ввода новых операций
            self._update_category_and_account_combos()
            
            # Показываем информацию о загрузке
            accounts_count = len(self.accounts_data)
            categories_count = self.category_filter_combo.count() - 1  # -1 для "Все категории"
            
            self.show_status_message(f"Загружено: {accounts_count} счетов, {categories_count} категорий", 2000, "success")
            
            # ОБНОВЛЯЕМ ТАБЛИЦУ
            self._update_display()
            
        except Exception as e:
            error_msg = str(e)
            self.show_status_message(f"Ошибка загрузки: {error_msg[:50]}...", 3000, "error")
            print(f"Ошибка загрузки данных: {e}")
        
    def _update_accounts_combo(self):
        """Обновляет комбобокс счетов с группировкой."""
        self.account_combo.clear()
        
        if not self.accounts_data:
            return
        
        # Словарь для перевода типов счетов на русский
        type_translation = {
            'Cash': 'Наличные',
            'Bank Account': 'Банковские счета',
            'Credit Card': 'Кредитные карты',
            'Counterparty': 'Контрагенты',
            'Other': 'Прочие'
        }
        
        # Группируем счета по типам
        accounts_by_type = {}
        for acc_id, info in self.accounts_data.items():
            acc_type = info.get('type', 'Other')
            acc_name = info['name']
            
            if acc_type not in accounts_by_type:
                accounts_by_type[acc_type] = []
            
            # Просто добавляем название счета без баланса
            accounts_by_type[acc_type].append(acc_name)
        
        # Порядок отображения типов
        type_order = ['Cash', 'Bank Account', 'Credit Card', 'Counterparty', 'Other']
        
        for acc_type in type_order:
            if acc_type in accounts_by_type and accounts_by_type[acc_type]:
                # Сортируем счета внутри типа
                accounts_by_type[acc_type].sort()
                
                # Добавляем счета этого типа
                for account_name in accounts_by_type[acc_type]:
                    self.account_combo.addItem(account_name)
        
        # Можно также добавить делегат для стилизации
        self.account_combo.setStyleSheet("""
            QComboBox {
                font-family: 'Segoe UI', Arial;
                font-size: 11px;
            }
        """)

    def keyPressEvent(self, event):
        """Переопределяем обработку клавиши Enter."""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            # Если фокус в поле описания или суммы - добавляем операцию
            if self.description_input.hasFocus() or self.amount_input.hasFocus():
                self._add_transaction()
                return  # Важно: предотвращаем дальнейшую обработку
            elif self.search_input.hasFocus():
                # При нажатии Enter в поиске просто применяем фильтры
                self._apply_filters()
                return
            else:
                # Для остальных случаев вызываем стандартную обработку
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)
            
    # --- Методы фильтрации ---
           
    
            
    def _apply_period_filter(self, index):
        """Применяет фильтр по периоду."""
        try:
            period_text = self.period_combo.currentText()
            
            if period_text == "Выбрать период...":
                # Сбрасываем текущий выбор, чтобы можно было выбрать снова
                self.period_combo.blockSignals(True)
                self.period_combo.setCurrentIndex(0)  # Устанавливаем "За все время"
                self.period_combo.blockSignals(False)
                
                # Открываем диалог выбора периода
                self._open_period_dialog()
                return
            
            date_from, date_to = DateUtils.get_period_dates(period_text)
            
            self.current_filters.update({
                "date_from": date_from.strftime('%Y-%m-%d') if date_from else None,
                "date_to": date_to.strftime('%Y-%m-%d') if date_to else None
            })
            
            self._update_display()
            
        except Exception as e:
            self.show_status_message(f"Ошибка фильтра периода: {str(e)[:50]}", 2000, "error")

    def _open_period_dialog(self):
        """Открывает диалог выбора периода."""
        try:
            dialog = DateRangeDialog(self)
            
            if dialog.exec():
                date_from_qdate, date_to_qdate = dialog.get_dates()
                
                if date_from_qdate and date_to_qdate:
                    date_from_py = date(date_from_qdate.year(), date_from_qdate.month(), date_from_qdate.day())
                    date_to_py = date(date_to_qdate.year(), date_to_qdate.month(), date_to_qdate.day())
                    
                    self.current_filters.update({
                        "date_from": date_from_py.strftime('%Y-%m-%d') if date_from_py else None,
                        "date_to": date_to_py.strftime('%Y-%m-%d') if date_to_py else None
                    })
                    
                    from_str = date_from_py.strftime('%Y-%m-%d')  # ← Формат гггг-мм-дд
                    to_str = date_to_py.strftime('%Y-%m-%d')
                    # Обновляем текст в комбобоксе, чтобы показать выбранный период
                    custom_text = f"{from_str} - {to_str}"
                    self.period_combo.blockSignals(True)
                    # Ищем есть ли уже такой период в списке
                    index = self.period_combo.findText(custom_text)
                    if index == -1:
                        # Добавляем новый элемент и выбираем его
                        self.period_combo.addItem(custom_text)
                        self.period_combo.setCurrentText(custom_text)
                    else:
                        self.period_combo.setCurrentIndex(index)
                    self.period_combo.blockSignals(False)
                    
                    self.show_status_message(f"Период: {from_str} - {to_str}", 2000, "info")
                else:
                    self.current_filters.update({
                        "date_from": None,
                        "date_to": None
                    })
                    self.period_combo.setCurrentText("За все время")
                
                self._update_display()
                
        except Exception as e:
            self.show_status_message(f"Ошибка выбора периода", 2000, "error")
            
    def _reset_all_filters(self):
        """Сбрасывает все фильтры."""
        # Блокируем сигналы, чтобы не вызывать обновления при каждом изменении
        self.type_filter_combo.blockSignals(True)
        self.category_filter_combo.blockSignals(True)
        self.account_filter_combo.blockSignals(True)
        self.period_combo.blockSignals(True)
        self.search_input.blockSignals(True)
        
        self.type_filter_combo.setCurrentIndex(0)
        self.category_filter_combo.setCurrentIndex(0)
        self.account_filter_combo.setCurrentIndex(0)
        self.period_combo.setCurrentIndex(0)
        self.search_input.clear()
        
        # Разблокируем сигналы
        self.type_filter_combo.blockSignals(False)
        self.category_filter_combo.blockSignals(False)
        self.account_filter_combo.blockSignals(False)
        self.period_combo.blockSignals(False)
        self.search_input.blockSignals(False)
        
        # Сбрасываем все фильтры
        self.current_filters = {
            "date_from": None, "date_to": None, "trans_type": None,
            "category_id": None, "account_id": None, "description_text": None
        }
        
        self._update_display()
        self.show_status_message("Все фильтры сброшены", 1000, "info")
        
    # ---филтры из старай версии---
    def _create_filter_menus(self):
        """Создает контекстные меню для заголовков столбцов - только сортировка."""
        # Убираем обработчик клика по заголовку для фильтров
        # Оставляем только стандартную сортировку при нажатии
        header = self.transactions_tree.header()
        header.setSectionsClickable(True)
        # Сортировка включена в настройках виджета
        
    def _on_header_clicked(self, logical_index):
        """Обработчик клика по заголовку колонки."""
        try:
            # Получаем название колонки
            header_item = self.transactions_tree.headerItem()
            if not header_item:
                return
                
            column_name = header_item.text(logical_index)
            
            # Создаем контекстное меню
            menu = QMenu(self)
            
            # Добавляем общий пункт "Все"
            all_action = menu.addAction("Все")
            all_action.triggered.connect(lambda: self._apply_column_filter(column_name, None))
            menu.addSeparator()
            
            # В зависимости от колонки добавляем специфичные пункты
            if column_name == "Тип":
                type_action_income = menu.addAction("Доход")
                type_action_income.triggered.connect(lambda: self._apply_column_filter(column_name, "Доход"))
                
                type_action_expense = menu.addAction("Расход")
                type_action_expense.triggered.connect(lambda: self._apply_column_filter(column_name, "Расход"))
                
            elif column_name == "Категория":
                # Загружаем категории
                try:
                    categories = self.db.get_categories_with_hierarchy() or []
                    
                    # Группируем по уровням
                    main_categories = []
                    sub_categories = {}
                    
                    for cat in categories:
                        if isinstance(cat, tuple):
                            cat_id, name, cat_type, budget, parent_id, level, path = cat
                        elif isinstance(cat, dict):
                            cat_id = cat.get('id')
                            name = cat.get('name', '')
                            level = cat.get('level', 0)
                        else:
                            continue
                        
                        if level == 0:
                            main_categories.append((name, cat_id))
                        else:
                            indent = "    " * level
                            display_name = f"{indent}{name}"
                            menu.addAction(display_name)
                            # Привязываем действие
                            action = menu.actions()[-1]
                            action.triggered.connect(
                                lambda checked=False, n=name: self._apply_column_filter(column_name, n)
                            )
                    
                    # Сначала добавляем основные категории
                    for name, cat_id in main_categories:
                        menu.addAction(name)
                        action = menu.actions()[-1]
                        action.triggered.connect(
                            lambda checked=False, n=name: self._apply_column_filter(column_name, n)
                        )
                    
                except Exception as e:
                    print(f"Ошибка загрузки категорий: {e}")
                    menu.addAction("Ошибка загрузки категорий").setEnabled(False)
                    
            elif column_name == "Счет":
                # Добавляем счета
                for acc_id, info in self.accounts_data.items():
                    menu.addAction(info['name'])
                    action = menu.actions()[-1]
                    action.triggered.connect(
                        lambda checked=False, n=info['name']: self._apply_column_filter(column_name, n)
                    )
                    
            elif column_name == "Дата":
                today = date.today()
                this_month_start = today.replace(day=1)
                this_year_start = today.replace(month=1, day=1)
                
                # Сегодня
                today_action = menu.addAction("Сегодня")
                today_action.triggered.connect(
                    lambda: self._apply_column_filter(column_name, 
                                                     today.strftime('%Y-%m-%d'),
                                                     today.strftime('%Y-%m-%d'))
                )
                
                # Последние 7 дней
                week_ago_action = menu.addAction("Последние 7 дней")
                week_ago_action.triggered.connect(
                    lambda: self._apply_column_filter(column_name,
                                                     (today - timedelta(days=7)).strftime('%Y-%m-%d'),
                                                     today.strftime('%Y-%m-%d'))
                )
                
                # Этот месяц
                month_action = menu.addAction("Этот месяц")
                month_action.triggered.connect(
                    lambda: self._apply_column_filter(column_name,
                                                     this_month_start.strftime('%Y-%m-%d'),
                                                     today.strftime('%Y-%m-%d'))
                )
                
                # Этот год
                year_action = menu.addAction("Этот год")
                year_action.triggered.connect(
                    lambda: self._apply_column_filter(column_name,
                                                     this_year_start.strftime('%Y-%m-%d'),
                                                     today.strftime('%Y-%m-%d'))
                )
                
                menu.addSeparator()
                
                # Выбрать диапазон
                range_action = menu.addAction("Выбрать диапазон...")
                range_action.triggered.connect(self._open_date_range_dialog)
                
            else:
                # Для других колонок (например, Описание) можно сделать текстовый фильтр
                text_action = menu.addAction("Фильтр по тексту...")
                text_action.triggered.connect(lambda: self._show_text_filter_dialog(column_name))
            
            # Показываем меню под заголовком
            header = self.transactions_tree.header()
            header_pos = header.mapToGlobal(header.pos())
            section_pos = header.sectionPosition(logical_index)
            section_width = header.sectionSize(logical_index)
            
            menu_x = header_pos.x() + section_pos
            menu_y = header_pos.y() + header.height()
            
            menu.exec_(self.mapToGlobal(QPoint(menu_x, menu_y)))
            
        except Exception as e:
            print(f"Ошибка показа меню фильтра: {e}")
            
    def _apply_column_filter(self, column_name, value, date_to_value=None):
        """Применяет фильтр для конкретного столбца."""
        try:
            if column_name == "Тип":
                if value == "Доход":
                    self.current_filters["trans_type"] = "income"
                elif value == "Расход":
                    self.current_filters["trans_type"] = "expense"
                else:
                    self.current_filters["trans_type"] = None
                    
            elif column_name == "Категория":
                if value:
                    # Ищем ID категории по имени
                    category_id = None
                    try:
                        categories = self.db.get_categories(include_subcategories=True)
                        for cat in categories:
                            if isinstance(cat, tuple):
                                cat_name = cat[1]
                            elif isinstance(cat, dict):
                                cat_name = cat.get('name', '')
                            else:
                                continue
                                
                            if cat_name == value:
                                if isinstance(cat, tuple):
                                    category_id = cat[0]
                                elif isinstance(cat, dict):
                                    category_id = cat.get('id')
                                break
                    except Exception as e:
                        print(f"Ошибка поиска категории: {e}")
                    
                    self.current_filters["category_id"] = category_id
                else:
                    self.current_filters["category_id"] = None
                    
            elif column_name == "Счет":
                if value:
                    account_id = None
                    for acc_id, info in self.accounts_data.items():
                        if info['name'] == value:
                            account_id = acc_id
                            break
                    self.current_filters["account_id"] = account_id
                else:
                    self.current_filters["account_id"] = None
                    
            elif column_name == "Дата":
                self.current_filters["date_from"] = value
                self.current_filters["date_to"] = date_to_value
                
            self._update_display()
            
            if value:
                self.show_status_message(f"🔍 Фильтр: {column_name} = '{value}'", 2000, "info")
            else:
                self.show_status_message("🔍 Фильтр сброшен", 1500, "info")
                
        except Exception as e:
            print(f"Ошибка применения фильтра: {e}")
            self.show_status_message(f"Ошибка применения фильтра: {str(e)[:50]}", 3000, "error")

    def _open_date_range_dialog(self):
        """Открывает диалог выбора диапазона дат."""
        try:
            dialog = DateRangeDialog(self)
            
            if dialog.exec():
                date_from_qdate, date_to_qdate = dialog.get_dates()
                
                if date_from_qdate and date_to_qdate:
                    date_from = date(date_from_qdate.year(), date_from_qdate.month(), date_from_qdate.day())
                    date_to = date(date_to_qdate.year(), date_to_qdate.month(), date_to_qdate.day())
                    
                    # Применяем фильтр
                    self._apply_column_filter(
                        "Дата", 
                        date_from.strftime('%Y-%m-%d'),
                        date_to.strftime('%Y-%m-%d')
                    )
                    
        except Exception as e:
            self.show_status_message(f"Ошибка выбора диапазона дат: {str(e)[:50]}", 3000, "error")
            print(f"Ошибка открытия диалога диапазона дат: {e}")

    def _show_text_filter_dialog(self, column_name):
        """Показывает диалог текстового фильтра."""
        try:
            text, ok = QInputDialog.getText(
                self, 
                f"Фильтр по {column_name}", 
                f"Введите текст для фильтрации по колонке '{column_name}':",
                QLineEdit.Normal,
                ""
            )
            
            if ok and text:
                # Для колонки "Описание"
                if column_name == "Описание":
                    self.current_filters["description_text"] = text
                    self._update_display()
                    self.show_status_message(f"Фильтр по описанию: '{text}'", 2000, "info")
                    
        except Exception as e:
            print(f"Ошибка текстового фильтра: {e}")
            
    # --- Работа с транзакциями ---
    
    def _add_transaction(self):
        """Добавляет новую транзакцию с поддержкой количества."""
        try:
            date_str = self.date_navigator.get_date_string("yyyy-MM-dd")
            amount_str = self.amount_input.text().strip()
            
            if not amount_str:
                self.show_status_message("Введите сумму", 2000, "warning")
                self.amount_input.setFocus()
                return
            
            # Поддержка формата "90*2" (цена * количество)
            quantity = 1.0
            price_per_unit = None
            
            if '*' in amount_str:
                try:
                    parts = amount_str.split('*')
                    if len(parts) == 2:
                        price_per_unit = float(parts[0].strip().replace(',', '.'))
                        quantity = float(parts[1].strip().replace(',', '.'))
                        total_amount = price_per_unit * quantity
                        
                        if quantity <= 0:
                            self.show_status_message("Количество должно быть положительным", 2000, "error")
                            self.amount_input.selectAll()
                            return
                            
                        # Автоматически добавляем количество в описание
                        if not self.description_input.text().strip():
                            if quantity == int(quantity):
                                qty_display = f"{int(quantity)}"
                            else:
                                qty_display = f"{quantity:.1f}"
                            self.description_input.setText(f"({qty_display} ед.)")
                    else:
                        # Просто умножаем все числа
                        total_amount = 1.0
                        for part in parts:
                            total_amount *= float(part.strip().replace(',', '.'))
                        quantity = float(parts[-1].strip().replace(',', '.')) if len(parts) > 1 else 1.0
                except ValueError:
                    self.show_status_message("Некорректный формат суммы", 2000, "error")
                    self.amount_input.selectAll()
                    return
            else:
                try:
                    total_amount = float(amount_str.replace(',', '.'))
                except ValueError:
                    self.show_status_message("Некорректная сумма", 2000, "error")
                    self.amount_input.selectAll()
                    return
            
            transaction_type_text = self.type_combo.currentText().lower()
            category_display_name = self.category_combo.currentText()
            account_name = self.account_combo.currentText()
            description = self.description_input.text().strip()
            
            if not category_display_name:
                self.show_status_message("Выберите категорию", 2000, "warning")
                return
            
            # Получаем ID категории из словаря ДЛЯ ВВОДА
            category_id = self.input_category_id_by_display_name.get(category_display_name)
            if category_id is None:
                # Пробуем найти в общем словаре на всякий случай
                category_id = self.category_id_by_display_name.get(category_display_name)
                if category_id is None:
                    self.show_status_message(f"Категория не найдена: {category_display_name}", 2000, "error")
                    print(f"Debug: Категория '{category_display_name}' не найдена в словарях")
                    print(f"Debug: input_category_id_by_display_name keys: {list(self.input_category_id_by_display_name.keys())[:5]}")
                    return
            
            account_id = None
            for acc_id, info in self.accounts_data.items():
                if info['name'] == account_name:
                    account_id = acc_id
                    break
            
            if account_id is None:
                self.show_status_message("Счет не найден", 2000, "error")
                return
            
            # Преобразуем тип для БД
            db_type = "income" if transaction_type_text == "доход" else "expense"
            
            # Создаем словарь с данными для нового API
            transaction_data = {
                'date': date_str,
                'amount': total_amount if db_type == 'income' else -abs(total_amount),
                'type': db_type,
                'category_id': category_id,
                'description': description,
                'account_id': account_id,
                'quantity': quantity
            }
            
            if price_per_unit:
                transaction_data['price_per_unit'] = price_per_unit

            # Добавляем транзакцию через новый API
            result = self.db.add_transaction(transaction_data)
            
            if result:
                # Показываем сообщение в статус-баре
                abs_amount = abs(total_amount)
                if transaction_type_text == "расход":
                    if quantity != 1.0:
                        if price_per_unit:
                            msg = f"Расход добавлен: {price_per_unit:.2f} ₽ × {quantity} = {abs_amount:.2f} ₽"
                        else:
                            msg = f"Расход добавлен: {abs_amount:.2f} ₽ ({quantity} ед.)"
                    else:
                        msg = f"Расход добавлен: {abs_amount:.2f} ₽"
                else:
                    if quantity != 1.0:
                        if price_per_unit:
                            msg = f"Доход добавлен: {price_per_unit:.2f} ₽ × {quantity} = {abs_amount:.2f} ₽"
                        else:
                            msg = f"Доход добавлен: {abs_amount:.2f} ₽ ({quantity} ед.)"
                    else:
                        msg = f"Доход добавлен: {abs_amount:.2f} ₽"
                
                self.show_status_message(f"✅ {msg}", 2000, "success")
                
                # Очищаем поля ввода, но НЕ сбрасываем фильтры
                self._clear_input_fields()
                
                # Обновляем ТОЛЬКО транзакции, не перезагружая все данные
                self._update_display()
                
                # Возвращаем фокус
                self.amount_input.setFocus()
                self.amount_input.selectAll()
                
                # Сигнал об обновлении (если родитель поддерживает)
                if hasattr(self.parent, 'data_updated'):
                    self.parent.data_updated.emit()
                    
            else:
                self.show_status_message("Ошибка добавления транзакции", 3000, "error")
                
        except Exception as e:
            self.show_status_message(f"Ошибка: {str(e)[:50]}", 3000, "error")
            print(f"Ошибка добавления транзакции: {e}")
            import traceback
            traceback.print_exc()
     
    def _create_refund(self):
        """Создает возврат для выбранной транзакции с выбором даты"""
        selected_items = self.transactions_tree.selectedItems()
        if not selected_items:
            self.show_status_message("Выберите транзакцию для возврата", 2000, "warning")
            return
        
        # Берем первую выбранную транзакцию
        item = selected_items[0]
        transaction_id = item.data(0, Qt.UserRole)
        
        if not transaction_id:
            self.show_status_message("Ошибка: не найден ID транзакции", 2000, "error")
            return
        
        try:
            # Получаем данные транзакции
            transaction = self.db.get_transaction_by_id(transaction_id)
            if not transaction:
                self.show_status_message("Транзакция не найдена в БД", 2000, "error")
                return
            
            # Проверяем, можно ли сделать возврат
            transaction_type = transaction.get('type')
            
            # Можно делать возврат только для доходов и расходов
            if transaction_type not in ['income', 'expense']:
                self.show_status_message(f"Нельзя сделать возврат для типа: {transaction_type}", 3000, "error")
                return
            
            # Проверяем, не является ли уже возвратом
            if transaction_type == 'refund':
                self.show_status_message("Нельзя сделать возврат для возврата", 2000, "error")
                return
            
            # Проверяем, нет ли уже возвратов для этой транзакции
            existing_refunds = self.db.get_refunds_for_transaction(transaction_id)
            if existing_refunds:
                total_refunded = sum(abs(float(refund.get('amount', 0))) for refund in existing_refunds)
                original_amount = abs(float(transaction.get('amount', 0)))
                
                if total_refunded >= original_amount:
                    self.show_status_message("Полный возврат уже сделан", 2000, "warning")
                    return
            
            # Создаем диалог для выбора даты возврата
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDateEdit, QPushButton, QMessageBox
            from PySide6.QtCore import QDate
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Выбор даты возврата")
            dialog.resize(300, 150)
            
            layout = QVBoxLayout(dialog)
            
            # Информация о транзакции
            transaction_date = transaction.get('date', '')
            transaction_amount = abs(float(transaction.get('amount', 0)))
            transaction_desc = transaction.get('description', '')[:50]
            
            info_label = QLabel(f"Оригинальная транзакция:\n"
                              f"Дата: {transaction_date}\n"
                              f"Сумма: {transaction_amount:.2f} ₽\n"
                              f"Описание: {transaction_desc}...")
            layout.addWidget(info_label)
            
            # Выбор даты
            layout.addWidget(QLabel("Дата возврата:"))
            date_edit = QDateEdit()
            date_edit.setCalendarPopup(True)
            date_edit.setDate(QDate.currentDate())  # По умолчанию сегодня
            date_edit.setDisplayFormat("yyyy-MM-dd")
            layout.addWidget(date_edit)
            
            # Кнопки
            button_layout = QHBoxLayout()
            ok_button = QPushButton("Создать возврат")
            cancel_button = QPushButton("Отмена")
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)
            
            # Подключение кнопок
            ok_button.clicked.connect(dialog.accept)
            cancel_button.clicked.connect(dialog.reject)
            
            # Показываем диалог
            if dialog.exec():
                # Получаем выбранную дату
                selected_date = date_edit.date().toString("yyyy-MM-dd")
                
                # Определяем тип операции
                if transaction_type == 'expense':
                    op_type = "покупки"
                    refund_amount = transaction_amount  # Положительная сумма для возврата расхода
                else:  # income
                    op_type = "дохода"
                    refund_amount = -transaction_amount  # Отрицательная сумма для возврата дохода
                
                # Подтверждение
                reply = QMessageBox.question(
                    self,
                    "Подтверждение возврата",
                    f"Создать возврат {op_type}?\n\n"
                    f"Оригинальная дата: {transaction_date}\n"
                    f"Дата возврата: {selected_date}\n"
                    f"Сумма: {transaction_amount:.2f} ₽\n"
                    f"Описание: {transaction_desc}...",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.No:
                    return
                
                # Создаем возврат с выбранной датой
                refund_id = self.db.add_refund(
                    original_transaction_id=transaction_id,
                    date=selected_date,
                    description=f"Возврат: {transaction_desc}" if transaction_desc else f"Возврат транзакции #{transaction_id}"
                )
                
                if refund_id:
                    # Показываем успешное сообщение
                    if transaction_type == 'expense':
                        self.show_status_message(f"✅ Возврат покупки на {transaction_amount:.2f} ₽ создан ({selected_date})", 3000, "success")
                    else:
                        self.show_status_message(f"✅ Возврат дохода на {transaction_amount:.2f} ₽ создан ({selected_date})", 3000, "success")
                    
                    # Обновляем отображение
                    self._update_display()
                    
                    # Обновляем родительское окно если нужно
                    if hasattr(self.parent, 'data_updated'):
                        self.parent.data_updated.emit()
                        
                else:
                    self.show_status_message("Ошибка создания возврата", 3000, "error")
                    
        except Exception as e:
            error_msg = str(e)[:100]
            self.show_status_message(f"Ошибка: {error_msg}...", 3000, "error")
            print(f"Ошибка создания возврата: {e}")
            import traceback
            traceback.print_exc()
       
    def _create_refund_with_options(self):
        """Создает возврат для выбранной транзакции с выбором даты и суммы"""
        selected_items = self.transactions_tree.selectedItems()
        if not selected_items:
            self.show_status_message("Выберите транзакцию для возврата", 2000, "warning")
            return
        
        # Берем первую выбранную транзакцию
        item = selected_items[0]
        transaction_id = item.data(0, Qt.UserRole)
        
        if not transaction_id:
            self.show_status_message("Ошибка: не найден ID транзакции", 2000, "error")
            return
        
        try:
            # Получаем данные транзакции
            transaction = self.db.get_transaction_by_id(transaction_id)
            if not transaction:
                self.show_status_message("Транзакция не найдена в БД", 2000, "error")
                return
            
            # Проверяем, можно ли сделать возврат
            transaction_type = transaction.get('type')
            
            if transaction_type not in ['income', 'expense']:
                self.show_status_message(f"Нельзя сделать возврат для типа: {transaction_type}", 3000, "error")
                return
            
            if transaction_type == 'refund':
                self.show_status_message("Нельзя сделать возврат для возврата", 2000, "error")
                return
            
            # Проверяем существующие возвраты
            existing_refunds = self.db.get_refunds_for_transaction(transaction_id)
            total_refunded = 0
            if existing_refunds:
                total_refunded = sum(abs(float(refund.get('amount', 0))) for refund in existing_refunds)
            
            original_amount = abs(float(transaction.get('amount', 0)))
            max_refundable = original_amount - total_refunded
            
            if max_refundable <= 0:
                self.show_status_message("Полный возврат уже сделан", 2000, "warning")
                return
            
            # Создаем диалог с настройками возврата
            from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                         QDateEdit, QPushButton, QMessageBox, QLineEdit,
                                         QDoubleSpinBox, QFormLayout, QGroupBox)
            from PySide6.QtCore import QDate
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Настройки возврата")
            dialog.resize(350, 250)
            
            layout = QVBoxLayout(dialog)
            
            # Информация о транзакции
            info_group = QGroupBox("Оригинальная транзакция")
            info_layout = QFormLayout()
            
            transaction_date = transaction.get('date', '')
            transaction_amount = abs(float(transaction.get('amount', 0)))
            transaction_desc = transaction.get('description', '')[:50]
            
            info_layout.addRow("Дата:", QLabel(transaction_date))
            info_layout.addRow("Сумма:", QLabel(f"{transaction_amount:.2f} ₽"))
            info_layout.addRow("Остаток для возврата:", QLabel(f"{max_refundable:.2f} ₽"))
            if transaction_desc:
                info_layout.addRow("Описание:", QLabel(transaction_desc))
            
            info_group.setLayout(info_layout)
            layout.addWidget(info_group)
            
            # Настройки возврата
            settings_group = QGroupBox("Настройки возврата")
            settings_layout = QFormLayout()
            
            # Дата возврата
            date_edit = QDateEdit()
            date_edit.setCalendarPopup(True)
            date_edit.setDate(QDate.currentDate())
            date_edit.setDisplayFormat("yyyy-MM-dd")
            settings_layout.addRow("Дата возврата:", date_edit)
            
            # Сумма возврата
            amount_spin = QDoubleSpinBox()
            amount_spin.setRange(0.01, max_refundable)
            amount_spin.setValue(max_refundable)
            amount_spin.setDecimals(2)
            amount_spin.setSuffix(" ₽")
            amount_spin.setSingleStep(10.0)
            settings_layout.addRow("Сумма возврата:", amount_spin)
            
            # Описание
            description_edit = QLineEdit()
            default_description = f"Возврат: {transaction_desc}" if transaction_desc else f"Возврат транзакции #{transaction_id}"
            description_edit.setText(default_description)
            settings_layout.addRow("Описание:", description_edit)
            
            settings_group.setLayout(settings_layout)
            layout.addWidget(settings_group)
            
            # Кнопки
            button_layout = QHBoxLayout()
            ok_button = QPushButton("Создать возврат")
            cancel_button = QPushButton("Отмена")
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)
            
            # Подключение кнопок
            ok_button.clicked.connect(dialog.accept)
            cancel_button.clicked.connect(dialog.reject)
            
            # Показываем диалог
            if dialog.exec():
                # Получаем параметры
                selected_date = date_edit.date().toString("yyyy-MM-dd")
                refund_amount = amount_spin.value()
                description = description_edit.text().strip()
                
                # Определяем знак суммы в зависимости от типа
                if transaction_type == 'expense':
                    # Для расхода возврат положительный
                    signed_amount = refund_amount
                else:  # income
                    # Для дохода возврат отрицательный
                    signed_amount = -refund_amount
                
                # Создаем возврат
                refund_data = {
                    'date': selected_date,
                    'amount': signed_amount,
                    'type': 'refund',
                    'original_transaction_id': transaction_id,
                    'category_id': transaction.get('category_id'),
                    'account_id': transaction.get('account_id'),
                    'description': description
                }
                
                # Используем прямой метод для добавления
                refund_id = self.db.add_transaction(refund_data)
                
                if refund_id:
                    self.show_status_message(f"✅ Возврат на {refund_amount:.2f} ₽ создан ({selected_date})", 3000, "success")
                    self._update_display()
                    
                    if hasattr(self.parent, 'data_updated'):
                        self.parent.data_updated.emit()
                        
                else:
                    self.show_status_message("Ошибка создания возврата", 3000, "error")
                    
        except Exception as e:
            error_msg = str(e)[:100]
            self.show_status_message(f"Ошибка: {error_msg}...", 3000, "error")
            print(f"Ошибка создания возврата: {e}")
            import traceback
            traceback.print_exc()
       
    def eventFilter(self, obj, event):
        """Обработчик событий для удаления по клавише Delete."""
        if obj == self.transactions_tree and event.type() == QKeyEvent.Type.KeyPress:
            if event.key() == Qt.Key_Delete:
                self._delete_selected_transactions()
                return True
        return super().eventFilter(obj, event)
        
    def _setup_keyboard_shortcuts(self):
        """Настройка горячих клавиш."""
        # Устанавливаем обработчик событий для дерева транзакций
        self.transactions_tree.installEventFilter(self)
    
    def _clear_input_fields(self):
        """Очищает поля ввода."""
        self.amount_input.clear()
        self.description_input.clear()
    
    def _update_display(self):
        """Обновляет отображение транзакций."""
        print(f"DEBUG: Обновление дисплея с фильтрами: {self.current_filters}")

        self._update_transactions_tree()
    
    def _update_transactions_tree(self):
        """Обновляет таблицу транзакций с текущими фильтрами."""
        try:
            self.transactions_tree.clear()
            
            # Подготавливаем фильтры для нового API
            filters = {}
            
            # Фильтр по дате
            if self.current_filters.get("date_from"):
                filters["date_from"] = self.current_filters["date_from"]
            if self.current_filters.get("date_to"):
                filters["date_to"] = self.current_filters["date_to"]
            
            # Фильтр по типу (преобразуем в формат БД)
            trans_type = self.current_filters.get("trans_type")
            if trans_type:
                filters["type"] = trans_type  # Прямое использование, т.к. уже в формате БД
            
            # Фильтр по категории
            if self.current_filters.get("category_id"):
                filters["category_id"] = self.current_filters["category_id"]
            
            # Фильтр по счету
            if self.current_filters.get("account_id"):
                filters["account_id"] = self.current_filters["account_id"]
            
            # Исключаем корректировки из списка
            filters["exclude_corrections"] = True
            
            print(f"DEBUG: Фильтры для SQL запроса: {filters}")
            
            # Получаем транзакции через новый API
            transactions = self.db.get_transactions(filters=filters, limit=500) or []
            
            print(f"DEBUG: Получено транзакций: {len(transactions)}")
            
            transaction_count = len(transactions)
            income_total = 0
            expense_total = 0
            refund_total = 0
            
            # Получаем текст для поиска (без учета регистра)
            search_text = self.current_filters.get("description_text")
            
            # Создаем словарь для быстрого доступа к категориям
            category_cache = {}
            try:
                all_categories = self.db.get_categories()
                for cat in all_categories:
                    category_cache[cat['id']] = cat['name']
            except:
                pass
            
            # Создаем словарь для быстрого доступа к счетам
            account_cache = {}
            for acc_id, info in self.accounts_data.items():
                account_cache[acc_id] = info['name']
            
            # Обрабатываем транзакции
            displayed_count = 0
            for t in transactions:
                if not isinstance(t, dict):
                    continue
                
                try:
                    # Получаем значения из словаря
                    t_id = t.get('id')
                    date_str = t.get('date', '')
                    amount = float(t.get('amount', 0))
                    t_type = t.get('type', '').lower()
                    
                    # Получаем имя категории через кэш
                    category_id = t.get('category_id')
                    category_name = category_cache.get(category_id, t.get('category_name', ''))
                    
                    description = t.get('description', '')
                    
                    # Получаем имя счета через кэш
                    account_id = t.get('account_id')
                    account_name = account_cache.get(account_id, t.get('account_name', ''))
                    
                    quantity = float(t.get('quantity', 1.0))
                    original_transaction_id = t.get('original_transaction_id')
                    price_per_unit = float(t.get('price_per_unit', 0)) if t.get('price_per_unit') else None
                    
                    # Применяем фильтр по описанию (если есть)
                    if search_text and search_text.lower() not in description.lower():
                        continue
                    
                    # Форматируем данные для отображения с учетом возвратов
                    item = None
                    
                    if t_type == 'income':
                        type_display = "Доход"
                        amount_display = f"{abs(amount):,.2f} ₽"
                        income_total += amount
                        color = QColor("#2e7d32")  # Зеленый
                        
                    elif t_type == 'expense':
                        type_display = "Расход"
                        amount_display = f"-{abs(amount):,.2f} ₽"
                        expense_total += abs(amount)
                        color = QColor("#d32f2f")  # Красный
                        
                    elif t_type == 'refund':
                        # ВОЗВРАТЫ - особый стиль
                        type_display = "Возврат"
                        
                        # Добавляем ссылку на оригинальную транзакцию в описание
                        if original_transaction_id:
                            description = f"[К #{original_transaction_id}] {description}"
                        
                        # Для возвратов знак зависит от типа оригинальной транзакции
                        # Но в БД возврат уже имеет правильный знак
                        amount_display = f"{amount:+,.2f} ₽"
                        
                        # Цвет для возврата
                        if amount > 0:
                            color = QColor("#2e7d32")  # Зеленый
                        else:
                            color = QColor("#d32f2f")  # Красный
                        
                        refund_total += amount
                        
                    else:
                        type_display = t_type.capitalize()
                        amount_display = f"{amount:,.2f} ₽"
                        color = QColor("#757575")  # Серый
                    
                    # Форматируем дату для отображения в формате гггг-мм-дд
                    try:
                        if '-' in date_str:
                            date_display = date_str
                        else:
                            dt = datetime.strptime(date_str, '%Y-%m-%d')
                            date_display = dt.strftime('%Y-%m-%d')
                    except:
                        date_display = date_str
                    
                    # Форматируем количество
                    if quantity != 1.0:
                        if quantity == int(quantity):
                            qty_display = f"{int(quantity)}"
                        else:
                            qty_display = f"{quantity:.1f}"
                        
                        # Показываем детали если есть цена за единицу
                        if price_per_unit:
                            amount_display = f"{abs(amount):,.2f} ₽"
                            qty_display = f"{quantity} × {price_per_unit:.2f} ₽"
                    else:
                        qty_display = "1"
                    
                    # Создаем элемент
                    item = QTreeWidgetItem([
                        date_display,
                        type_display,
                        amount_display,
                        qty_display,
                        str(category_name) if category_name else "-",
                        str(account_name) if account_name else "-",
                        str(description) if description else "-"
                    ])
                    
                    # Цвет суммы
                    if item:
                        item.setForeground(2, color)
                        
                        # Для возвратов делаем фон светлее
                        if t_type == 'refund':
                            item.setBackground(0, QColor("#f3e5f5"))  # Светло-фиолетовый
                            item.setBackground(1, QColor("#f3e5f5"))
                            item.setBackground(2, QColor("#f3e5f5"))
                            item.setFont(1, QFont("Segoe UI", 10, QFont.Bold))
                        
                        # Сохраняем дополнительные данные
                        item.setData(0, Qt.UserRole, t_id)
                        item.setData(3, Qt.UserRole, quantity)
                        
                        # Для возвратов сохраняем оригинальную транзакцию
                        if t_type == 'refund':
                            item.setData(0, Qt.UserRole + 1, original_transaction_id)
                        
                        self.transactions_tree.addTopLevelItem(item)
                        displayed_count += 1
                    
                except Exception as e:
                    print(f"Ошибка обработки транзакции {t.get('id', 'unknown')}: {e}")
                    continue
            
            print(f"DEBUG: Отображено транзакций: {displayed_count}")
            
            # Обновляем итоги
            filtered_count = self.transactions_tree.topLevelItemCount()
            summary_text = f"Операций: {filtered_count}"
            if filtered_count > 0:
                summary_text += f" | Доходы: {income_total:,.2f} ₽ | Расходы: {expense_total:,.2f} ₽"
                if refund_total != 0:
                    summary_text += f" | Возвраты: {refund_total:+,.2f} ₽"
                if transaction_count > filtered_count:
                    summary_text += f" (отфильтровано из {transaction_count})"
            
            self.summary_label.setText(summary_text)
            
            # Сортировка по дате (новые сверху)
            self.transactions_tree.sortItems(0, Qt.DescendingOrder)
            
        except Exception as e:
            print(f"Ошибка обновления таблицы: {e}")
            import traceback
            traceback.print_exc()
            self.summary_label.setText("Ошибка загрузки данных")
            self.show_status_message(f"Ошибка обновления: {str(e)[:50]}", 3000, "error")
        
    def _debug_transaction_data(self, transactions):
        """Отладочный метод для проверки данных транзакций."""
        print("=== ОТЛАДКА ДАННЫХ ТРАНЗАКЦИЙ ===")
        print(f"Всего транзакций: {len(transactions)}")
        
        if transactions:
            print("\nПервые 3 транзакции:")
            for i, t in enumerate(transactions[:3]):
                print(f"\nТранзакция {i+1}:")
                if isinstance(t, dict):
                    for key, value in t.items():
                        print(f"  {key}: {value}")
                else:
                    print(f"  Тип: {type(t)}")
                    print(f"  Данные: {t}")
        
        print("=== КОНЕЦ ОТЛАДКИ ===")
    # --- Контекстное меню ---
    
    def _show_transactions_context_menu(self, position):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 3px;
                padding: 3px;
                font-size: 11px;
            }
            QMenu::item {
                padding: 4px 20px 4px 8px;
                border-radius: 2px;
            }
            QMenu::item:selected {
                background-color: #e3f2fd;
            }
        """)
        
        selected_items = self.transactions_tree.selectedItems()
        
        if not selected_items:
            return
        
        # Получаем transaction_id из первого выбранного элемента
        item = selected_items[0]
        transaction_id = item.data(0, Qt.UserRole)
        
        # Проверяем тип транзакции через БД
        if transaction_id:
            try:
                transaction = self.db.get_transaction_by_id(transaction_id)
                if transaction:
                    transaction_type = transaction.get('type')
                    
                    # Показываем "Создать возврат" только для income/expense
                    if transaction_type in ['income', 'expense']:
                        # Проверяем, нет ли уже возвратов
                        existing_refunds = self.db.get_refunds_for_transaction(transaction_id)
                        
                        # Считаем общую сумму возвратов
                        total_refunded = 0
                        if existing_refunds:
                            total_refunded = sum(abs(float(ref.get('amount', 0))) for ref in existing_refunds)
                        
                        original_amount = abs(float(transaction.get('amount', 0)))
                        
                        # Проверяем, можно ли еще сделать возврат
                        if total_refunded < original_amount:
                            refund_action = menu.addAction("↪️ Создать возврат")
                            refund_action.triggered.connect(self._create_refund_with_options)
                            menu.addSeparator()
                            
                            # Если есть частичные возвраты, покажем их количество
                            if existing_refunds:
                                refund_action.setText(f"↪️ Создать возврат ({len(existing_refunds)} уже есть)")
            except Exception as e:
                print(f"Ошибка проверки возможности возврата: {e}")
        
        # Существующие действия
        edit_action = menu.addAction("✏️ Редактировать")
        edit_action.triggered.connect(self._edit_transaction)
        
        # Дублирование
        duplicate_simple_action = menu.addAction("🔁 Дублировать (просто)")
        duplicate_simple_action.triggered.connect(self._duplicate_transaction)
        
        duplicate_advanced_action = menu.addAction("🔁 Дублировать (с настройками)")
        duplicate_advanced_action.triggered.connect(self._duplicate_transaction_with_options)
        
        # Показывать детали если есть количество
        details_action = menu.addAction("📊 Показать детали")
        details_action.triggered.connect(self._show_quantity_details)
        menu.addSeparator()
        
        delete_action = menu.addAction("🗑️ Удалить")
        delete_action.triggered.connect(self._delete_selected_transactions)
        
        menu.exec_(self.transactions_tree.viewport().mapToGlobal(position))


    def _can_create_refund_for_item(self, item):
        """Проверяет, можно ли создать возврат для выбранной транзакции"""
        try:
            transaction_id = item.data(0, Qt.UserRole)
            if not transaction_id:
                return False
            
            transaction = self.db.get_transaction_by_id(transaction_id)
            if not transaction:
                return False
            
            transaction_type = transaction.get('type')
            
            # Только для доходов и расходов
            if transaction_type not in ['income', 'expense']:
                return False
            
            # Проверяем, нет ли уже возвратов
            existing_refunds = self.db.get_refunds_for_transaction(transaction_id)
            if existing_refunds:
                total_refunded = sum(abs(ref['amount']) for ref in existing_refunds)
                original_amount = abs(transaction['amount'])
                
                # Если уже есть полный возврат
                if total_refunded >= original_amount:
                    return False
            
            return True
            
        except:
            return False
            
    
    def _show_quantity_details(self):
        """Показывает детали операции с количеством."""
        selected_items = self.transactions_tree.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        quantity = item.data(3, Qt.UserRole)
        price_per_unit = item.data(3, Qt.UserRole + 1)
        total_amount = item.text(2).replace('₽', '').replace(',', '').strip()
        
        try:
            total = float(total_amount)
            details = f"Детали:\n\n"
            
            if price_per_unit:
                details += f"Цена за единицу: {price_per_unit:.2f} ₽\n"
                details += f"Количество: {quantity}\n"
                details += f"Итого: {total:.2f} ₽\n"
                details += f"({price_per_unit:.2f} ₽ × {quantity} = {total:.2f} ₽)"
            else:
                details += f"Количество: {quantity}\n"
                details += f"Сумма за единицу: {total/quantity:.2f} ₽\n"
                details += f"Итого: {total:.2f} ₽"
            
            QMessageBox.information(self, "Детали операции", details)
        except:
            pass
            
    def _edit_transaction(self):
        """Редактирует транзакцию."""
        selected_items = self.transactions_tree.selectedItems()
        if not selected_items:
            self.show_status_message("Выберите операцию для редактирования", 2000, "warning")
            return
        
        transaction_id = selected_items[0].data(0, Qt.UserRole)
        
        # Получаем данные транзакции (уже в формате словаря)
        transaction_data = self.db.get_transaction_by_id(transaction_id)
        
        if transaction_data:
            try:
                # Убедимся, что transaction_id присутствует в данных
                if 'id' not in transaction_data:
                    transaction_data['id'] = transaction_id
                
                # Создаем диалог редактирования с передачей словаря
                dialog = EditTransactionDialog(self, self.db, transaction_data)
                
                if dialog.exec():
                    self.show_status_message("Операция обновлена", 1500, "success")
                    self._update_display()
                    
                    if hasattr(self.parent, 'data_updated'):
                        self.parent.data_updated.emit()
                        
            except Exception as e:
                print(f"DEBUG: Error in _edit_transaction: {e}")
                self.show_status_message(f"Ошибка редактирования: {str(e)[:50]}", 3000, "error")
        else:
            self.show_status_message("Операция не найдена", 2000, "error")
        
    def _delete_selected_transactions(self):
        """Удаляет выбранные транзакции."""
        selected_items = self.transactions_tree.selectedItems()
        if not selected_items:
            self.show_status_message("Выберите операции для удаления", 2000, "warning")
            return
        
        count = len(selected_items)
        
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить {count} операций?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return
        
        success_count = 0
        
        for item in selected_items:
            transaction_id = item.data(0, Qt.UserRole)
            try:
                if self.db.delete_transaction(transaction_id):
                    success_count += 1
            except Exception as e:
                print(f"Ошибка удаления транзакции {transaction_id}: {e}")
        
        if success_count > 0:
            self.show_status_message(f"✅ Удалено: {success_count} операций", 2000, "success")
            self._update_display()
            
            if hasattr(self.parent, 'data_updated'):
                self.parent.data_updated.emit()
        else:
            self.show_status_message("Не удалось удалить операции", 3000, "error")
        

    def _duplicate_transaction(self):
        """Дублирует транзакцию через создание новой записи."""
        selected_items = self.transactions_tree.selectedItems()
        if not selected_items:
            self.show_status_message("Выберите операцию для дублирования", 2000, "warning")
            return
        
        transaction_id = selected_items[0].data(0, Qt.UserRole)
        
        if not transaction_id:
            self.show_status_message("Ошибка: не найден ID транзакции", 2000, "error")
            return
        
        try:
            # Получаем данные транзакции
            transaction = self.db.get_transaction_by_id(transaction_id)
            
            if not transaction:
                self.show_status_message("Операция не найдена", 2000, "error")
                return
            
            # Проверяем, что транзакция не является возвратом или корректировкой
            if transaction.get('type') not in ['income', 'expense']:
                self.show_status_message("Можно дублировать только доходы и расходы", 2000, "warning")
                return
            
            # Подтверждение дублирования
            reply = QMessageBox.question(
                self, "Подтверждение",
                f"Создать копию транзакции?\n\n"
                f"Дата: {transaction.get('date', '')}\n"
                f"Сумма: {abs(transaction.get('amount', 0)):.2f} ₽\n"
                f"Описание: {transaction.get('description', '')[:50]}...",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
            
            # Создаем копию транзакции
            today = datetime.now().strftime('%Y-%m-%d')
            
            transaction_data = {
                'date': today,  # Новая дата - сегодня
                'amount': transaction['amount'],  # Сохраняем ту же сумму
                'type': transaction['type'],  # Сохраняем тип
                'category_id': transaction.get('category_id'),  # Сохраняем категорию
                'description': f"{transaction.get('description')}",  # Добавляем пометку
                'account_id': transaction['account_id'],  # Сохраняем счет
                'quantity': transaction.get('quantity', 1.0),  # Сохраняем количество
            }
            
            # Добавляем новую транзакцию
            new_id = self.db.add_transaction(transaction_data)
            
            if new_id:
                self.show_status_message(f"✅ Транзакция скопирована (ID: {new_id})", 2000, "success")
                
                # Обновляем отображение
                self._update_display()
                
                # Обновляем родительское окно если нужно
                if hasattr(self.parent, 'data_updated'):
                    self.parent.data_updated.emit()
                    
                # Очищаем поля ввода и устанавливаем значения для быстрой правки
                try:
                    self.date_navigator.set_date_string(today, "yyyy-MM-dd")
                    amount_value = abs(transaction['amount'])
                    self.amount_input.setText(f"{amount_value:.2f}")
                    
                    # Устанавливаем тип
                    if transaction['type'] == 'income':
                        self.type_combo.setCurrentText("Доход")
                    else:
                        self.type_combo.setCurrentText("Расход")
                    
                    # Устанавливаем описание (убираем "(копия)" для удобства редактирования)
                    description = transaction.get('description', '').replace(' (копия)', '')
                    self.description_input.setText(description)
                    self.description_input.selectAll()
                    
                    # Устанавливаем фокус
                    self.description_input.setFocus()
                    
                except Exception as e:
                    print(f"Ошибка заполнения полей: {e}")
                    self._clear_input_fields()
                    self.amount_input.setFocus()
                    
            else:
                self.show_status_message("Ошибка копирования транзакции", 3000, "error")
                
        except Exception as e:
            error_msg = str(e)[:100]
            self.show_status_message(f"Ошибка копирования: {error_msg}...", 3000, "error")
            print(f"Ошибка дублирования транзакции: {e}")
            import traceback
            traceback.print_exc()
        

    def _duplicate_transaction_with_options(self):
        """Дублирует транзакцию с настройками."""
        selected_items = self.transactions_tree.selectedItems()
        if not selected_items:
            self.show_status_message("Выберите операцию для дублирования", 2000, "warning")
            return
        
        transaction_id = selected_items[0].data(0, Qt.UserRole)
        
        if not transaction_id:
            self.show_status_message("Ошибка: не найден ID транзакции", 2000, "error")
            return
        
        try:
            from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                         QDateEdit, QPushButton, QMessageBox, QLineEdit,
                                         QDoubleSpinBox, QFormLayout, QGroupBox, QCheckBox)
            from PySide6.QtCore import QDate
            
            # Получаем данные транзакции
            transaction = self.db.get_transaction_by_id(transaction_id)
            
            if not transaction:
                self.show_status_message("Операция не найдена", 2000, "error")
                return
            
            if transaction.get('type') not in ['income', 'expense']:
                self.show_status_message("Можно дублировать только доходы и расходы", 2000, "warning")
                return
            
            # Создаем диалог с настройками дублирования
            dialog = QDialog(self)
            dialog.setWindowTitle("Настройки дублирования")
            dialog.resize(350, 320)
            
            layout = QVBoxLayout(dialog)
            
            # Информация о оригинальной транзакции
            info_group = QGroupBox("Оригинальная транзакция")
            info_layout = QFormLayout()
            
            original_date = transaction.get('date', '')
            original_amount = abs(float(transaction.get('amount', 0)))
            original_desc = transaction.get('description', '')[:50]
            
            info_layout.addRow("Дата:", QLabel(original_date))
            info_layout.addRow("Сумма:", QLabel(f"{original_amount:.2f} ₽"))
            info_layout.addRow("Тип:", QLabel("Доход" if transaction.get('type') == 'income' else "Расход"))
            if original_desc:
                info_layout.addRow("Описание:", QLabel(original_desc))
            
            info_group.setLayout(info_layout)
            layout.addWidget(info_group)
            
            # Настройки копии
            settings_group = QGroupBox("Настройки копии")
            settings_layout = QFormLayout()
            
            # Дата копии - ПО УМОЛЧАНИЮ ТА ЖЕ САМАЯ
            date_edit = QDateEdit()
            date_edit.setCalendarPopup(True)
            
            # Устанавливаем дату оригинала по умолчанию
            if original_date:
                try:
                    # Парсим дату из формата "2023-12-20"
                    year, month, day = map(int, original_date.split('-'))
                    qdate = QDate(year, month, day)
                    if qdate.isValid():
                        date_edit.setDate(qdate)
                    else:
                        date_edit.setDate(QDate.currentDate())
                except:
                    date_edit.setDate(QDate.currentDate())
            else:
                date_edit.setDate(QDate.currentDate())
                
            date_edit.setDisplayFormat("yyyy-MM-dd")
            settings_layout.addRow("Новая дата:", date_edit)
            
            # Сумма (с возможностью изменения)
            amount_spin = QDoubleSpinBox()
            amount_spin.setRange(0.01, 1000000)
            amount_spin.setValue(original_amount)
            amount_spin.setDecimals(2)
            amount_spin.setSuffix(" ₽")
            amount_spin.setSingleStep(10.0)
            settings_layout.addRow("Новая сумма:", amount_spin)
            
            # Описание
            description_edit = QLineEdit()
            description_edit.setText(f"{original_desc}")
            settings_layout.addRow("Описание:", description_edit)
            
            # Чекбокс для количества
            copy_quantity_cb = QCheckBox("Копировать количество")
            copy_quantity_cb.setChecked(True)
            settings_layout.addRow("", copy_quantity_cb)
            
            settings_group.setLayout(settings_layout)
            layout.addWidget(settings_group)
            
            # Кнопки
            button_layout = QHBoxLayout()
            ok_button = QPushButton("Создать копию")
            cancel_button = QPushButton("Отмена")
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)
            
            # Подключение кнопок
            ok_button.clicked.connect(dialog.accept)
            cancel_button.clicked.connect(dialog.reject)
            
            # Показываем диалог
            if dialog.exec():
                # Получаем параметры
                new_date = date_edit.date().toString("yyyy-MM-dd")
                new_amount = amount_spin.value()
                description = description_edit.text().strip()
                
                # Применяем знак в зависимости от типа
                if transaction.get('type') == 'income':
                    signed_amount = new_amount
                else:
                    signed_amount = -new_amount
                
                # Подготавливаем данные
                transaction_data = {
                    'date': new_date,
                    'amount': signed_amount,
                    'type': transaction['type'],
                    'category_id': transaction.get('category_id'),
                    'description': description,
                    'account_id': transaction['account_id'],
                }
                
                # Копируем количество если нужно
                if copy_quantity_cb.isChecked():
                    transaction_data['quantity'] = transaction.get('quantity', 1.0)
                
                # Создаем копию
                new_id = self.db.add_transaction(transaction_data)
                
                if new_id:
                    self.show_status_message(f"✅ Копия создана (ID: {new_id})", 2000, "success")
                    self._update_display()
                    
                    if hasattr(self.parent, 'data_updated'):
                        self.parent.data_updated.emit()
                        
                else:
                    self.show_status_message("Ошибка создания копии", 3000, "error")
                    
        except Exception as e:
            error_msg = str(e)[:100]
            self.show_status_message(f"Ошибка: {error_msg}...", 3000, "error")
            print(f"Ошибка дублирования с настройками: {e}")
            import traceback
            traceback.print_exc()
            
        
    
        # --- Открытие других диалогов (ИСПРАВЛЕННЫЕ МЕТОДЫ) ---
    
    def _open_account_management(self):
        """Открывает управление счетами."""
        try:
            dialog = AccountManagementDialog(self, self.db)
            dialog.data_updated.connect(self._on_child_data_updated)
            dialog.show()
            self.open_windows['accounts'] = dialog
            self.show_status_message("Управление счетами открыто", 1500, "info")
            
        except Exception as e:
            self.show_status_message(f"Ошибка открытия счетов: {str(e)[:50]}", 3000, "error")
            print(f"Ошибка открытия управления счетами: {e}")
    
    def _open_category_management(self):
        """Открывает управление категориями."""
        try:
            dialog = CategoryManagementDialog(self, self.db)
            dialog.data_updated.connect(self._on_child_data_updated)
            dialog.show()
            self.open_windows['categories'] = dialog
            self.show_status_message("Управление категориями открыто", 1500, "info")
            
        except Exception as e:
            self.show_status_message(f"Ошибка открытия категорий: {str(e)[:50]}", 3000, "error")
            print(f"Ошибка открытия управления категориями: {e}")
    
    def _open_transfer_dialog(self):
        """Открывает диалог переводов."""
        try:
            if not self.accounts_data:
                self.show_status_message("Нет счетов для перевода", 2000, "warning")
                return
            
            dialog = TransferDialog(self, self.db, self.accounts_data)
            dialog.data_updated.connect(self._on_child_data_updated)
            dialog.show()
            self.open_windows['transfer'] = dialog
            self.show_status_message("Диалог переводов открыт", 1500, "info")
            
        except Exception as e:
            self.show_status_message(f"Ошибка открытия переводов: {str(e)[:50]}", 3000, "error")
            print(f"Ошибка открытия диалога переводов: {e}")
    
    def _open_reconciliation_dialog(self):
        """Открывает диалог сверки баланса."""
        try:
            # Не проверяем accounts_data, так как диалог сам загружает данные
            # через DatabaseManager.get_instance()
            
            # Открываем диалог с правильным количеством параметров
            dialog = ReconciliationDialog(self)
            dialog.data_updated.connect(self._on_child_data_updated)
            dialog.show()
            self.open_windows['reconciliation'] = dialog
            self.show_status_message("Сверка балансов открыта", 1500, "info")
            
        except Exception as e:
            self.show_status_message(f"Ошибка открытия сверки: {str(e)[:50]}", 3000, "error")
            print(f"Ошибка открытия диалога сверки балансов: {e}")
   
    def _open_loan_management(self):
        """Открывает управление займами."""
        try:
            dialog = LoanManagementWindow(self, self.db)
            dialog.data_updated.connect(self._on_child_data_updated)
            dialog.show()
            self.open_windows['loans'] = dialog
            self.show_status_message("Управление займами открыто", 1500, "info")
            
        except Exception as e:
            self.show_status_message(f"Ошибка открытия займов: {str(e)[:50]}", 3000, "error")
            print(f"Ошибка открытия управления займами: {e}")
    
    def _open_credit_cards(self):
        """Открывает управление кредитными картами."""
        try:
            # Проверяем есть ли кредитные карты
            has_credit_cards = any(
                info['type'] == 'Credit Card' 
                for info in self.accounts_data.values()
            )
            
            if not has_credit_cards:
                self.show_status_message("Нет кредитных карт", 2000, "warning")
                return
            
            dialog = CreditCardsWindow(self, self.db)
            dialog.data_updated.connect(self._on_child_data_updated)
            dialog.show()
            self.open_windows['credit_cards'] = dialog
            self.show_status_message("Управление картами открыто", 1500, "info")
            
        except Exception as e:
            self.show_status_message(f"Ошибка открытия карт: {str(e)[:50]}", 3000, "error")
            print(f"Ошибка открытия управления кредитными картами: {e}")
    
    def _on_child_data_updated(self):
        """Обработчик обновления данных из дочерних диалогов."""
        self._load_all_data()
        self._update_display()
        self.show_status_message("Данные обновлены", 1500, "success")
        
        # Пробрасываем сигнал дальше, если нужно
        if hasattr(self.parent, 'data_updated'):
            self.parent.data_updated.emit()
    
    # --- Вспомогательные методы ---
    
    def show_status_message(self, message, duration_ms=2000, message_type="info"):
        """Показывает сообщение в статусе (без QMessageBox)."""
        colors = {
            "info": "#6c757d",
            "success": "#28a745",
            "warning": "#fd7e14",
            "error": "#dc3545"
        }
        
        color = colors.get(message_type, "#6c757d")
        self.status_bar.setText(message)
        self.status_bar.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 11px;
                padding: 4px 8px;
                background-color: #f8f9fa;
                border-radius: 2px;
                border-top: 1px solid #dee2e6;
                font-weight: bold;
            }}
        """)
        
        # Таймер для сброса сообщения
        QTimer.singleShot(duration_ms, lambda: self._reset_status_bar())
    
    def _reset_status_bar(self):
        """Сбрасывает статус-бар в исходное состояние."""
        self.status_bar.setText("Готово")
        self.status_bar.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-size: 11px;
                padding: 4px 8px;
                background-color: #f8f9fa;
                border-radius: 2px;
                border-top: 1px solid #dee2e6;
            }
        """)
    
    # def _setup_keyboard_shortcuts(self):
        # """Настройка горячих клавиш."""
        # pass
    
    def _export_data(self):
        """Экспортирует данные."""
        self.show_status_message("Экспорт данных...", 1000, "info")
        # TODO: Реализовать экспорт
    
    def closeEvent(self, event):
        """Обработчик закрытия диалога."""
        # Закрываем все дочерние окна
        for window in self.open_windows.values():
            if window and window.isVisible():
                window.close()
        event.accept()

