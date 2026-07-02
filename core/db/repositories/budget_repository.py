"""
Репозиторий для работы с бюджетами (budgets).
Работает с dataclass-моделями вместо словарей.
"""

import logging
from typing import List, Dict, Any, Optional
from core.db.repositories.base import BaseRepository
from core.db.models import Budget
from core.db.interfaces import QueryExecutor

logger = logging.getLogger(__name__)


class BudgetRepository(BaseRepository[Budget]):
    """Репозиторий для работы с бюджетами."""
    
    def _get_table_name(self) -> str:
        return "budgets"
    
    def _get_model_class(self) -> type[Budget]:
        return Budget
    
    def set_budget(self, category_id: int, month_year: str, amount: float) -> bool:
        """Установка бюджета на месяц."""
        try:
            sql = '''
                INSERT OR REPLACE INTO budgets 
                (category_id, month_year, planned_amount) 
                VALUES (?, ?, ?)
            '''
            
            success = self.executor.execute(sql, (category_id, month_year, amount))
            
            if success:
                logger.info(f"Установлен бюджет для категории {category_id} на {month_year}: {amount}")
            
            return bool(success)
            
        except Exception as e:
            logger.error(f"Ошибка при установке бюджета: {e}")
            return False
    
    def get_budgets(self, month_year: str = None) -> List[Dict[str, Any]]:
        """Получение бюджетов."""
        if month_year:
            sql = '''
                SELECT 
                    b.id, b.category_id, b.month_year, 
                    b.planned_amount, b.actual_amount, b.created_at,
                    c.name as category_name, c.type as category_type,
                    c.color as category_color
                FROM budgets b
                JOIN categories c ON b.category_id = c.id
                WHERE b.month_year = ?
                ORDER BY c.type, c.name
            '''
            return self.executor.fetch_all(sql, (month_year,))
        else:
            sql = '''
                SELECT 
                    b.id, b.category_id, b.month_year, 
                    b.planned_amount, b.actual_amount, b.created_at,
                    c.name as category_name, c.type as category_type,
                    c.color as category_color
                FROM budgets b
                JOIN categories c ON b.category_id = c.id
                ORDER BY b.month_year DESC, c.type, c.name
            '''
            return self.executor.fetch_all(sql)
    
    def get_budget_status(self, month_year: str) -> List[Dict[str, Any]]:
        """Получение статуса бюджетов на месяц."""
        sql = '''
            SELECT 
                b.category_id,
                c.name as category_name,
                c.type as category_type,
                b.planned_amount,
                COALESCE(SUM(CASE 
                    WHEN t.type = 'expense' THEN ABS(t.amount)
                    ELSE 0 
                END), 0) as actual_amount,
                c.color
            FROM budgets b
            JOIN categories c ON b.category_id = c.id
            LEFT JOIN transactions t ON t.category_id = c.id 
                AND t.type = 'expense'
                AND strftime('%Y-%m', t.date) = ?
            WHERE b.month_year = ?
            GROUP BY b.category_id, c.name, c.type, b.planned_amount, c.color
        '''
        
        return self.executor.fetch_all(sql, (month_year, month_year))
    
    def update_budget_actuals(self, month_year: str) -> bool:
        """Обновление фактических сумм в бюджетах."""
        try:
            sql = '''
                UPDATE budgets
                SET actual_amount = (
                    SELECT COALESCE(SUM(ABS(t.amount)), 0)
                    FROM transactions t
                    WHERE t.category_id = budgets.category_id
                      AND t.type = 'expense'
                      AND strftime('%Y-%m', t.date) = budgets.month_year
                )
                WHERE month_year = ?
            '''
            
            self.executor.execute(sql, (month_year,))
            
            logger.info(f"Обновлены фактические суммы бюджетов за {month_year}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении бюджетов: {e}")
            return False