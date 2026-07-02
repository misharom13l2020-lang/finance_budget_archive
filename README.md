# Finance Budget

> ⚠️ **ВНИМАНИЕ: Проект не поддерживается**  
> Данный репозиторий является **архивным**. Обновления, исправления ошибок и техническая поддержка не производятся.  
> Актуальная разработка ведётся в репозитории [**FinanceBudgetV3**](https://github.com/glybina18diver-lang/finance_budget_v3).

Программа на ПК для учёта личных финансов на Python + Tkinter/PySide6.  

---

## Статус проекта

| Параметр | Значение |
|----------|----------|
| **Статус** | Архив (не поддерживается) |
| **Обновления** | Не планируются |
| **Баг-репорты** | Не принимаются |
| **Pull requests** | Не принимаются |
| **Актуальная версия** | → [FinanceBudgetV3](https://github.com/misharom13l2020-lang/FinanceBudgetV3) |

> Этот репозиторий сохранён исключительно в ознакомительных и архивных целях.  
> Для использования актуальной версии приложения перейдите в репозиторий [**FinanceBudgetV3**](https://github.com/glybina18diver-lang/finance_budget_v3).

---

##  Версии

| Версия | Статус | Запуск | Бинарник |
|--------|--------|--------|----------|
| **v1** |  Архив | Только через CMD/PowerShell |  Нет |
| **v2** |  Архив | Двойной клик по .exe |  Есть |

 Все релизы: [Releases](https://github.com/glybina18diver-lang/finance_budget_archive/releases)

---

##  Возможности

- Учёт доходов и расходов
- Управление категориями операций
- Переводы между счетами
- Кредитные карты и займы (базовая логика)
- История операций
- Визуализация (графики доходов/расходов)

### Не реализовано / Отложено на V3
- Сверка балансов (модуль не работает)
- Полная логика расчёта процентов по кредитам
- Оптимизация архитектуры БД (сейчас монолитный `database.py`)

---

## Запуск

### Через Python (обе версии)

```bash
# 1. Клонируй репозиторий
git clone https://github.com/misharom13l2020-lang/finance_budget_archive.git
cd finance_budget_archive

# 2. Создай виртуальное окружение
python -m venv venv
venv\Scripts\activate

# 3. Установи зависимости
pip install -r requirements.txt

# 4. Запусти
python main.py
```

### Через .exe (только v2)

1. Скачай `FinanceBudgetV2.exe` из [Releases](https://github.com/glybina18diver-lang/finance_budget_archive/releases/tag/v2.5.2)
2. Запусти двойным кликом
3. База данных `budget.db` создастся автоматически в папке с программой

---

## Структура проекта (не полная)

```
.                       # Корень проекта
├── main.py             # Точка входа в приложение
├── config.py           # Конфигурация приложения
├── requirements.txt    # Зависимости
├── core/               # Ядро приложения
│   ├── database.py     # DatabaseManager (SQLite)
│   ├── models.py       # Модели данных
├── ui/                 # Пользовательский интерфейс
│   ├── windows/        # Главные окна
│   │   ├── main_window.py
│   │   └── dashboard.py
│   ├── dialogs/        # Диалоговые окна
│   │   ├── operations_dialog.py
│   │   ├── account_dialog.py
│   │   ├── category_dialog.py
│   │   ├── credit_cards_window.py
│   │   ├── loan_dialog.py
│   │   ├── transfer_dialog.py
│   │   └── reconciliation_dialog.py
│   ├── widgets/        # Виджеты
│   │   ├── expense_pie_chart_widget.py
│   │   ├── income_expense_chart.py
│   │   └── ...
│   └── styles/         # Стили QSS
├── services/           # Бизнес-логика
│   ├── budget_service.py
│   ├── report_service.py
│   └── transaction_service.py
├── utils/              # Утилиты
│   ├── converters.py
│   ├── formatters.py
│   └── validators.py

```

---

## Технологии

- **Python 3.14**
- **Tkinter/PySide6** — GUI
- **SQLite** — база данных
- **Matplotlib** — графики
- **PyInstaller** — сборка в .exe

---

## История версий

Подробный список изменений: [CHANGELOG.md](CHANGELOG.md)

---

##  Лицензия

MIT License - Только на V1 на V2
