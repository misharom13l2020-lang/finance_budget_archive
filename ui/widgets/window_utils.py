# ui/widgets/window_utils.py
"""
Утилиты для работы с окнами в PySide6
Включает центрирование окон с учетом панели задач
"""
import sys
from PySide6.QtCore import QRect, QPoint, Qt
from PySide6.QtWidgets import QApplication, QWidget
import ctypes
import ctypes.wintypes


def get_simple_taskbar_height():
    """
    Упрощенный метод определения высоты панели задач для Windows.
    Возвращает: высота панели задач в пикселях
    """
    try:
        # Для Windows
        if sys.platform == 'win32':
            # Получаем высоту экрана
            screen_height = ctypes.windll.user32.GetSystemMetrics(1)  # SM_CYSCREEN
            
            # Получаем рабочую область (без панели задач)
            class RECT(ctypes.Structure):
                _fields_ = [
                    ("left", ctypes.c_long),
                    ("top", ctypes.c_long),
                    ("right", ctypes.c_long),
                    ("bottom", ctypes.c_long)
                ]
            
            rect = RECT()
            # SPI_GETWORKAREA = 48
            success = ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0)
            
            if success:
                work_height = rect.bottom - rect.top
                taskbar_height = screen_height - work_height
                
                if 0 <= taskbar_height <= 100:
                    return taskbar_height
                else:
                    # Панель задач сверху или сбоку
                    return 40  # Значение по умолчанию
                    
        # Для Linux (используем фиксированные значения)
        elif sys.platform.startswith('linux'):
            # Обычные значения для GNOME/KDE
            return 40
            
        # Для macOS
        elif sys.platform == 'darwin':
            # Dock обычно 60-70px
            return 60
            
    except Exception as e:
        print(f"INFO: Не удалось определить высоту панели задач: {e}")
    
    # Значения по умолчанию в зависимости от разрешения экрана
    try:
        screen = QApplication.primaryScreen()
        if screen:
            screen_height = screen.geometry().height()
            
            if screen_height <= 768:
                return 30
            elif screen_height <= 1080:
                return 40
            elif screen_height <= 1440:
                return 45
            else:
                return 50
    except:
        pass
    
    return 40  # Значение по умолчанию


def center_window(window: QWidget, parent: QWidget = None, offset_y: int = 0):
    """
    Центрирует окно на экране с учетом панели задач.
    
    Args:
        window: Окно для центрирования
        parent: Родительское окно (если None - центрировать относительно экрана)
        offset_y: Смещение по Y (может быть отрицательным)
    """
    try:
        if not window.isVisible():
            window.show()
        
        # Обновляем геометрию окна
        window.updateGeometry()
        QApplication.processEvents()
        
        # Если есть родительское окно, центрируем относительно него
        if parent and parent.isVisible():
            return center_window_relative(window, parent, offset_y)
        
        # Получаем геометрию экрана
        screen = QApplication.primaryScreen()
        if not screen:
            return
            
        screen_geometry = screen.availableGeometry()  # Без панели задач!
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()
        
        # Получаем размеры окна
        window_width = window.width()
        window_height = window.height()
        
        # Проверяем корректность размеров
        if window_width <= 1 or window_height <= 1:
            # Берем размеры из sizeHint или устанавливаем по умолчанию
            size_hint = window.sizeHint()
            if size_hint.isValid():
                window_width = size_hint.width()
                window_height = size_hint.height()
            else:
                window_width = 800
                window_height = 600
            
            window.resize(window_width, window_height)
        
        # Ограничиваем размер окна, если оно слишком большое
        max_width = screen_width - 10
        max_height = screen_height - 10
        
        if window_width > max_width:
            window_width = max_width
        if window_height > max_height:
            window_height = max_height
        
        # Вычисляем позицию для центрирования
        x = screen_geometry.left() + (screen_width - window_width) // 2
        y = screen_geometry.top() + (screen_height - window_height) // 2 + offset_y - 15
        
        # Убеждаемся, что окно не выходит за границы экрана
        if y < screen_geometry.top():
            y = screen_geometry.top() + 20
        
        # Устанавливаем позицию
        window.move(x, y)
        
        # Поднимаем окно на передний план
        window.raise_()
        window.activateWindow()
        
        print(f"DEBUG центрирования: Окно {window_width}x{window_height} на позиции ({x}, {y})")
        
    except Exception as e:
        print(f"ERROR: Ошибка при центрировании окна '{window.windowTitle()}': {e}")
        # Просто центрируем без учета панели задач
        if parent and parent.isVisible():
            center_window_simple(window, parent)
        else:
            center_window_simple(window)


