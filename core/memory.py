"""Система памяти JARVIS - хранение истории диалогов и фактов о пользователе."""
import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, List, Dict


class MemorySystem:
    """Постоянная память на SQLite для истории и фактов."""
    
    def __init__(self, db_path: str = "db/history.db"):
        self.db_path = db_path
        self._ensure_db()
    
    def _ensure_db(self):
        """Создаёт базу данных и таблицы если их нет."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Таблица истории диалогов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL
                )
            """)
            
            # Таблица фактов о пользователе
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Индекс для быстрого поиска
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_timestamp 
                ON conversations(timestamp DESC)
            """)
            
            conn.commit()
    
    def add_message(self, role: str, content: str):
        """Добавляет сообщение в историю диалога."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO conversations (role, content) VALUES (?, ?)",
                (role, content)
            )
            conn.commit()
    
    def get_recent_history(self, limit: int = 10) -> List[Dict[str, str]]:
        """Загружает последние N сообщений истории."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT role, content 
                FROM conversations 
                ORDER BY timestamp DESC 
                LIMIT ?
                """,
                (limit,)
            )
            rows = cursor.fetchall()
            # Возвращаем в хронологическом порядке
            return [{"role": row[0], "content": row[1]} for row in reversed(rows)]
    
    def set_fact(self, key: str, value: str):
        """Сохраняет факт о пользователе."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO facts (key, value, timestamp) 
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, value))
            conn.commit()
    
    def get_fact(self, key: str) -> Optional[str]:
        """Получает факт о пользователе."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM facts WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else None
    
    def get_all_facts(self) -> Dict[str, str]:
        """Получает все факты о пользователе."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM facts")
            return {row[0]: row[1] for row in cursor.fetchall()}
    
    def delete_fact(self, key: str):
        """Удаляет факт."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM facts WHERE key = ?", (key,))
            conn.commit()
    
    def clear_old_history(self, days: int = 30):
        """Очищает историю старше N дней."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM conversations 
                WHERE timestamp < datetime('now', '-' || ? || ' days')
                """,
                (days,)
            )
            conn.commit()
    
    def get_context_summary(self) -> str:
        """Генерирует краткое резюме контекста для промпта."""
        facts = self.get_all_facts()
        if not facts:
            return ""
        
        summary = "Известные факты о пользователе:\n"
        for key, value in facts.items():
            summary += f"- {key}: {value}\n"
        return summary


# Глобальный экземпляр памяти
_memory_instance: Optional[MemorySystem] = None


def get_memory() -> MemorySystem:
    """Возвращает глобальный экземпляр системы памяти."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = MemorySystem()
    return _memory_instance
