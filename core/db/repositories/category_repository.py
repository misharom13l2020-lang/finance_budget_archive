"""
Репозиторий для работы с категориями (categories).
Работает с dataclass-моделями вместо словарей.
"""

import logging
from typing import List, Dict, Any, Optional
from core.db.repositories.base import BaseRepository
from core.db.models import Category
from core.db.interfaces import QueryExecutor

logger = logging.getLogger(__name__)


class CategoryRepository(BaseRepository[Category]):
    """Репозиторий для работы с категориями."""
    
    def _get_table_name(self) -> str:
        return "categories"
    
    def _get_model_class(self) -> type[Category]:
        return Category
    
    def get_categories(self, type: str = None, include_system: bool = False,
                      include_subcategories: bool = True) -> List[Category]:
        """Получение всех категорий."""
        sql = '''
            SELECT id, name, type, budget_amount_monthly,
                   parent_id, color, icon, is_system, created_at
            FROM categories
            WHERE 1=1
        '''
        
        params = []
        if type:
            sql += " AND type = ?"
            params.append(type)
        
        if not include_system:
            sql += " AND is_system = 0"
        
        if not include_subcategories:
            sql += " AND parent_id IS NULL"
        
        sql += " ORDER BY type, parent_id, name"
        rows = self.executor.fetch_all(sql, tuple(params))
        return [self._to_model(row) for row in rows]
    
    def get_category_by_name(self, name: str) -> Optional[Category]:
        """Получение категории по имени."""
        sql = '''
            SELECT id, name, type, budget_amount_monthly,
                   parent_id, color, icon, is_system, created_at
            FROM categories
            WHERE name = ?
        '''
        row = self.executor.fetch_one(sql, (name,))
        if row is None:
            return None
        return self._to_model(row)
    
    def get_category_hierarchy(self, type: str = None) -> List[Dict[str, Any]]:
        """Получение иерархии категорий."""
        sql = '''
            WITH RECURSIVE category_hierarchy AS (
                SELECT 
                    id,
                    name,
                    type,
                    budget_amount_monthly,
                    parent_id,
                    color,
                    icon,
                    is_system,
                    created_at,
                    0 as level,
                    name as path
                FROM categories
                WHERE parent_id IS NULL
                
                UNION ALL
                
                SELECT 
                    c.id,
                    c.name,
                    c.type,
                    c.budget_amount_monthly,
                    c.parent_id,
                    c.color,
                    c.icon,
                    c.is_system,
                    c.created_at,
                    ch.level + 1 as level,
                    ch.path || ' > ' || c.name as path
                FROM categories c
                JOIN category_hierarchy ch ON c.parent_id = ch.id
            )
            SELECT 
                id,
                name,
                type,
                budget_amount_monthly,
                parent_id,
                color,
                icon,
                is_system,
                created_at,
                level,
                path
            FROM category_hierarchy
            WHERE 1=1
        '''
        
        params = []
        if type:
            sql += " AND type = ?"
            params.append(type)
        
        sql += " ORDER BY type, level, path"
        return self.executor.fetch_all(sql, tuple(params))
    
    def get_categories_for_display(self, type: str = None) -> List[Dict[str, Any]]:
        """Получение категорий для отображения в UI (с отступами)."""
        hierarchy = self.get_category_hierarchy(type)
        
        result = []
        for cat in hierarchy:
            indent = "    " * cat['level']
            result.append({
                'id': cat['id'],
                'display_name': f"{indent}{cat['name']}",
                'name': cat['name'],
                'type': cat['type'],
                'level': cat['level'],
                'color': cat['color'],
                'icon': cat['icon']
            })
        
        return result
    
    def delete_category_with_checks(self, category_id: int, delete_children: bool = False) -> Dict[str, Any]:
        """
        Удаление категории с проверками.
        
        Args:
            category_id: ID категории.
            delete_children: Если True, удаляет все подкатегории.
            
        Returns:
            Словарь с результатом операции.
        """
        try:
            category = self.get_by_id(category_id)
            if not category:
                return {
                    'success': False,
                    'message': f"Категория с ID {category_id} не найдена"
                }
            
            if category.is_system:
                return {
                    'success': False,
                    'message': "Нельзя удалить системную категорию"
                }
            
            category_name = category.name
            
            if delete_children:
                # Удаляем категорию и все подкатегории
                sql = '''
                    WITH RECURSIVE category_tree AS (
                        SELECT id FROM categories WHERE id = ?
                        UNION ALL
                        SELECT c.id FROM categories c
                        JOIN category_tree ct ON c.parent_id = ct.id
                    )
                    DELETE FROM categories WHERE id IN (SELECT id FROM category_tree)
                '''
                self.executor.execute(sql, (category_id,))
                
                # Обнуляем category_id в транзакциях
                sql = '''
                    WITH RECURSIVE category_tree AS (
                        SELECT id FROM categories WHERE id = ?
                        UNION ALL
                        SELECT c.id FROM categories c
                        JOIN category_tree ct ON c.parent_id = ct.id
                    )
                    UPDATE transactions 
                    SET category_id = NULL 
                    WHERE category_id IN (SELECT id FROM category_tree)
                '''
                self.executor.execute(sql, (category_id,))
                
                logger.info(f"Удалена категория с подкатегориями: {category_name}")
                
            else:
                # Делаем подкатегории основными
                sql = "UPDATE categories SET parent_id = NULL WHERE parent_id = ?"
                self.executor.execute(sql, (category_id,))
                
                # Обнуляем category_id в транзакциях
                sql = "UPDATE transactions SET category_id = NULL WHERE category_id = ?"
                self.executor.execute(sql, (category_id,))
                
                # Удаляем саму категорию
                sql = "DELETE FROM categories WHERE id = ?"
                self.executor.execute(sql, (category_id,))
                
                logger.info(f"Удалена категория: {category_name}")
            
            return {
                'success': True,
                'message': f"Категория '{category_name}' успешно удалена"
            }
            
        except Exception as e:
            logger.error(f"Ошибка при удалении категории: {e}")
            return {
                'success': False,
                'message': f"Ошибка при удалении категории: {str(e)}"
            }