def center_window_relative(window: QWidget, parent: QWidget, offset_y: int = 0):
    """
    Центрирует дочернее окно относительно родительского.
    
    Args:
        window: Дочернее окно
        parent: Родительское окно
        offset_y: Вертикальное смещение
    """
    try:
        if not window.isVisible():
            window.show()
        
        window.updateGeometry()
        QApplication.processEvents()
        
        # Получаем геометрию родительского окна
        parent_geometry = parent.geometry()
        parent_x = parent_geometry.x()
        parent_y = parent_geometry.y()
        parent_width = parent_geometry.width()
        parent_height = parent_geometry.height()
        
        # Получаем размеры дочернего окна
        window_width = window.width()
        window_height = window.height()
        
        # Проверяем корректность размеров
        if window_width <= 1 or window_height <= 1:
            size_hint = window.sizeHint()
            if size_hint.isValid():
                window_width = size_hint.width()
                window_height = size_hint.height()
            else:
                window_width = 600
                window_height = 400
            
            window.resize(window_width, window_height)
        
        # Вычисляем позицию для центрирования относительно родителя
        x = parent_x + (parent_width - window_width) // 2
        y = parent_y + (parent_height - window_height) // 2 + offset_y-15
        
        # Убеждаемся, что окно не выходит за границы экрана
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            
            # Если окно выходит за правый край
            if x + window_width > screen_geometry.right():
                x = screen_geometry.right() - window_width - 20
            
            # Если окно выходит за нижний край
            if y + window_height > screen_geometry.bottom():
                y = screen_geometry.bottom() - window_height - 20
            
            # Если окно выходит за левый край
            if x < screen_geometry.left():
                x = screen_geometry.left() + 20
            
            # Если окно выходит за верхний край
            if y < screen_geometry.top():
                y = screen_geometry.top() + 20
        
        # Устанавливаем позицию
        window.move(x, y)
        
        # Поднимаем окно на передний план
        window.raise_()
        window.activateWindow()
        
        print(f"DEBUG относительного центрирования: Окно {window_width}x{window_height} относительно родителя")
        
    except Exception as e:
        print(f"ERROR: Ошибка при относительном центрировании: {e}")
        center_window_simple(window)


def center_window_simple(window: QWidget, parent: QWidget = None):
    """
    Простое центрирование окна (без учета панели задач).
    Используется как запасной вариант.
    """
    try:
        if not window.isVisible():
            window.show()
        
        window.updateGeometry()
        QApplication.processEvents()
        
        if parent and parent.isVisible():
            # Относительно родителя
            parent_geometry = parent.geometry()
            window_width = window.width()
            window_height = window.height()
            
            if window_width <= 1 or window_height <= 1:
                window_width = 600
                window_height = 400
                window.resize(window_width, window_height)
            
            x = parent_geometry.x() + (parent_geometry.width() - window_width) // 2
            y = parent_geometry.y() + (parent_geometry.height() - window_height) // 2
        else:
            # Относительно экрана
            screen = QApplication.primaryScreen()
            if screen:
                screen_geometry = screen.availableGeometry()
                window_width = window.width()
                window_height = window.height()
                
                if window_width <= 1 or window_height <= 1:
                    window_width = 800
                    window_height = 600
                    window.resize(window_width, window_height)
                
                x = screen_geometry.left() + (screen_geometry.width() - window_width) // 2
                y = screen_geometry.top() + (screen_geometry.height() - window_height) // 2
            else:
                return
        
        window.move(x, y)
        
    except Exception as e:
        print(f"ERROR: Ошибка при простом центрировании: {e}")


