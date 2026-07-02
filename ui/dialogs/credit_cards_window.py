# ui/dialogs/credit_cards_window.py
"""
Окно управления кредитными картами
Переведено на PySide6 с сохранением функциональности Tkinter версии
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTreeWidget, QTreeWidgetItem, QMessageBox, QGroupBox, QWidget,
    QTextEdit, QFormLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
from datetime import datetime, timedelta

from core.database import DatabaseManager
from ui.widgets.window_utils import center_window_relative



class CreditCardsWindow(QDialog):
    """Окно управления кредитными картами"""
    
    data_updated = Signal()
    
    def __init__(self, parent=None, db_manager=None):
        super().__init__(parent)
        self.parent = parent
        self.db = db_manager or DatabaseManager.get_instance()
        
        self.setWindowTitle("Кредитные карты")
        self.resize(900, 600)
        
        center_window_relative(self, parent)
        
        self.setup_ui()
        self._load_data()
        
    def setup_ui(self):
        """Создает интерфейс"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        
        # Общая сводка
        summary_group = QGroupBox("Общая сводка")
        summary_layout = QVBoxLayout()
        
        self.summary_label = QLabel()
        summary_font = QFont()
        summary_font.setPointSize(10)
        self.summary_label.setFont(summary_font)
        summary_layout.addWidget(self.summary_label)
        
        summary_group.setLayout(summary_layout)
        main_layout.addWidget(summary_group)
        
        # Таблица кредитных карт
        table_group = QGroupBox("Кредитные карты")
        table_layout = QVBoxLayout()
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([
            "Название", "Баланс", "Лимит", "Доступно", 
            "Использование", "День платежа", "Мин. платеж"
        ])
        
        # Настройка ширины колонок
        self.tree.setColumnWidth(0, 150)  # Название
        self.tree.setColumnWidth(1, 100)  # Баланс
        self.tree.setColumnWidth(2, 100)  # Лимит
        self.tree.setColumnWidth(3, 100)  # Доступно
        self.tree.setColumnWidth(4, 100)  # Использование
        self.tree.setColumnWidth(5, 100)  # День платежа
        self.tree.setColumnWidth(6, 120)  # Мин. платеж
        
        self.tree.setAlternatingRowColors(True)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        
        table_layout.addWidget(self.tree)
        table_group.setLayout(table_layout)
        main_layout.addWidget(table_group, 1)
        
        # Кнопки управления
        button_layout = QHBoxLayout()
        
        add_payment_button = QPushButton("Добавить платеж")
        add_payment_button.clicked.connect(self._add_payment)
        button_layout.addWidget(add_payment_button)
        
        refresh_button = QPushButton("Обновить")
        refresh_button.clicked.connect(self._load_data)
        button_layout.addWidget(refresh_button)
        
        check_overdue_button = QPushButton("Проверить просрочки")
        check_overdue_button.clicked.connect(self._check_overdue)
        button_layout.addWidget(check_overdue_button)
        
        button_layout.addStretch()
        
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
    def _load_data(self):
        """Загружает данные кредитных карт"""
        self.tree.clear()
        
        summary = self._get_all_credit_cards_summary()
        
        # Обновляем сводку
        summary_text = (
            f"Общий долг: {summary['total_debt']:,.2f} ₽ | "
            f"Общий лимит: {summary['total_credit_limit']:,.2f} ₽ | "
            f"Доступно: {summary['total_available_credit']:,.2f} ₽ | "
            f"Использование: {summary['total_utilization']:.1f}%"
        )
        self.summary_label.setText(summary_text)
        
        # Добавляем данные в таблицу
        for card in summary['cards']:
            item = QTreeWidgetItem(self.tree)
            item.setText(0, card['name'])
            item.setText(1, f"{card['current_balance']:,.2f} ₽")
            item.setText(2, f"{card['credit_limit']:,.2f} ₽")
            item.setText(3, f"{card['available_credit']:,.2f} ₽")
            item.setText(4, f"{card['utilization_percent']:.1f}%")
            item.setText(5, f"{card['payment_due_day']} число")
            item.setText(6, f"{card['min_payment_amount']:.2f} ₽ ({card['min_payment_percent']}%)")
            
            # Устанавливаем цвет в зависимости от баланса
            if card['current_balance'] < 0:
                item.setForeground(1, QColor("red"))
            elif card['current_balance'] > 0:
                item.setForeground(1, QColor("green"))
                
            # Цвет для процента использования
            if card['utilization_percent'] > 80:
                item.setForeground(4, QColor("red"))
            elif card['utilization_percent'] > 50:
                item.setForeground(4, QColor("orange"))
            else:
                item.setForeground(4, QColor("green"))
                
            item.setData(0, Qt.UserRole, card['id'])
    
    def _get_all_credit_cards_summary(self):
        """Получает сводку по всем кредитным картам через get_accounts()"""
        accounts = self.db.get_accounts(active_only=True)
        summaries = []
        total_debt = 0.0
        total_credit_limit = 0.0
        
        for account in accounts:
            try:
                if account['type'] != 'Credit Card':
                    continue
                
                account_id = account['id']
                name = account['name']
                current_balance = float(account['current_balance']) if account['current_balance'] is not None else 0.0
                credit_limit = float(account['credit_limit']) if account['credit_limit'] is not None else 0.0
                payment_due_day = account['payment_due_day'] if account['payment_due_day'] is not None else 1
                min_payment_percent = account['min_payment_percent'] if account['min_payment_percent'] is not None else 5.0
                last_payment_date = account.get('last_payment_date')
                
                available_credit = credit_limit + current_balance  # current_balance отрицательный для долга
                utilization_percent = (abs(current_balance) / credit_limit * 100) if credit_limit > 0 else 0
                min_payment_amount = abs(current_balance) * (min_payment_percent / 100)
                
                summary = {
                    'id': account_id,
                    'name': name,
                    'current_balance': current_balance,
                    'credit_limit': credit_limit,
                    'available_credit': available_credit,
                    'utilization_percent': utilization_percent,
                    'payment_due_day': payment_due_day,
                    'min_payment_amount': min_payment_amount,
                    'min_payment_percent': min_payment_percent,
                    'last_payment_date': last_payment_date
                }
                
                summaries.append(summary)
                total_debt += abs(current_balance)
                total_credit_limit += credit_limit
                
            except (ValueError, TypeError, KeyError) as e:
                print(f"DEBUG: Error processing account {account}: {e}")
                continue
        
        total_utilization = (total_debt / total_credit_limit * 100) if total_credit_limit > 0 else 0
        total_available_credit = total_credit_limit - total_debt
        
        return {
            'cards': summaries,
            'total_debt': total_debt,
            'total_credit_limit': total_credit_limit,
            'total_utilization': total_utilization,
            'total_available_credit': total_available_credit
        }
    
    def _on_selection_changed(self):
        """Обработчик изменения выбора в таблице"""
        selected_items = self.tree.selectedItems()
        # Можно активировать кнопки в зависимости от выбора
    
    def _add_payment(self):
        """Добавляет платеж по кредитной карте"""
        selected_items = self.tree.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Платеж", "Выберите кредитную карту для внесения платежа.")
            return
        
        item = selected_items[0]
        card_name = item.text(0)
        card_id = item.data(0, Qt.UserRole)
        
        # Получаем текущие данные карты
        account = self.db.get_account_by_id(card_id)
        if not account:
            QMessageBox.critical(self, "Ошибка", "Не удалось получить данные карты.")
            return
        
        # Создаем диалог для ввода платежа
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Платеж по карте {card_name}")
        dialog.resize(350, 200)
        
        layout = QVBoxLayout()
        
        # Информация о карте
        current_balance = account['current_balance']
        min_payment_percent = account.get('min_payment_percent', 5.0)
        min_payment = abs(current_balance) * (min_payment_percent / 100)
        
        info_label = QLabel(f"💳 Карта: {card_name}\nТекущий долг: {abs(current_balance):,.2f} ₽\nМинимальный платеж: {min_payment:.2f} ₽")
        info_font = QFont()
        info_font.setBold(True)
        info_label.setFont(info_font)
        layout.addWidget(info_label)
        
        # Форма ввода
        form_layout = QFormLayout()
        
        self.payment_amount_input = QLineEdit()
        self.payment_amount_input.setPlaceholderText(f"Например: {min_payment:.2f}")
        form_layout.addRow("Сумма платежа:", self.payment_amount_input)
        
        self.payment_date_input = QLineEdit()
        self.payment_date_input.setText(datetime.now().strftime("%Y-%m-%d"))
        form_layout.addRow("Дата платежа:", self.payment_date_input)
        
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Например: Платеж по кредитной карте")
        form_layout.addRow("Описание:", self.description_input)
        
        layout.addLayout(form_layout)
        
        # Кнопки
        button_layout = QHBoxLayout()
        
        process_button = QPushButton("Внести платеж")
        process_button.clicked.connect(lambda: self._process_payment(dialog, card_id, account))
        button_layout.addWidget(process_button)
        
        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        
        dialog.exec()
    
    def _process_payment(self, dialog, card_id, account):
        """Обрабатывает внесение платежа"""
        amount_str = self.payment_amount_input.text().replace(',', '.').strip()
        date_str = self.payment_date_input.text().strip()
        description = self.description_input.text().strip()
        
        try:
            amount = float(amount_str)
            if amount <= 0:
                QMessageBox.critical(dialog, "Ошибка", "Сумма платежа должна быть положительной.")
                return
            
            # Проверяем формат даты
            datetime.strptime(date_str, "%Y-%m-%d")
            
            if amount > abs(account['current_balance']):
                if QMessageBox.question(dialog, "Подтверждение", 
                                       f"Сумма платежа ({amount:,.2f} ₽) превышает текущий долг ({abs(account['current_balance']):,.2f} ₽). Продолжить?") != QMessageBox.Yes:
                    return
            
            if self._record_payment(card_id, amount, date_str, description):
                QMessageBox.information(dialog, "Успех", f"Платеж на сумму {amount:,.2f} ₽ записан.")
                dialog.accept()
                self._load_data()
                self.data_updated.emit()
            else:
                QMessageBox.critical(dialog, "Ошибка", "Не удалось записать платеж.")
                
        except ValueError as e:
            QMessageBox.critical(dialog, "Ошибка", f"Некорректные данные: {e}")
    
    def _record_payment(self, account_id, amount, payment_date, description):
        """Записывает платеж по кредитной карте"""
        try:
            # Получаем категорию для кредитных платежей
            category = self.db.get_category_by_name("Кредитные платежи")
            if not category:
                # Создаем новую категорию
                category_id = self.db.add_category({
                    'name': 'Кредитные платежи',
                    'type': 'income',  # Платеж по кредиту - доход для счета
                    'budget_amount_monthly': 0.0,
                    'color': '#FF5733',
                    'icon': '💳'
                })
            else:
                category_id = category['id']
            
            # Получаем текущий счет
            account = self.db.get_account_by_id(account_id)
            if not account:
                return False
            
            # Создаем транзакцию платежа
            transaction_id = self.db.add_transaction({
                'date': payment_date,
                'amount': amount,  # Положительная сумма увеличивает баланс (уменьшает долг)
                'type': 'income',
                'category_id': category_id,
                'account_id': account_id,
                'description': description or f"Платеж по кредитной карте {account['name']}"
            })
            
            if transaction_id:
                # Обновляем дату последнего платежа
                self.db.update_account(account_id, {
                    'last_payment_date': payment_date
                })
                
                self.db.logger.info(f"Записан платеж по кредитной карте {account['name']}: {amount} ₽")
                return True
            
            return False
            
        except Exception as e:
            self.db.logger.error(f"Ошибка при записи платежа: {e}")
            return False
    
    def _check_overdue(self):
        """Проверяет просроченные платежи по кредитным картам"""
        today = datetime.now()
        accounts = self.db.get_accounts(active_only=True)
        overdue_cards = []
        
        for account in accounts:
            if account['type'] != 'Credit Card':
                continue
            
            current_balance = account.get('current_balance', 0.0)
            if current_balance >= 0:  # Нет долга
                continue
            
            payment_due_day = account.get('payment_due_day', 1)
            last_payment_date = account.get('last_payment_date')
            
            next_payment_date = self._calculate_next_payment_date(payment_due_day, last_payment_date)
            
            if today.date() > next_payment_date:
                min_payment_percent = account.get('min_payment_percent', 5.0)
                min_payment = abs(current_balance) * (min_payment_percent / 100)
                overdue_days = (today.date() - next_payment_date).days
                
                overdue_cards.append({
                    'name': account['name'],
                    'overdue_days': overdue_days,
                    'min_payment': min_payment,
                    'total_debt': abs(current_balance),
                    'next_payment_date': next_payment_date.strftime("%Y-%m-%d"),
                    'payment_due_day': payment_due_day
                })
        
        if not overdue_cards:
            QMessageBox.information(self, "Проверка", "Нет просроченных платежей по кредитным картам.")
            return
        
        # Создаем диалог для отображения просрочек
        dialog = QDialog(self)
        dialog.setWindowTitle("Просроченные платежи")
        dialog.resize(500, 400)
        
        layout = QVBoxLayout()
        
        # Текст с информацией о просрочках
        overdue_text = "📅 Просроченные платежи по кредитным картам:\n\n"
        
        total_overdue_min = sum(card['min_payment'] for card in overdue_cards)
        total_overdue_debt = sum(card['total_debt'] for card in overdue_cards)
        
        overdue_text += f"Общий минимальный платеж к оплате: {total_overdue_min:,.2f} ₽\n"
        overdue_text += f"Общая сумма долга: {total_overdue_debt:,.2f} ₽\n\n"
        overdue_text += "Детали по картам:\n"
        
        for card in overdue_cards:
            overdue_text += (
                f"\n💳 {card['name']}:\n"
                f"   📅 Дата платежа: {card['next_payment_date']} ({card['payment_due_day']} число)\n"
                f"   ⏰ Просрочено: {card['overdue_days']} дней\n"
                f"   💰 Минимальный платеж: {card['min_payment']:,.2f} ₽\n"
                f"   🏦 Общий долг: {card['total_debt']:,.2f} ₽\n"
            )
        
        text_edit = QTextEdit()
        text_edit.setPlainText(overdue_text)
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("Arial", 10))
        layout.addWidget(text_edit)
        
        # Кнопки
        button_layout = QHBoxLayout()
        
        add_all_button = QPushButton("Добавить платежи")
        add_all_button.clicked.connect(lambda: self._add_payments_for_overdue(overdue_cards, dialog))
        button_layout.addWidget(add_all_button)
        
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(dialog.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        
        dialog.exec()
    
    def _calculate_next_payment_date(self, due_day, last_payment_date):
        """Рассчитывает дату следующего платежа"""
        today = datetime.now()
        
        if last_payment_date:
            try:
                last_payment = datetime.strptime(last_payment_date, "%Y-%m-%d")
                if last_payment.month == today.month and last_payment.year == today.year:
                    # Платеж уже был в этом месяце, следующий - в следующем
                    next_date = today.replace(day=1) + timedelta(days=32)
                    next_date = next_date.replace(day=min(due_day, 28))
                    return next_date.date()
            except ValueError:
                pass
        
        # Рассчитываем следующий платеж на основе текущей даты
        if today.day > due_day:
            # Дата платежа уже прошла в этом месяце
            next_date = today.replace(day=1) + timedelta(days=32)
            try:
                next_date = next_date.replace(day=due_day)
            except ValueError:
                # Для месяцев с меньшим количеством дней
                next_date = next_date.replace(day=min(due_day, 28))
        else:
            # Дата платежа еще не наступила в этом месяце
            try:
                next_date = today.replace(day=due_day)
            except ValueError:
                # Для месяцев с меньшим количеством дней
                next_date = today.replace(day=1) + timedelta(days=32)
                next_date = next_date.replace(day=min(due_day, 28))
        
        return next_date.date()
    
    def _add_payments_for_overdue(self, overdue_cards, parent_dialog):
        """Добавляет платежи для всех просроченных карт"""
        for card in overdue_cards:
            # Находим ID карты по имени
            accounts = self.db.get_accounts()
            for account in accounts:
                if account['type'] == 'Credit Card' and account['name'] == card['name']:
                    # Добавляем минимальный платеж
                    today = datetime.now().strftime("%Y-%m-%d")
                    description = f"Платеж по просрочке ({card['overdue_days']} дней)"
                    
                    self._record_payment(
                        account['id'],
                        card['min_payment'],
                        today,
                        description
                    )
                    break
        
        QMessageBox.information(parent_dialog, "Успех", "Добавлены минимальные платежи для всех просроченных карт.")
        parent_dialog.accept()
        self._load_data()
        self.data_updated.emit()