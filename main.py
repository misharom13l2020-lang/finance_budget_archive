# main.py
import sys
import os
from PySide6.QtWidgets import QApplication
from ui.windows.main_window import MainWindow
from ui.styles import apply_global_styles
from config import get_db_path  # <--- Импортируем нашу функцию

# Импорты для БД (оставь те, что используются у тебя сейчас)
# from core.database import DatabaseManager      # Старая
# from core.db.connection import SQLiteConnection # Новая

def main():
    app = QApplication(sys.argv)
    apply_global_styles(app)

    # === КЛЮЧЕВОЙ МОМЕНТ ===
    # Получаем правильный путь к БД (рядом с .exe)
    db_path = get_db_path()
    
    # Если у тебя в MainWindow или DatabaseManager есть возможность передать путь:
    # Вариант А: Если используешь старую архитектуру (Singleton)
    # from core.database import DatabaseManager
    # DatabaseManager.get_instance(db_path=db_path)
    
    # Вариант Б: Если используешь новую архитектуру
    # from core.db.connection import SQLiteConnection
    # db_conn = SQLiteConnection(db_path=db_path)

    # Создаем окно. 
    # Если MainWindow умеет принимать db_path или connection - передай его.
    # Если нет - он возьмет его сам через config.get_db_path(), который мы поправили в Шаге 1.
    window = MainWindow() 
    
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()