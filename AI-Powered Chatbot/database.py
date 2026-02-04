"""
Database module for AI-Powered Chatbot.
Handles SQLite database operations with thread-safe connection management.
Stores user messages and bot responses with timestamps.
"""

import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager


class ChatbotDatabase:
    """Thread-safe SQLite database handler for chatbot conversations."""
    
    def __init__(self, db_path: str = "chatbot.db"):
        """
        Initialize database connection with thread-local storage.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.local = threading.local()
        self.lock = threading.Lock()
        self._initialize_db()
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for thread-safe database connections.
        Yields a database connection and ensures proper cleanup.
        """
        if not hasattr(self.local, 'connection') or self.local.connection is None:
            self.local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=10.0
            )
            self.local.connection.row_factory = sqlite3.Row
        
        try:
            yield self.local.connection
        except sqlite3.Error as e:
            self.local.connection.rollback()
            raise e
    
    def _initialize_db(self):
        """Create conversation table if it doesn't exist."""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS conversations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_message TEXT NOT NULL,
                        bot_response TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        session_id TEXT
                    )
                ''')
                conn.commit()
    
    def save_conversation(self, user_message: str, bot_response: str, session_id: str = None):
        """
        Save user message and bot response to database.
        
        Args:
            user_message: User's input message
            bot_response: Bot's generated response
            session_id: Optional session identifier
            
        Returns:
            int: ID of inserted conversation record
        """
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO conversations (user_message, bot_response, session_id)
                    VALUES (?, ?, ?)
                ''', (user_message, bot_response, session_id))
                conn.commit()
                return cursor.lastrowid
    
    def get_conversation_history(self, limit: int = 10, session_id: str = None):
        """
        Retrieve conversation history from database.
        
        Args:
            limit: Maximum number of records to retrieve
            session_id: Optional session filter
            
        Returns:
            list: List of conversation records
        """
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if session_id:
                    cursor.execute('''
                        SELECT id, user_message, bot_response, timestamp
                        FROM conversations
                        WHERE session_id = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    ''', (session_id, limit))
                else:
                    cursor.execute('''
                        SELECT id, user_message, bot_response, timestamp
                        FROM conversations
                        ORDER BY timestamp DESC
                        LIMIT ?
                    ''', (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
    
    def get_total_conversations(self):
        """Get total number of stored conversations."""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) as count FROM conversations')
                result = cursor.fetchone()
                return result['count'] if result else 0
    
    def clear_old_conversations(self, days: int = 30):
        """
        Delete conversations older than specified days.
        
        Args:
            days: Number of days to keep
        """
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM conversations
                    WHERE datetime(timestamp) < datetime('now', ? || ' days')
                ''', (f'-{days}',))
                conn.commit()
                return cursor.rowcount
