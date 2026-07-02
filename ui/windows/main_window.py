# ui/main_window.py - Исправленная версия с учетом новой БД
import sys
import os
import shutil
from datetime import datetime
from pathlib import Path
import traceback

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QMessageBox, QMenuBar, QMenu,
    QFileDialog, QApplication, QScrollArea, QDialog, QTextEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QFont

from core.database import DatabaseManager
from ui.dialogs.operations_dialog import OperationsDialog
from ui.dialogs.account_dialog import AccountManagementDialog
from ui.dialogs.category_dialog import CategoryManagementDialog
from ui.dialogs.credit_cards_window import CreditCardsWindow
from ui.dialogs.loan_dialog import LoanManagementWindow
# from ui.widgets.pie_chart_widget import PieChartWidget
from ui.widgets.income_expense_chart import IncomeExpenseChart
from ui.widgets.window_utils import center_window
from ui.widgets.expense_pie_chart_widget import ExpensePieChartWidget


class MainWindow(QMainWindow):
    """Главное окно приложения на PySide6."""
    
    data_updated = Signal()
    
    def __init__(self):
        super().__init__()
        self.db = None
        self._init_database()
        self.setWindowTitle("Простой Бюджет (PySide6 v2) - SQLite")
        # Устанавливаем фиксированный размер как на скриншоте
        # self.setFixedSize(1300, 680)
        self.setMinimumSize(1300, 680)
        self.resize(1300, 680)
        
        center_window(self)
        # # Центрируем окно
        # screen_geometry = QApplication.primaryScreen().availableGeometry()
        # x = (screen_geometry.width() - 1300) // 2
        # y = (screen_geometry.height() - 680) // 2-15
        # self.move(x, y)
        
        # Хранилище открытых окон
        self.open_windows = {
            'operations': None,
            'accounts': None,
            'categories': None,
            'dashboard': None,
            'transfers': None,
            'reconciliation': None,
            'credit_cards': None,
            'loans': None
        }
        
        # Данные приложения
        self.accounts_data = {}
        self.all_categories_data = {}
        self.categories_by_name = {}
        
        self._init_ui()
        self._create_menu()
        self._load_all_data()
        self._update_display()
        
        # Подключаем сигнал обновления данных
        self.data_updated.connect(self._on_data_updated)
    
    def _safe_float(self, value, default=0.0):
        """Безопасное преобразование в float."""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def _safe_int(self, value, default=1):
        """Безопасное преобразование в int."""
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def _safe_str(self, value, default=""):
        """Безопасное преобразование в строку."""
        if value is None:
            return default
        try:
            return str(value)
        except:
            return default
    
    def _init_database(self):
        """Инициализация базы данных с обработкой ошибок."""
        try:
            self.db = DatabaseManager()  # Используем ваш конструктор
            print("✅ База данных инициализирована")
        except Exception as e:
            QMessageBox.critical(
                None,
                "Ошибка базы данных",
                f"Не удалось подключиться к базе данных:\n{str(e)}\n\n"
                "Проверьте наличие файла budget.db в папке с программой."
            )
            sys.exit(1)
    
    def _init_ui(self):
        """Инициализация пользовательского интерфейса."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        
        # === ВЕРХНЯЯ ЧАСТЬ: КНОПКИ И ОБЩИЙ БАЛАНС ===
        top_container = self._create_top_panel()
        main_layout.addWidget(top_container)
        
        # Разделитель
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.HLine)
        separator1.setFrameShadow(QFrame.Sunken)
        separator1.setStyleSheet("background-color: #ddd; margin: 5px 0;")
        main_layout.addWidget(separator1)
        
        # === СЧЕТА В 2 КОЛОНКИ ===
        accounts_container = self._create_accounts_panel()
        main_layout.addWidget(accounts_container, 0)
        
        # Разделитель
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setFrameShadow(QFrame.Sunken)
        separator2.setStyleSheet("background-color: #ddd; margin: 5px 0;")
        main_layout.addWidget(separator2)
        
        # === ГРАФИКИ В 2 КОЛОНКИ ===
        charts_container = self._create_charts_panel()
        main_layout.addWidget(charts_container, 1)
        
        # Статус бар
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Готово")
    
    def _create_top_panel(self):
        """Создает верхнюю панель с кнопками и общим балансом."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Кнопка "Обновить"
        refresh_btn = QPushButton("🔄 Обновить")
        refresh_btn.setMaximumWidth(100)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        refresh_btn.clicked.connect(self._refresh_data)
        layout.addWidget(refresh_btn)
        
        # Кнопка "+ Операции"
        add_op_btn = QPushButton("+ Операции")
        add_op_btn.setMaximumWidth(100)
        add_op_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        add_op_btn.clicked.connect(self._open_operations_dialog)
        layout.addWidget(add_op_btn)
        
        # Кнопка "Дашборд"
        dashboard_btn = QPushButton("📊 Дашборд")
        dashboard_btn.setMaximumWidth(100)
        dashboard_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        dashboard_btn.clicked.connect(self._open_dashboard)
        layout.addWidget(dashboard_btn)
        
        # Растягиваем пространство
        layout.addStretch()
        
        # Общий баланс
        balance_container = self._create_balance_widget()
        layout.addWidget(balance_container)
        
        return container
    
    def _create_balance_widget(self):
        """Создает виджет общего баланса."""
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 4px;
                border: 1px solid #dee2e6;
                padding: 2px;
            }
        """)
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # Текст "Общий баланс:"
        balance_text_label = QLabel("Общий баланс:")
        balance_text_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #2c3e50;
                font-weight: bold;
                background-color: transparent;
            }
        """)
        layout.addWidget(balance_text_label)
        
        # Сумма баланса
        self.total_balance_label = QLabel("0.00 ₽")
        self.total_balance_label.setAlignment(Qt.AlignCenter)
        self.total_balance_label.setMinimumWidth(120)
        self._update_balance_style(0)
        layout.addWidget(self.total_balance_label)
        
        return container
    
    def _create_accounts_panel(self):
        """Создает панель счетов в 2 колонки."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # ЛЕВАЯ КОЛОНКА - Обычные счета
        left_widget = self._create_accounts_column("regular")
        layout.addWidget(left_widget, 1)
        
        # ПРАВАЯ КОЛОНКА - Кредитные карты
        right_widget = self._create_accounts_column("credit")
        layout.addWidget(right_widget, 1)
        
        return container
    
    def _create_accounts_column(self, column_type):
        """Создает колонку для счетов."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Создаем layout для счетов
        accounts_layout = QVBoxLayout()
        accounts_layout.setSpacing(2)
        
        # Сохраняем ссылку на layout
        if column_type == "regular":
            self.regular_accounts_layout = accounts_layout
        else:
            self.credit_accounts_layout = accounts_layout
        
        # Создаем scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(180)
        scroll.setMaximumHeight(220)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        # Контейнер для счетов
        scroll_widget = QWidget()
        scroll_widget.setLayout(accounts_layout)
        scroll.setWidget(scroll_widget)
        
        layout.addWidget(scroll)
        return widget
    
    def _create_charts_panel(self):
        """Создает панель графиков."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Круговая диаграмма РАСХОДОВ
        from ui.widgets.expense_pie_chart_widget import ExpensePieChartWidget
        self.pie_chart = ExpensePieChartWidget(self, self.db)
        self.pie_chart.setMinimumHeight(250)
        self.pie_chart.setMaximumHeight(270)
        layout.addWidget(self.pie_chart, 1)
        
        # График доходов/расходов
        self.income_expense_chart = IncomeExpenseChart(self, self.db)
        self.income_expense_chart.setMinimumHeight(250)
        self.income_expense_chart.setMaximumHeight(270)
        layout.addWidget(self.income_expense_chart, 1)
        
        return container
    
    def _create_menu(self):
        """Создает главное меню приложения."""
        menubar = self.menuBar()
        
        # Меню Файл
        file_menu = menubar.addMenu("Файл")
        self._add_menu_action(file_menu, "Импорт CSV...", self._import_from_csv)
        self._add_menu_action(file_menu, "Экспорт в CSV...", self._export_to_csv)
        file_menu.addSeparator()
        self._add_menu_action(file_menu, "Создать резервную копию...", self._create_backup)
        self._add_menu_action(file_menu, "Восстановить...", self._restore_backup)
        self._add_menu_action(file_menu, "Информация о копиях", self._show_backup_info)
        file_menu.addSeparator()
        self._add_menu_action(file_menu, "Выход", self.close)
        
        # Меню Настройки
        settings_menu = menubar.addMenu("Настройки")
        self._add_menu_action(settings_menu, "Управление счетами", self._open_account_management)
        self._add_menu_action(settings_menu, "Управление категориями", self._open_category_management)
        settings_menu.addSeparator()
        self._add_menu_action(settings_menu, "Внешний вид", self._stub_method)
        self._add_menu_action(settings_menu, "Язык", self._stub_method)
        settings_menu.addSeparator()
        self._add_menu_action(settings_menu, "Настройки уведомлений", self._stub_method)
        self._add_menu_action(settings_menu, "Автоматизация", self._stub_method)
        
        # Меню Операции
        operations_menu = menubar.addMenu("Операции")
        self._add_menu_action(operations_menu, "Добавить операцию...", self._open_operations_dialog)
        self._add_menu_action(operations_menu, "Посмотреть все транзакции", 
                             lambda: self._open_operations_dialog(show_filters=True))
        
        # Меню Кредиты
        credit_menu = menubar.addMenu("Кредиты")
        self._add_menu_action(credit_menu, "Управление кредитными картами", self._open_credit_cards)
        self._add_menu_action(credit_menu, "Управление займами", self._open_loan_management)
        self._add_menu_action(credit_menu, "Аналитика по кредитам", self._stub_method)
        
        # Меню Отчеты
        reports_menu = menubar.addMenu("Отчеты")
        self._add_menu_action(reports_menu, "Дашборд", self._open_dashboard)
        self._add_menu_action(reports_menu, "Месячный отчет", self._stub_method)
        self._add_menu_action(reports_menu, "Отчет по категориям", self._show_category_report)
        self._add_menu_action(reports_menu, "Анализ расходов", self._stub_method)
        
        # Меню Помощь
        help_menu = menubar.addMenu("Помощь")
        self._add_menu_action(help_menu, "Справка", self._stub_method)
        self._add_menu_action(help_menu, "О программе", self._show_about)
    
    def _add_menu_action(self, menu, text, slot):
        """Добавляет действие в меню."""
        action = QAction(text, self)
        action.triggered.connect(slot)
        menu.addAction(action)
    
    # --- Методы управления данными ---
    
    def _load_all_data(self):
        """Загружает все данные из БД."""
        try:
            print("=" * 50)
            print("ДИАГНОСТИКА ЗАГРУЗКИ ДАННЫХ")
            print("=" * 50)
            
            if not self.db:
                self._init_database()
            
            # Загрузка счетов - ваша БД возвращает СЛОВАРИ
            accounts = self.db.get_accounts_direct()
            print(f"✅ Получено счетов: {len(accounts) if accounts else 0}")
            
            self.accounts_data = {}
            
            if accounts:
                for acc in accounts:
                    try:
                        # БД возвращает словари!
                        account_id = acc['id']
                        account_name = acc.get('name', 'Без названия')
                        account_type = acc.get('type', 'Cash')
                        
                        # Безопасное получение балансов
                        initial_balance = self._safe_float(acc.get('initial_balance', 0.0))
                        current_balance = self._safe_float(acc.get('current_balance', 0.0))
                        
                        # Кредитные параметры
                        credit_limit = self._safe_float(acc.get('credit_limit', 0.0))
                        payment_due_day = self._safe_int(acc.get('payment_due_day', 1))
                        min_payment_percent = self._safe_float(acc.get('min_payment_percent', 5.0))
                        
                        # Сохраняем в формате, который ожидает остальной код
                        self.accounts_data[account_id] = {
                            'id': account_id,
                            'name': account_name,
                            'type': account_type,
                            'initial_balance': initial_balance,
                            'balance': current_balance,  # текущий баланс
                            'credit_limit': credit_limit,
                            'payment_due_day': payment_due_day,
                            'min_payment_percent': min_payment_percent,
                            'last_payment_date': acc.get('last_payment_date'),
                            'currency': acc.get('currency', 'RUB'),
                            'is_active': acc.get('is_active', True)
                        }
                        
                        print(f"  ✅ Счет: {account_name} (ID: {account_id}), Баланс: {current_balance}")
                        
                    except KeyError as e:
                        print(f"⚠️ Ошибка ключа в данных счета: {e}, данные: {acc}")
                        continue
                    except Exception as e:
                        print(f"⚠️ Ошибка обработки счета: {e}")
                        continue
            
            print(f"✅ Итого загружено счетов: {len(self.accounts_data)}")
            
            # Загрузка категорий - тоже могут быть словари
            categories = []
            try:
                # Пробуем разные методы
                if hasattr(self.db, 'get_categories_with_hierarchy'):
                    categories = self.db.get_categories_with_hierarchy()
                    print(f"✅ Используем get_categories_with_hierarchy()")
                elif hasattr(self.db, 'get_categories'):
                    categories = self.db.get_categories(include_subcategories=True)
                    print(f"✅ Используем get_categories()")
            except Exception as e:
                print(f"⚠️ Ошибка загрузки категорий: {e}")
            
            self.all_categories_data = {}
            self.categories_by_name = {}
            
            if categories:
                for cat in categories:
                    try:
                        # Проверяем формат категорий
                        if isinstance(cat, dict):
                            # Новый формат - словарь
                            cat_id = cat.get('id')
                            cat_name = cat.get('name', 'Без названия')
                            
                            if cat_id:
                                self.all_categories_data[cat_id] = cat
                                self.categories_by_name[cat_name] = cat_id
                                
                        elif isinstance(cat, (tuple, list)):
                            # Старый формат - кортеж
                            if len(cat) >= 3:
                                cat_id = cat[0]
                                cat_name = cat[1] if cat[1] else 'Без названия'
                                
                                # Преобразуем в словарь для единообразия
                                cat_dict = {
                                    'id': cat_id,
                                    'name': cat_name,
                                    'type': cat[2] if len(cat) > 2 else 'expense',
                                    'budget_amount_monthly': self._safe_float(cat[3] if len(cat) > 3 else 0.0),
                                    'parent_id': cat[4] if len(cat) > 4 else None
                                }
                                
                                self.all_categories_data[cat_id] = cat_dict
                                self.categories_by_name[cat_name] = cat_id
                                
                    except Exception as e:
                        print(f"⚠️ Ошибка обработки категории: {e}")
                        continue
            
            print(f"✅ Загружено категорий: {len(self.all_categories_data)}")
            
            # Обновляем открытые окна
            self._update_open_windows()
            
            print("=" * 50)
            print("✅ ЗАГРУЗКА ДАННЫХ ЗАВЕРШЕНА")
            print("=" * 50)
            
        except Exception as e:
            print(f"❌ Критическая ошибка загрузки данных: {e}")
            traceback.print_exc()
            self.status_bar.showMessage(f"Ошибка загрузки данных", 3000)
            
    def _update_display(self):
        """Обновляет отображение данных в главном окне."""
        try:
            self._update_total_balance()
            self._update_individual_balances()
            
            # Обновляем круговую диаграмму
            if hasattr(self, 'pie_chart') and self.pie_chart:
                try:
                    print("Обновление круговой диаграммы")
                    if hasattr(self.pie_chart, 'update_chart'):
                        self.pie_chart.update_chart()
                    elif hasattr(self.pie_chart, 'refresh'):
                        self.pie_chart.refresh()
                except Exception as e:
                    print(f"Ошибка обновления круговой диаграммы: {e}")
            
            # Обновляем график доходов/расходов
            if hasattr(self, 'income_expense_chart') and self.income_expense_chart:
                try:
                    print("Обновление графика доходов/расходов")
                    # Создаем временный метод если его нет
                    if not hasattr(self.income_expense_chart, 'update_chart'):
                        self.income_expense_chart.update_chart = lambda: self.income_expense_chart.update_data()
                    
                    self.income_expense_chart.update_chart()
                except Exception as e:
                    print(f"Ошибка обновления графика доходов/расходов: {e}")
            
            if not self.accounts_data:
                self.status_bar.showMessage("Создайте свой первый счет для начала работы", 3000)
            else:
                self.status_bar.showMessage("Готово")
                
        except Exception as e:
            print(f"Ошибка обновления отображения: {e}")
            traceback.print_exc()
            self.status_bar.showMessage(f"Ошибка обновления: {e}", 3000)
    
    def _update_total_balance(self):
        """Обновляет отображение общего баланса."""
        try:
            total_balance = sum(acc['balance'] for acc in self.accounts_data.values())
            self._update_balance_style(total_balance)
            
            if total_balance < 0:
                text = f"-{abs(total_balance):,.2f} ₽"
            else:
                text = f"{total_balance:,.2f} ₽"
            
            self.total_balance_label.setText(text)
            
        except Exception as e:
            print(f"Ошибка расчета общего баланса: {e}")
            self.total_balance_label.setText("0.00 ₽")
            self._update_balance_style(0)
    
    def _update_balance_style(self, balance):
        """Обновляет стиль отображения баланса."""
        if balance < 0:
            color = "#e74c3c"  # Красный
        elif balance == 0:
            color = "#f39c12"  # Оранжевый
        else:
            color = "#27ae60"  # Зеленый
        
        self.total_balance_label.setStyleSheet(f"""
            QLabel {{
                font-size: 16px;
                font-weight: bold;
                color: {color};
                padding: 6px 12px;
                background-color: white;
                border-radius: 3px;
                border: 1px solid #ced4da;
            }}
        """)
    
    def _update_individual_balances(self):
        """Обновляет отображение индивидуальных балансов."""
        try:
            # Очищаем обе колонки
            for layout in [self.regular_accounts_layout, self.credit_accounts_layout]:
                self._clear_layout(layout)
            
            if not self.accounts_data:
                self._show_no_accounts_message()
                return
            
            # Разделяем счета
            regular_accounts = []
            credit_accounts = []
            
            for acc_id, acc_info in self.accounts_data.items():
                if "Контрагент:" in str(acc_info['name']):
                    continue
                
                if acc_info['type'] == 'Credit Card':
                    credit_accounts.append((acc_id, acc_info))
                else:
                    regular_accounts.append((acc_id, acc_info))
            
            # Сортировка по балансу
            regular_accounts.sort(key=lambda x: x[1]['balance'])
            credit_accounts.sort(key=lambda x: x[1]['balance'])
            
            # Обычные счета
            if not regular_accounts:
                self._add_no_data_label(self.regular_accounts_layout, "Нет обычных счетов")
            else:
                for acc_id, acc_info in regular_accounts:
                    self._create_compact_regular_widget(acc_info, self.regular_accounts_layout)
            
            # Кредитные карты
            if not credit_accounts:
                self._add_no_data_label(self.credit_accounts_layout, "Нет кредитных карт")
            else:
                for acc_id, acc_info in credit_accounts:
                    self._create_credit_widget(acc_info, acc_id, self.credit_accounts_layout)
            
            # Добавляем растяжку
            self.regular_accounts_layout.addStretch()
            self.credit_accounts_layout.addStretch()
            
        except Exception as e:
            print(f"Ошибка обновления балансов: {e}")
            traceback.print_exc()
    
    def _clear_layout(self, layout):
        """Очищает layout."""
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
    
    def _show_no_accounts_message(self):
        """Показывает сообщение об отсутствии счетов."""
        label = QLabel("Нет счетов")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #95a5a6; font-style: italic; padding: 20px; font-size: 11px;")
        self.regular_accounts_layout.addWidget(label)
    
    def _add_no_data_label(self, layout, text):
        """Добавляет сообщение об отсутствии данных."""
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #95a5a6; font-style: italic; padding: 10px; font-size: 11px;")
        layout.addWidget(label)
    
    def _create_compact_regular_widget(self, acc_info, layout):
        """Создает компактный виджет для обычных счетов."""
        frame = QWidget()
        frame.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border-radius: 3px;
                margin: 1px;
            }
            QWidget:hover {
                background-color: #e9ecef;
            }
        """)
        
        inner_layout = QHBoxLayout(frame)
        inner_layout.setContentsMargins(8, 6, 8, 6)
        inner_layout.setSpacing(8)
        
        # Имя счета
        name = str(acc_info['name'])
        if len(name) > 20:
            name = name[:18] + "..."
        
        name_label = QLabel(name)
        name_label.setStyleSheet("font-size: 12px; color: #2c3e50; font-weight: normal;")
        name_label.setToolTip(acc_info['name'])
        inner_layout.addWidget(name_label, 1)
        
        # Баланс
        balance = acc_info['balance']
        if balance < 0:
            color = "#e74c3c"
            balance_text = f"-{abs(balance):,.0f} ₽"
        else:
            color = "#27ae60"
            balance_text = f"{balance:,.0f} ₽"
        
        balance_label = QLabel(balance_text)
        balance_label.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {color};")
        inner_layout.addWidget(balance_label)
        
        layout.addWidget(frame)
    
    def _create_credit_widget(self, acc_info, account_id, layout):
        """Создает виджет для кредитных карт."""
        try:
            # Используем данные из accounts_data, а не запрашиваем БД
            credit_limit = acc_info.get('credit_limit', 0.0)
            debt = abs(acc_info['balance'])
            available = credit_limit + acc_info['balance']
            utilization = (debt / credit_limit * 100) if credit_limit > 0 else 0
            
            # Основной контейнер
            container = QWidget()
            container.setStyleSheet("""
                QWidget {
                    background-color: #f8f9fa;
                    border-radius: 3px;
                    margin: 1px;
                }
                QWidget:hover {
                    background-color: #e9ecef;
                }
            """)
            
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(8, 6, 8, 6)
            container_layout.setSpacing(4)
            
            # Первая строка: Название и долг
            top_row = QWidget()
            top_row.setStyleSheet("background-color: transparent;")
            top_layout = QHBoxLayout(top_row)
            top_layout.setContentsMargins(0, 0, 0, 0)
            
            # Название карты
            name_label = QLabel(str(acc_info['name']))
            name_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #2c3e50;")
            name_label.setAlignment(Qt.AlignLeft)
            top_layout.addWidget(name_label, 1)
            
            # Долг
            debt_container = QWidget()
            debt_container.setStyleSheet("background-color: transparent;")
            debt_layout = QHBoxLayout(debt_container)
            debt_layout.setContentsMargins(0, 0, 0, 0)
            debt_layout.setSpacing(6)
            
            debt_text = QLabel("Долг:")
            debt_text.setStyleSheet("font-size: 12px; color: #7f8c8d;")
            debt_layout.addWidget(debt_text)
            
            debt_amount = QLabel(f"{debt:,.2f} ₽")
            debt_amount.setStyleSheet("font-size: 12px; font-weight: bold; color: #e74c3c;")
            debt_layout.addWidget(debt_amount)
            
            percent_text = QLabel(f"({utilization:.1f}% лимита)")
            if utilization > 80:
                percent_color = "#e74c3c"
            elif utilization > 50:
                percent_color = "#f39c12"
            else:
                percent_color = "#7f8c8d"
            
            percent_text.setStyleSheet(f"font-size: 10px; color: {percent_color};")
            debt_layout.addWidget(percent_text)
            
            top_layout.addWidget(debt_container)
            container_layout.addWidget(top_row)
            
            # Вторая строка: Лимит и доступно
            bottom_row = QWidget()
            bottom_row.setStyleSheet("background-color: transparent;")
            bottom_layout = QHBoxLayout(bottom_row)
            bottom_layout.setContentsMargins(0, 0, 0, 0)
            
            # Лимит
            limit_container = QWidget()
            limit_container.setStyleSheet("background-color: transparent;")
            limit_inner = QHBoxLayout(limit_container)
            limit_inner.setContentsMargins(0, 0, 0, 0)
            limit_inner.setSpacing(4)
            
            limit_label = QLabel("Лимит:")
            limit_label.setStyleSheet("font-size: 11px; color: #7f8c8d;")
            limit_inner.addWidget(limit_label)
            
            limit_amount = QLabel(f"{credit_limit:,.0f} ₽")
            limit_amount.setStyleSheet("font-size: 11px; font-weight: bold; color: #2c3e50;")
            limit_inner.addWidget(limit_amount)
            
            bottom_layout.addWidget(limit_container)
            bottom_layout.addStretch()
            
            # Доступно
            available_container = QWidget()
            available_container.setStyleSheet("background-color: transparent;")
            available_inner = QHBoxLayout(available_container)
            available_inner.setContentsMargins(0, 0, 0, 0)
            available_inner.setSpacing(4)
            
            available_label = QLabel("Доступно:")
            available_label.setStyleSheet("font-size: 11px; color: #7f8c8d;")
            available_inner.addWidget(available_label)
            
            available_color = "#27ae60" if available >= 0 else "#e74c3c"
            available_amount = QLabel(f"{available:,.0f} ₽")
            available_amount.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {available_color};")
            available_inner.addWidget(available_amount)
            
            bottom_layout.addWidget(available_container)
            container_layout.addWidget(bottom_row)
            
            layout.addWidget(container)
            
        except Exception as e:
            print(f"Ошибка создания виджета кредитной карты: {e}")
            traceback.print_exc()
            # Создаем простой виджет в случае ошибки
            self._create_compact_regular_widget(acc_info, layout)
            
    def _update_open_windows(self):
        """Обновляет все открытые окна."""
        for window_type, window in self.open_windows.items():
            if window and window.isVisible():
                try:
                    if hasattr(window, 'refresh_data'):
                        window.refresh_data()
                    elif hasattr(window, '_update_display'):
                        window._update_display()
                except Exception as e:
                    print(f"Ошибка обновления окна {window_type}: {e}")
    
    # --- Методы открытия диалогов ---
    
    def _open_operations_dialog(self, show_filters=False):
        """Открывает диалог операций."""
        try:
            if self.open_windows['operations'] and self.open_windows['operations'].isVisible():
                self.open_windows['operations'].raise_()
                self.open_windows['operations'].activateWindow()
                return
            
            dialog = OperationsDialog(self, self.db, self.accounts_data)
            dialog.data_updated.connect(self._on_data_updated)
            self.open_windows['operations'] = dialog
            
            if show_filters:
                dialog.show_filters()
            
            dialog.show()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть диалог операций:\n{e}")
            traceback.print_exc()
    
    def _open_account_management(self):
        """Открывает управление счетами."""
        try:
            if self.open_windows['accounts'] and self.open_windows['accounts'].isVisible():
                self.open_windows['accounts'].raise_()
                self.open_windows['accounts'].activateWindow()
                return
            
            dialog = AccountManagementDialog(self, self.db)
            dialog.data_updated.connect(self._on_data_updated)
            self.open_windows['accounts'] = dialog
            dialog.show()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть управление счетами:\n{e}")
            traceback.print_exc()
    
    def _open_category_management(self):
        """Открывает управление категориями."""
        try:
            if self.open_windows['categories'] and self.open_windows['categories'].isVisible():
                self.open_windows['categories'].raise_()
                self.open_windows['categories'].activateWindow()
                return
            
            dialog = CategoryManagementDialog(self, self.db)
            dialog.data_updated.connect(self._on_data_updated)
            self.open_windows['categories'] = dialog
            dialog.show()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть управление категориями:\n{e}")
            traceback.print_exc()
    
    def _open_credit_cards(self):
        """Открывает управление кредитными картами."""
        try:
            if self.open_windows['credit_cards'] and self.open_windows['credit_cards'].isVisible():
                self.open_windows['credit_cards'].raise_()
                self.open_windows['credit_cards'].activateWindow()
                return
            
            # Проверяем наличие кредитных карт
            has_credit_cards = any(
                acc['type'] == 'Credit Card' 
                for acc in self.accounts_data.values()
            )
            
            if not has_credit_cards:
                QMessageBox.information(
                    self,
                    "Кредитные карты",
                    "У вас нет кредитных карт.\n\n"
                    "Добавьте кредитную карту через 'Настройки' → 'Управление Счетами' → выберите тип 'Credit Card'."
                )
                return
            
            dialog = CreditCardsWindow(self, self.db)
            dialog.data_updated.connect(self._on_data_updated)
            self.open_windows['credit_cards'] = dialog
            dialog.show()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть управление кредитными картами:\n{e}")
            traceback.print_exc()
    
    def _open_loan_management(self):
        """Открывает управление займами."""
        try:
            if self.open_windows['loans'] and self.open_windows['loans'].isVisible():
                self.open_windows['loans'].raise_()
                self.open_windows['loans'].activateWindow()
                return
            
            dialog = LoanManagementWindow(self, self.db)
            dialog.data_updated.connect(self._on_data_updated)
            self.open_windows['loans'] = dialog
            dialog.show()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть управление займами:\n{e}")
            traceback.print_exc()
    
    def _open_dashboard(self):
        """Открывает дашборд."""
        QMessageBox.information(self, "В разработке", "Функция в разработке")
    
    # --- Обработчики событий ---
    
    def _refresh_data(self):
        """Обновляет все данные."""
        self._load_all_data()
        self._update_display()
        self.status_bar.showMessage("Данные обновлены", 2000)
    
    def _on_data_updated(self):
        """Обработчик обновления данных."""
        self._refresh_data()
    
    def _stub_method(self):
        """Заглушка для нереализованных методов."""
        QMessageBox.information(self, "В разработке", "Функция в разработке")
    
    # --- Вспомогательные методы ---
    
    def _show_about(self):
        """Показывает информацию о программе."""
        about_text = (
            "Простой Бюджет (PySide6) - SQLite\n"
            "Версия: 2.4\n"
            "© 2026\n\n"
            "Управление личными финансами\n"
            "Поддержка счетов, категорий, транзакций,\n"
            "переводов, кредитных карт и займов."
        )
        QMessageBox.about(self, "О программе", about_text)
    
    def _show_category_report(self):
        """Показывает отчет по категориям."""
        try:
            # Пробуем получить статистику
            stats = []
            try:
                stats = self.db.get_category_statistics(include_subcategories=True)
            except:
                pass
            
            if not stats:
                QMessageBox.information(self, "Отчет по категориям", "Нет данных для формирования отчета")
                return
            
            report_text = self._generate_category_report(stats)
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Отчет по категориям")
            dialog.setGeometry(200, 200, 800, 600)
            
            layout = QVBoxLayout(dialog)
            
            text_edit = QTextEdit()
            text_edit.setPlainText(report_text)
            text_edit.setReadOnly(True)
            text_edit.setFont(QFont("Consolas", 10))
            
            layout.addWidget(text_edit)
            
            button_layout = QHBoxLayout()
            
            save_button = QPushButton("Сохранить в файл")
            save_button.clicked.connect(lambda: self._save_report_to_file(report_text, "Отчет по категориям"))
            
            close_button = QPushButton("Закрыть")
            close_button.clicked.connect(dialog.close)
            
            button_layout.addWidget(save_button)
            button_layout.addStretch()
            button_layout.addWidget(close_button)
            
            layout.addLayout(button_layout)
            
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сформировать отчет:\n{e}")
            traceback.print_exc()
    
    def _generate_category_report(self, stats):
        """Генерирует отчет по категориям."""
        try:
            if not stats:
                return "📭 Нет данных для формирования отчета по категориям."
            
            report_text = "📊 ОТЧЕТ ПО КАТЕГОРИЯМ\n"
            report_text += "=" * 50 + "\n\n"
            
            # Создаем простой отчет без сложной группировки
            total_expense = 0
            
            for stat in stats:
                if len(stat) >= 6:
                    cat_id, name, cat_type, budget, parent_id, total_expense_val = stat[:6]
                    
                    try:
                        expense = float(total_expense_val) if total_expense_val else 0.0
                    except (ValueError, TypeError):
                        expense = 0.0
                    
                    if expense > 0:
                        total_expense += expense
                        
                        indent = "    " if parent_id else ""
                        report_text += f"{indent}{name}: {expense:,.2f} ₽\n"
            
            report_text += "\n" + "=" * 50 + "\n"
            report_text += f"💸 Общие расходы: {total_expense:,.2f} ₽\n"
            report_text += f"📋 Всего категорий с расходами: {len([s for s in stats if len(s) >= 6 and s[5] and float(s[5]) > 0])}\n"
            
            return report_text
            
        except Exception as e:
            return f"❌ Ошибка при формировании отчета:\n{str(e)}"
    
    def _save_report_to_file(self, report_text, title):
        """Сохраняет отчет в файл."""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            f"Сохранить {title}",
            f"{title.replace(' ', '_')}.txt",
            "Text files (*.txt);;All files (*.*)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(report_text)
                self.status_bar.showMessage(f"Отчет сохранен: {os.path.basename(filename)}", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{e}")
    
    # --- Методы работы с файлами (импорт/экспорт/резервные копии) ---
    
    def _export_to_csv(self):
        """Экспортирует транзакции в CSV."""
        QMessageBox.information(self, "В разработке", "Экспорт в CSV в разработке")
    
    def _import_from_csv(self):
        """Импортирует транзакции из CSV."""
        QMessageBox.information(self, "В разработке", "Импорт из CSV в разработке")
    
    def _create_backup(self):
        """Создает резервную копию БД."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить резервную копию",
                f"budget_backup_{timestamp}.db",
                "Database files (*.db);;All files (*.*)"
            )
            
            if filename:
                shutil.copy2("budget.db", filename)
                QMessageBox.information(self, "Успех", f"Резервная копия создана:\n{filename}")
                
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать резервную копию:\n{e}")
    
    def _restore_backup(self):
        """Восстанавливает БД из резервной копии."""
        QMessageBox.information(self, "В разработке", "Восстановление из резервной копии в разработке")
    
    def _show_backup_info(self):
        """Показывает информацию о резервных копиях."""
        QMessageBox.information(self, "В разработке", "Информация о резервных копиях в разработке")
    
    def closeEvent(self, event):
        """Обработчик закрытия окна."""
        # Закрываем все дочерние окна
        for window in self.open_windows.values():
            if window and window.isWidgetType() and window.isVisible():
                window.close()
        
        # Закрываем соединения с БД
        try:
            DatabaseManager.get_instance().close()
        except Exception as e:
            print(f"Ошибка при закрытии соединений БД: {e}")
        
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())