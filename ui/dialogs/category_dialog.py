# ui/dialogs/category_dialog.py
"""
Диалог управления категориями с подкатегориями
Адаптировано для работы с новой версией DatabaseManager (dict API)
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTreeWidget,
    QTreeWidgetItem, QPushButton, QComboBox, QFormLayout, QGroupBox,
    QMessageBox, QMenu, QAbstractItemView, QHeaderView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QAction

from core.database import DatabaseManager
from ui.widgets.window_utils import center_window_relative


class CategoryManagementDialog(QDialog):
    """Диалог для управления категориями с иерархией"""
    
    data_updated = Signal()
    
    def __init__(self, parent=None, db_manager=None):
        super().__init__(parent)
        self.parent = parent
        self.db = db_manager if db_manager else DatabaseManager.get_instance()
        
        self.setWindowTitle("Управление Категориями с Подкатегориями")
        self.resize(600, 550)
        
        center_window_relative(self, parent)
        
        # Переменные состояния
        self.editing_category_id = None
        self.current_parent_id = None
        self.always_on_top = False
        
        self.setup_ui()
        self.load_categories_into_tree()
        
    def setup_ui(self):
        """Создание интерфейса"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        
        # Заголовок
        title_label = QLabel("Управление Категориями с Подкатегориями")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Дерево категорий
        tree_group = QGroupBox("Дерево категорий")
        tree_layout = QVBoxLayout()
        
        self.categories_tree = QTreeWidget()
        self.categories_tree.setHeaderLabels(["Название категории", "Тип", "Плановый бюджет"])
        self.categories_tree.setColumnWidth(0, 250)
        self.categories_tree.setColumnWidth(1, 80)
        self.categories_tree.setColumnWidth(2, 120)
        self.categories_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        
        self.categories_tree.itemSelectionChanged.connect(self._on_category_select)
        self.categories_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.categories_tree.customContextMenuRequested.connect(self._show_tree_context_menu)
        
        tree_layout.addWidget(self.categories_tree)
        tree_group.setLayout(tree_layout)
        main_layout.addWidget(tree_group, 1)  # Растягиваем
        
        # Форма для добавления/редактирования
        form_group = QGroupBox("Добавить/Редактировать категорию")
        form_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Введите название категории")
        form_layout.addRow("Название:", self.name_input)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["expense", "income"])  # Для выбора оставляем английские значения
        form_layout.addRow("Тип:", self.type_combo)
        
        self.parent_combo = QComboBox()
        self.parent_combo.addItem("")
        self.parent_combo.setEditable(False)
        form_layout.addRow("Родительская категория:", self.parent_combo)
        
        self.budget_input = QLineEdit()
        self.budget_input.setText("0.0")
        form_layout.addRow("Плановый бюджет (мес.):", self.budget_input)
        
        form_group.setLayout(form_layout)
        main_layout.addWidget(form_group)
        
        # Кнопки управления
        button_layout = QHBoxLayout()
        
        self.add_button = QPushButton("Добавить")
        self.add_button.clicked.connect(self._add_category)
        button_layout.addWidget(self.add_button)
        
        self.edit_button = QPushButton("Сохранить изменения")
        self.edit_button.clicked.connect(self._edit_category)
        self.edit_button.setEnabled(False)
        button_layout.addWidget(self.edit_button)
        
        self.delete_button = QPushButton("Удалить выбранную")
        self.delete_button.clicked.connect(self._delete_selected_category)
        self.delete_button.setEnabled(False)
        button_layout.addWidget(self.delete_button)
        
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.on_close)
        button_layout.addWidget(close_button)
        
        main_layout.addLayout(button_layout)
        
        # Кнопка "Поверх всех окон"
        self.pin_button = QPushButton("📌")
        self.pin_button.setFixedWidth(40)
        self.pin_button.clicked.connect(self._toggle_pin)
        main_layout.addWidget(self.pin_button, 0, Qt.AlignRight)
        
        self.setLayout(main_layout)
        
        # Контекстное меню для дерева
        self._setup_tree_context_menu()
        
    def _setup_tree_context_menu(self):
        """Настраивает контекстное меню для дерева категорий"""
        self.tree_context_menu = QMenu(self)
        
        edit_action = QAction("✏️ Редактировать", self)
        edit_action.triggered.connect(self._edit_category)
        self.tree_context_menu.addAction(edit_action)
        
        add_sub_action = QAction("➕ Добавить подкатегорию", self)
        add_sub_action.triggered.connect(self._add_subcategory)
        self.tree_context_menu.addAction(add_sub_action)
        
        self.tree_context_menu.addSeparator()
        
        delete_action = QAction("🗑️ Удалить категорию", self)
        delete_action.triggered.connect(self._delete_selected_category)
        self.tree_context_menu.addAction(delete_action)
        
        self.tree_context_menu.addSeparator()
        
        stats_action = QAction("📊 Статистика категории", self)
        stats_action.triggered.connect(self._analyze_category)
        self.tree_context_menu.addAction(stats_action)
    
    def _show_tree_context_menu(self, position):
        """Показывает контекстное меню для дерева"""
        item = self.categories_tree.itemAt(position)
        if item:
            self.categories_tree.setCurrentItem(item)
            self.tree_context_menu.exec(self.categories_tree.mapToGlobal(position))
    
    def _toggle_pin(self):
        """Включает/выключает режим 'всегда поверх'"""
        self.always_on_top = not self.always_on_top
        self.setWindowFlag(Qt.WindowStaysOnTopHint, self.always_on_top)
        self.show()
        
        if self.always_on_top:
            self.pin_button.setText("📌")
            self.pin_button.setStyleSheet("background-color: #ffeb3b;")
        else:
            self.pin_button.setText("📌")
            self.pin_button.setStyleSheet("")
    
    def _on_category_select(self):
        """Обработчик выбора категории в дереве"""
        selected_items = self.categories_tree.selectedItems()
        
        if selected_items:
            self.edit_button.setEnabled(True)
            self.delete_button.setEnabled(True)
            
            item = selected_items[0]
            category_id = item.data(0, Qt.UserRole)
            category_data = self.db.get_category_by_id(category_id)
            
            if category_data:
                self.name_input.setText(category_data['name'])
                
                # Устанавливаем тип (обратное преобразование)
                item_type = category_data['type']
                index = self.type_combo.findText(item_type)
                if index >= 0:
                    self.type_combo.setCurrentIndex(index)
                
                # Устанавливаем родительскую категорию
                parent_id = category_data.get('parent_id')
                if parent_id:
                    parent_data = self.db.get_category_by_id(parent_id)
                    if parent_data:
                        parent_name = parent_data['name']
                        index = self.parent_combo.findText(parent_name)
                        if index >= 0:
                            self.parent_combo.setCurrentIndex(index)
                        else:
                            self.parent_combo.setCurrentIndex(0)
                    else:
                        self.parent_combo.setCurrentIndex(0)
                else:
                    self.parent_combo.setCurrentIndex(0)
                
                # Устанавливаем бюджет
                self.budget_input.setText(str(category_data.get('budget_amount_monthly', 0.0)))
                
                self.editing_category_id = category_id
        else:
            self._reset_form_state()
            
    def _add_subcategory(self):
        """Добавляет подкатегорию для выбранной категории"""
        selected_items = self.categories_tree.selectedItems()
        if not selected_items:
            self.show_status_message("⚠️ Выберите категорию для добавления подкатегории", "warning")
            return
        
        item = selected_items[0]
        item_id = item.data(0, Qt.UserRole)
        
        # Получаем данные родительской категории
        parent_data = self.db.get_category_by_id(item_id)
        if not parent_data:
            self.show_status_message("❌ Не удалось получить данные родительской категории", "error")
            return
        
        parent_name = parent_data['name']
        parent_type = parent_data['type']
        
        # Устанавливаем тип такой же как у родителя
        if parent_type == 'income':
            self.type_combo.setCurrentText('income')
        else:
            self.type_combo.setCurrentText('expense')
        
        # Сбрасываем форму и устанавливаем родителя
        self._reset_form_state()
        
        # Находим родительскую категорию в комбобоксе
        index = self.parent_combo.findText(parent_name)
        if index >= 0:
            self.parent_combo.setCurrentIndex(index)
        else:
            # Если родитель не найден в комбобоксе, обновляем список и снова ищем
            self._update_parent_combo()
            index = self.parent_combo.findText(parent_name)
            if index >= 0:
                self.parent_combo.setCurrentIndex(index)
        
        self.name_input.setFocus()
        
        self.show_status_message(f"➕ Готово к добавлению подкатегории для '{parent_name}'", "info")
    
    def load_categories_into_tree(self):
        """Загружает категории с иерархией в дерево"""
        self.categories_tree.clear()
        
        # Загружаем категории из базы
        categories = self.db.get_category_hierarchy()
        
        if not categories:
            return
        
        # Создаем словарь для связи ID с элементами дерева
        tree_items = {}
        
        # Добавляем категории в дерево
        for category in categories:
            cat_id = category['id']
            name = category['name']
            cat_type = category['type']
            budget = category.get('budget_amount_monthly', 0.0)
            parent_id = category.get('parent_id')
            
            # Преобразуем тип для отображения
            display_type = self._get_display_type(cat_type)
            
            if parent_id is None:
                # Корневая категория
                item = QTreeWidgetItem(self.categories_tree)
                item.setText(0, name)
                item.setText(1, display_type)
                item.setText(2, f"{budget:.2f} ₽")
                item.setData(0, Qt.UserRole, cat_id)
                tree_items[cat_id] = item
            elif parent_id in tree_items:
                # Подкатегория
                parent_item = tree_items[parent_id]
                item = QTreeWidgetItem(parent_item)
                item.setText(0, name)
                item.setText(1, display_type)
                item.setText(2, f"{budget:.2f} ₽")
                item.setData(0, Qt.UserRole, cat_id)
                tree_items[cat_id] = item
                parent_item.setExpanded(True)
        
        # Обновляем список родительских категорий
        self._update_parent_combo()
        
        # Сбрасываем выделение
        self.categories_tree.clearSelection()
        self._on_category_select()
    
    def _get_display_type(self, type_str):
        """Преобразует тип для отображения на русском"""
        if type_str == 'income':
            return 'Доход'
        elif type_str == 'expense':
            return 'Расход'
        else:
            return type_str
    
    def _update_parent_combo(self):
        """Обновляет список родительских категорий в комбобоксе"""
        self.parent_combo.clear()
        self.parent_combo.addItem("")  # Пустой элемент для отсутствия родителя
        
        main_categories = []
        # Берем только корневые категории (parent_id == None)
        categories = self.db.get_categories(include_subcategories=False)
        for cat in categories:
            main_categories.append(cat['name'])
        
        main_categories.sort()
        self.parent_combo.addItems(main_categories)
        
    def _add_category(self):
        """Добавляет новую категорию с поддержкой родителя"""
        name = self.name_input.text().strip()
        cat_type = self.type_combo.currentText()
        budget_str = self.budget_input.text().strip()
        parent_name = self.parent_combo.currentText()
        
        if not name:
            self.show_status_message("⚠️ Введите название категории", "warning")
            return
        
        try:
            budget = float(budget_str)
        except ValueError:
            QMessageBox.critical(self, "Ошибка", "Плановый бюджет должен быть числом.")
            return
        
        # Определяем parent_id из выбранной родительской категории
        parent_id = None
        if parent_name:
            parent_data = self.db.get_category_by_name(parent_name)
            if parent_data:
                parent_id = parent_data['id']
                # Автоматически устанавливаем тип как у родителя
                if cat_type != parent_data['type']:
                    cat_type = parent_data['type']
                    self.type_combo.setCurrentText(cat_type)
                    self.show_status_message("⚠️ Тип автоматически изменен на тип родительской категории", "warning")
            else:
                QMessageBox.critical(self, "Ошибка", 
                                   f"Родительская категория '{parent_name}' не найдена.")
                return
        
        # Проверяем соответствие типов родительской и дочерней категорий
        if parent_id:
            parent_category = self.db.get_category_by_id(parent_id)
            if parent_category and parent_category['type'] != cat_type:
                QMessageBox.critical(self, "Ошибка", 
                                   f"Подкатегория типа '{cat_type}' не может быть добавлена "
                                   f"к родительской категории типа '{parent_category['type']}'.")
                return
        
        # Добавляем категорию в базу
        category_data = {
            'name': name,
            'type': cat_type,
            'budget_amount_monthly': budget,
            'parent_id': parent_id
        }
        
        category_id = self.db.add_category(category_data)
        
        if category_id:
            if parent_id:
                parent_name_display = parent_category['name'] if parent_category else parent_name
                self.show_status_message(f"✅ Подкатегория '{name}' добавлена к '{parent_name_display}'", "success")
            else:
                self.show_status_message(f"✅ Категория '{name}' добавлена", "success")
            
            self.load_categories_into_tree()
            self._reset_form_state()
            self.data_updated.emit()
        else:
            self.show_status_message(f"❌ Не удалось добавить категорию '{name}'", "error")

    def _edit_category(self):
        """Редактирует выбранную категорию"""
        if not self.editing_category_id:
            self.show_status_message("⚠️ Выберите категорию для редактирования", "warning")
            return
        
        name = self.name_input.text().strip()
        cat_type = self.type_combo.currentText()
        budget_str = self.budget_input.text().strip()
        parent_name = self.parent_combo.currentText()
        
        if not name:
            QMessageBox.critical(self, "Ошибка", "Введите название категории.")
            return
        
        try:
            budget = float(budget_str)
        except ValueError:
            QMessageBox.critical(self, "Ошибка", "Плановый бюджет должен быть числом.")
            return
        
        parent_id = None
        if parent_name:
            parent_data = self.db.get_category_by_name(parent_name)
            if parent_data:
                parent_id = parent_data['id']
            else:
                QMessageBox.critical(self, "Ошибка", 
                                   f"Родительская категория '{parent_name}' не найдена.")
                return
        
        # Проверяем уникальность имени
        existing_category = self.db.get_category_by_name(name)
        if existing_category and existing_category['id'] != self.editing_category_id:
            QMessageBox.critical(self, "Ошибка", f"Категория с именем '{name}' уже существует.")
            return
        
        # Обновляем категорию
        category_data = {
            'name': name,
            'type': cat_type,
            'budget_amount_monthly': budget,
            'parent_id': parent_id
        }
        
        success = self.db.update_category(self.editing_category_id, category_data)
        
        if success:
            self.show_status_message(f"✏️ Категория '{name}' обновлена", "success")
            self.load_categories_into_tree()
            self._reset_form_state()
            self.data_updated.emit()
        else:
            self.show_status_message(f"❌ Не удалось обновить категорию '{name}'", "error")
    
    def _delete_selected_category(self):
        """Удаляет выбранную категорию с подкатегориями"""
        selected_items = self.categories_tree.selectedItems()
        if not selected_items:
            self.show_status_message("⚠️ Выберите категорию для удаления", "warning")
            return
        
        item = selected_items[0]
        category_name = item.text(0)
        category_id = item.data(0, Qt.UserRole)
        
        # Подсчитываем количество детей
        child_count = self._count_children(item)
        
        # Проверяем наличие транзакций
        transactions = self.db.get_transactions(filters={'category_id': category_id})
        transaction_count = len(transactions)
        
        # Формируем сообщение подтверждения
        confirm_msg = f"Вы уверены, что хотите удалить категорию '{category_name}'?"
        
        if child_count > 0:
            confirm_msg += f"\n\n⚠️ Внимание! Будут также удалены {child_count} подкатегорий."
        
        if transaction_count > 0:
            confirm_msg += f"\n\n⚠️ В этой категории есть {transaction_count} транзакций. "
            confirm_msg += "Они будут переведены в категорию 'Без категории'."
        
        reply = QMessageBox.question(self, "Подтверждение удаления", confirm_msg,
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.No:
            return
        
        # Удаляем категорию
        result = self.db.delete_category(category_id, delete_children=True)
        
        if result['success']:
            self.show_status_message(f"✅ {result['message']}", "success")
            self.load_categories_into_tree()
            self._reset_form_state()
            self.data_updated.emit()
        else:
            self.show_status_message(f"❌ {result['message']}", "error")
    
    def _count_children(self, item):
        """Рекурсивно подсчитывает количество детей элемента"""
        count = item.childCount()
        for i in range(item.childCount()):
            count += self._count_children(item.child(i))
        return count
    
    def _analyze_category(self):
        """Показывает статистику по выбранной категории"""
        selected_items = self.categories_tree.selectedItems()
        if not selected_items:
            self.show_status_message("⚠️ Выберите категорию для просмотра статистики", "warning")
            return
        
        category_id = selected_items[0].data(0, Qt.UserRole)
        category_name = selected_items[0].text(0)
        
        transactions = self.db.get_transactions(filters={'category_id': category_id})
        
        if not transactions:
            self.show_status_message(f"📊 В категории '{category_name}' нет транзакций", "info")
            return
        
        total_income = 0
        total_expense = 0
        transaction_count = len(transactions)
        
        for trans in transactions:
            amount = trans['amount']
            trans_type = trans['type']
            
            if trans_type == 'income':
                total_income += amount
            else:
                total_expense += abs(amount)
        
        # Создаем диалог со статистикой
        stats_dialog = QDialog(self)
        stats_dialog.setWindowTitle(f"Статистика: {category_name}")
        stats_dialog.resize(400, 250)
        
        layout = QVBoxLayout()
        
        stats_text = f"📊 Статистика категории: {category_name}\n\n"
        stats_text += f"📋 Количество операций: {transaction_count}\n"
        stats_text += f"💰 Общий доход: {total_income:.2f} ₽\n"
        stats_text += f"💸 Общий расход: {total_expense:.2f} ₽\n"
        
        if total_income > 0 or total_expense > 0:
            net_flow = total_income - total_expense
            stats_text += f"📈 Чистый поток: {net_flow:.2f} ₽\n"
        
        stats_label = QLabel(stats_text)
        stats_label.setAlignment(Qt.AlignLeft)
        stats_label.setStyleSheet("font-size: 12px; padding: 10px;")
        layout.addWidget(stats_label)
        
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(stats_dialog.accept)
        layout.addWidget(close_button)
        
        stats_dialog.setLayout(layout)
        stats_dialog.exec()
    
    def _reset_form_state(self):
        """Сбрасывает поля формы и состояние кнопок"""
        self.name_input.clear()
        self.type_combo.setCurrentIndex(0)  # expense
        self.parent_combo.setCurrentIndex(0)  # пусто
        self.budget_input.setText("0.0")
        self.editing_category_id = None
        self.edit_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        # Сбрасываем current_parent_id при сбросе формы
        self.current_parent_id = None
    
    def show_status_message(self, message, message_type="info"):
        """Показывает сообщение в статусе родительского окна"""
        if hasattr(self.parent, 'show_status_message'):
            self.parent.show_status_message(message, 3000)
        else:
            print(f"STATUS [{message_type}]: {message}")
    
    def on_close(self):
        """Закрывает диалоговое окно"""
        self.data_updated.emit()
        self.accept()