def ensure_window_on_screen(window: QWidget):
    """
    Гарантирует, что окно находится в пределах экрана.
    Если окно выходит за границы, перемещает его.
    """
    try:
        screen = QApplication.primaryScreen()
        if not screen:
            return
            
        screen_geometry = screen.availableGeometry()
        window_geometry = window.geometry()
        
        # Проверяем каждую сторону
        if window_geometry.left() < screen_geometry.left():
            window.move(screen_geometry.left(), window_geometry.top())
        
        if window_geometry.top() < screen_geometry.top():
            window.move(window_geometry.left(), screen_geometry.top())
        
        if window_geometry.right() > screen_geometry.right():
            window.move(screen_geometry.right() - window_geometry.width(), window_geometry.top())
        
        if window_geometry.bottom() > screen_geometry.bottom():
            window.move(window_geometry.left(), screen_geometry.bottom() - window_geometry.height())
            
    except Exception as e:
        print(f"ERROR: Ошибка при проверке положения окна: {e}")


def set_window_always_on_top(window: QWidget, always_on_top: bool = True):
    """
    Устанавливает окно поверх всех остальных.
    
    Args:
        window: Окно
        always_on_top: Если True - окно поверх всех
    """
    try:
        if always_on_top:
            window.setWindowFlags(window.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            window.setWindowFlags(window.windowFlags() & ~Qt.WindowStaysOnTopHint)
        
        window.show()  # Необходимо перепоказать окно после изменения флагов
        
    except Exception as e:
        print(f"ERROR: Ошибка при установке поверх всех окон: {e}")


def fade_in_window(window: QWidget, duration: int = 300):
    """
    Плавное появление окна (эффект fade-in).
    
    Args:
        window: Окно
        duration: Длительность анимации в мс
    """
    try:
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve
        
        window.setWindowOpacity(0)
        window.show()
        
        animation = QPropertyAnimation(window, b"windowOpacity")
        animation.setDuration(duration)
        animation.setStartValue(0)
        animation.setEndValue(1)
        animation.setEasingCurve(QEasingCurve.InOutQuad)
        animation.start()
        
    except Exception as e:
        print(f"INFO: Не удалось создать анимацию появления: {e}")
        window.show()


def fade_out_window(window: QWidget, duration: int = 300):
    """
    Плавное исчезновение окна (эффект fade-out).
    
    Args:
        window: Окно
        duration: Длительность анимации в мс
    """
    try:
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QTimer
        
        animation = QPropertyAnimation(window, b"windowOpacity")
        animation.setDuration(duration)
        animation.setStartValue(window.windowOpacity())
        animation.setEndValue(0)
        animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        # Закрываем окно после завершения анимации
        animation.finished.connect(window.close)
        animation.start()
        
    except Exception as e:
        print(f"INFO: Не удалось создать анимацию исчезновения: {e}")
        window.close()


# Декоратор для автоматического центрирования окон
def auto_center(method):
    """
    Декоратор для автоматического центрирования окон после их создания.
    
    Использование:
        @auto_center
        def create_window(self):
            window = QDialog(self)
            # настройка окна
            return window
    """
    def wrapper(*args, **kwargs):
        # Вызываем оригинальный метод
        window = method(*args, **kwargs)
        
        # Если метод вернул окно - центрируем его
        if isinstance(window, QWidget):
            # Ищем родительское окно среди аргументов
            parent = None
            for arg in args:
                if isinstance(arg, QWidget):
                    parent = arg
                    break
            
            if parent:
                center_window_relative(window, parent)
            else:
                center_window(window)
        
        return window
    
    return wrapper


# Пример использования
if __name__ == "__main__":
    # Тестирование функций
    app = QApplication([])
    
    # Создаем тестовое окно
    test_window = QWidget()
    test_window.setWindowTitle("Тест центрирования")
    test_window.resize(400, 300)
    
    # Центрируем на экране
    center_window(test_window)
    
    # Показываем
    test_window.show()
    
    # Создаем второе окно (дочернее)
    child_window = QWidget(test_window)
    child_window.setWindowTitle("Дочернее окно")
    child_window.resize(300, 200)
    
    # Центрируем относительно родителя
    center_window_relative(child_window, test_window, offset_y=-20)
    child_window.show()
    
    sys.exit(app.exec())