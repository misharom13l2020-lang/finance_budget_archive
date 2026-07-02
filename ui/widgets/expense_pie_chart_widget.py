# ui/widgets/expense_pie_chart_widget.py - Виджет круговой диаграммы расходов
from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
                               QComboBox, QPushButton, QWidget, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patheffects as path_effects
from datetime import datetime, timedelta
import numpy as np


class ExpensePieChartWidget(QFrame):
    """Виджет для отображения круговой диаграммы расходов по категориям."""
    
    # Сигнал для уведомления об обновлении данных
    data_updated = Signal()
    
    def __init__(self, parent=None, db_manager=None):
        super().__init__(parent)
        self.db = db_manager  # Менеджер базы данных
        self.figure = None    # Объект Figure из matplotlib
        self.canvas = None    # Canvas для отрисовки
        self.ax = None        # Оси для графика
        
        self.setup_ui()
        self.setup_connections()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
    def setup_ui(self):
        """Настраивает интерфейс виджета."""
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setLineWidth(1)
        
        # Основной layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Заголовок и элементы управления
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Заголовок
        title_label = QLabel("📊 Расходы по категориям")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        # Растягивающийся разделитель
        header_layout.addStretch()
        
        # Период
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Текущий месяц", "Прошлый месяц", "Текущий год", "Все время"])
        self.period_combo.setFixedWidth(150)
        header_layout.addWidget(self.period_combo)
        
        # Кнопка обновления
        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.setFixedWidth(80)
        header_layout.addWidget(self.refresh_btn)
        
        main_layout.addWidget(header_widget)
        
        # Layout для диаграммы
        self.chart_layout = QVBoxLayout()
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addLayout(self.chart_layout, 1)
        
        # Инициализируем matplotlib
        self.figure = None
        self.canvas = None
        self.ax = None
        
        # Обновляем диаграмму
        self.update_chart()
    
    def setup_connections(self):
        """Настройка сигналов и слотов."""
        # Изменение периода → обновление диаграммы
        self.period_combo.currentTextChanged.connect(self.update_chart)
        
        # Кнопка обновления → обновление диаграммы
        self.refresh_btn.clicked.connect(self.update_chart)
        
        # Автоматическое обновление при изменении данных в БД
        if self.db:
            self.db.data_updated.connect(self.schedule_update)
            
        # Таймер для отложенного обновления
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.update_chart)
    
    def schedule_update(self, data_type=None):
        """Планирует отложенное обновление диаграммы."""
        if data_type in [None, 'transactions', 'categories']:
            self.update_timer.start(500)  # Обновление через 500 мс
    
    def get_date_range(self):
        """Возвращает диапазон дат для выбранного периода."""
        today = datetime.now()
        period = self.period_combo.currentText()
        
        if period == "Текущий месяц":
            # С 1-го числа текущего месяца до конца месяца
            date_from = datetime(today.year, today.month, 1)
            date_to = (date_from.replace(month=date_from.month % 12 + 1, 
                     year=date_from.year + date_from.month // 12) - 
                     timedelta(days=1))
            
        elif period == "Прошлый месяц":
            # Весь предыдущий месяц
            prev_month = today.replace(day=1) - timedelta(days=1)
            date_from = prev_month.replace(day=1)
            date_to = prev_month
            
        elif period == "Текущий год":
            # С 1 января по 31 декабря текущего года
            date_from = datetime(today.year, 1, 1)
            date_to = datetime(today.year, 12, 31)
            
        else:  # "Все время"
            date_from = datetime(2000, 1, 1)  # Условная начальная дата
            date_to = datetime(2100, 12, 31)   # Условная конечная дата
        
        return date_from, date_to
    
    def clear_chart(self):
        """Очищает текущую диаграмму и все связанные виджеты."""
        try:
            # 1. Удаляем все виджеты из chart_layout
            self._clear_layout_widgets(self.chart_layout)
            
            # 2. Закрываем и освобождаем ресурсы matplotlib
            if self.figure:
                try:
                    plt.close(self.figure)
                except:
                    pass  # Игнорируем ошибки при закрытии
                
                # Сбрасываем ссылки для освобождения памяти
                self.figure = None
                self.ax = None
            
            # 3. Удаляем canvas если он еще существует
            if self.canvas:
                try:
                    self.canvas.setParent(None)
                    self.canvas.deleteLater()
                except:
                    pass
                finally:
                    self.canvas = None
            
            # 4. Принудительная сборка мусора для освобождения памяти
            import gc
            gc.collect()
            
        except Exception as e:
            print(f"[ExpensePieChartWidget] Ошибка при очистке диаграммы: {e}")
            import traceback
            traceback.print_exc()

    def _clear_layout_widgets(self, layout):
        """Рекурсивно удаляет все виджеты из layout."""
        if not layout:
            return
        
        try:
            # Идем в обратном порядке, чтобы избежать изменения индексов
            for i in reversed(range(layout.count())):
                item = layout.itemAt(i)
                
                if not item:
                    continue
                    
                if item.widget():
                    # Удаляем виджет
                    widget = item.widget()
                    try:
                        widget.setParent(None)
                        widget.deleteLater()
                    except:
                        pass
                        
                elif item.layout():
                    # Рекурсивно очищаем вложенный layout
                    self._clear_layout_widgets(item.layout())
                    
                    # Удаляем сам layout
                    sub_layout = item.layout()
                    try:
                        # Удаляем все элементы из sub_layout
                        while sub_layout.count():
                            sub_item = sub_layout.takeAt(0)
                            if sub_item.widget():
                                w = sub_item.widget()
                                w.setParent(None)
                                w.deleteLater()
                    except:
                        pass
                    
        except Exception as e:
            print(f"[ExpensePieChartWidget] Ошибка при очистке layout: {e}")
            
    def cleanup_resources(self):
        """Полная очистка всех ресурсов виджета."""
        # Останавливаем таймеры
        if hasattr(self, 'update_timer'):
            try:
                self.update_timer.stop()
                self.update_timer.deleteLater()
            except:
                pass
        
        # Отключаем сигналы от БД
        if self.db:
            try:
                self.db.data_updated.disconnect(self.schedule_update)
            except:
                pass
        
        # Очищаем диаграмму
        self.clear_chart()
        
        # Очищаем комбобоксы и другие виджеты
        if hasattr(self, 'period_combo'):
            try:
                self.period_combo.clear()
            except:
                pass
        
        print("[ExpensePieChartWidget] Ресурсы очищены")

    def closeEvent(self, event):
        """Обработчик закрытия виджета."""
        self.cleanup_resources()
        super().closeEvent(event)

    def get_expense_data_from_db(self):
        """Получает данные о расходах из базы данных."""
        try:
            # Получаем диапазон дат
            date_from, date_to = self.get_date_range()
            
            # Запрашиваем статистику по категориям
            stats = self.db.get_category_statistics(
                date_from=date_from.strftime('%Y-%m-%d'),
                date_to=date_to.strftime('%Y-%m-%d')
            )
            
            # Извлекаем только данные по расходам
            expense_data = []
            if 'expense_categories' in stats:
                for category in stats['expense_categories']:
                    amount = category.get('total_amount', 0)
                    if amount > 0:
                        expense_data.append({
                            'name': category.get('name', 'Без названия'),
                            'amount': amount,
                            'count': category.get('transaction_count', 0),
                            'color': category.get('color', '#3498db')
                        })
            
            return expense_data
            
        except Exception as e:
            print(f"Ошибка при получении данных из БД: {e}")
            return []
    
    def generate_colors(self, num_colors):
        """Генерирует цвета для категорий."""
        # Используем цветовую карту Set3 для приятных цветов
        cmap = plt.cm.Set3
        colors = [cmap(i % cmap.N) for i in range(num_colors)]
        
        # Если нужно больше цветов, добавляем из другой карты
        if num_colors > cmap.N:
            cmap2 = plt.cm.tab20c
            for i in range(num_colors - cmap.N):
                colors.append(cmap2(i % cmap2.N))
        
        return colors
    
    def update_chart(self):
        """Основной метод обновления диаграммы."""
        self.clear_chart()  # Очищаем предыдущий график
        
        try:
            # 1. Проверяем подключение к БД
            if not self.db:
                self.show_no_data_message("Нет подключения к БД")
                return
            
            # 2. Получаем данные о расходах
            expense_data = self.get_expense_data_from_db()
            
            # 3. Проверяем наличие данных
            if not expense_data:
                self.show_no_data_message("Нет данных по расходам за выбранный период")
                return
            
            # 4. Сортируем данные по сумме (от большего к меньшему)
            expense_data.sort(key=lambda x: x['amount'], reverse=True)
            
            # 5. Ограничиваем количество категорий (первые 8, остальные в "Прочие")
            max_categories = 8
            display_data = []
            
            if len(expense_data) <= max_categories:
                display_data = expense_data.copy()
            else:
                # Берем первые (max_categories-1) категорий
                display_data = expense_data[:max_categories-1]
                
                # Суммируем остальные в "Прочие"
                other_amount = sum(cat['amount'] for cat in expense_data[max_categories-1:])
                other_count = sum(cat['count'] for cat in expense_data[max_categories-1:])
                
                if other_amount > 0:
                    display_data.append({
                        'name': 'Прочие',
                        'amount': other_amount,
                        'count': other_count,
                        'color': '#95a5a6'
                    })
            
            # 6. Создаем фигуру и оси
            self.figure = Figure(figsize=(8, 6), dpi=80, facecolor='#f8f9fa')
            self.canvas = FigureCanvas(self.figure)
            self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.ax = self.figure.add_subplot(111)
            
            # Настраиваем отступы
            self.figure.subplots_adjust(left=0.05, right=0.75, top=0.85, bottom=0.05)
            
            # 7. Подготавливаем данные для диаграммы
            labels = [cat['name'] for cat in display_data]
            amounts = [cat['amount'] for cat in display_data]
            colors = [cat.get('color', '#3498db') for cat in display_data]
            
            # Если цвета не указаны, генерируем их
            if all(color == '#3498db' for color in colors):
                colors = self.generate_colors(len(display_data))
            
            total_amount = sum(amounts)
            
            # 8. Строим круговую диаграмму
            wedges, texts, autotexts = self.ax.pie(
                amounts,
                labels=labels,
                colors=colors,
                autopct=lambda pct: f'{pct:.1f}%' if pct >= 3 else '',
                startangle=90,
                wedgeprops={'edgecolor': 'white', 'linewidth': 1.5, 'width': 0.4},
                textprops={'fontsize': 9, 'fontweight': 'bold'},
                explode=[0.02] * len(amounts),  # Небольшое разделение секторов
                pctdistance=0.85,
                labeldistance=1.05
            )
            
            # 9. Настраиваем внешний вид текста
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_path_effects([
                    path_effects.withStroke(linewidth=2, foreground='black', alpha=0.5)
                ])
            
            for text in texts:
                text.set_fontsize(9)
            
            self.ax.axis('equal')  # Делаем диаграмму круглой
            
            # 10. Добавляем легенду с дополнительной информацией
            legend_labels = []
            for cat in display_data:
                percentage = (cat['amount'] / total_amount * 100) if total_amount > 0 else 0
                avg_amount = cat['amount'] / cat['count'] if cat['count'] > 0 else 0
                legend_labels.append(
                    f"{cat['name']}\n"
                    f"Сумма: {cat['amount']:,.0f} ₽\n"
                    f"Доля: {percentage:.1f}%\n"
                    f"Транзакций: {cat['count']}\n"
                    f"Среднее: {avg_amount:,.0f} ₽"
                )
            
            self.ax.legend(wedges, legend_labels,
                          title="Детализация расходов",
                          loc="center left",
                          bbox_to_anchor=(1, 0, 0.5, 1),
                          fontsize=8,
                          title_fontsize=9,
                          framealpha=0.9)
            
            # 11. Добавляем общую сумму в центр диаграммы
            center_text = f"Всего расходов:\n{total_amount:,.0f} ₽\n\n"
            center_text += f"Категорий: {len(expense_data)}\n"
            center_text += f"Период: {self.period_combo.currentText().lower()}"
            
            self.ax.text(0, 0, center_text,
                       ha='center', va='center',
                       fontsize=10, fontweight='bold',
                       color='#2c3e50',
                       bbox=dict(boxstyle="round,pad=0.6",
                                facecolor="white",
                                edgecolor="#3498db",
                                alpha=0.9))
            
            # 12. Добавляем заголовок
            self.ax.set_title("Распределение расходов по категориям", 
                            fontsize=12, fontweight='bold', pad=20)
            
            # 13. Отображаем диаграмму
            self.chart_layout.addWidget(self.canvas)
            self.canvas.draw()
            
            # 14. Уведомляем об обновлении
            self.data_updated.emit()
            
        except Exception as e:
            print(f"Ошибка при построении диаграммы: {e}")
            self.show_error_message(str(e))
    
    def show_no_data_message(self, message):
        """Отображает сообщение при отсутствии данных."""
        no_data_label = QLabel(message)
        no_data_label.setAlignment(Qt.AlignCenter)
        no_data_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                font-size: 14px;
                font-weight: 500;
                padding: 60px;
                background-color: #f8f9fa;
                border-radius: 8px;
                border: 2px dashed #bdc3c7;
            }
        """)
        self.chart_layout.addWidget(no_data_label)
    
    def show_error_message(self, error_text):
        """Отображает сообщение об ошибке."""
        error_label = QLabel(f"Ошибка загрузки данных:\n{error_text}")
        error_label.setAlignment(Qt.AlignCenter)
        error_label.setStyleSheet("""
            QLabel {
                color: #c0392b;
                font-size: 12px;
                font-weight: 500;
                padding: 40px;
                background-color: #fadbd8;
                border-radius: 8px;
                border: 1px solid #f1948a;
            }
        """)
        self.chart_layout.addWidget(error_label)
    
    def set_db_manager(self, db_manager):
        """Устанавливает менеджер базы данных для виджета."""
        self.db = db_manager
        if self.db:
            self.db.data_updated.connect(self.schedule_update)
        self.update_chart()
    
    def export_chart(self, filename="расходы_по_категориям.png"):
        """Экспортирует диаграмму в файл."""
        if self.figure:
            try:
                self.figure.savefig(filename, dpi=150, bbox_inches='tight')
                return True
            except Exception as e:
                print(f"Ошибка при экспорте диаграммы: {e}")
                return False
        return False