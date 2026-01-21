"""
Base repository classes and database utilities.
"""

import os
import sqlite3
import shutil
from contextlib import contextmanager
from typing import Generator


class DatabaseManager:
    """
    Manages SQLite database connections and schema initialization.
    
    Provides thread-safe connection management and ensures
    the database schema is properly initialized.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize the database manager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self._db_path = db_path
        self._ensure_valid_database()
        self._ensure_schema()
    
    @property
    def db_path(self) -> str:
        """Get the database file path."""
        return self._db_path
    
    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Get a database connection as a context manager.
        
        Yields:
            SQLite connection that will be properly closed
        """
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _ensure_valid_database(self) -> None:
        """
        Ensure the database file is valid.
        
        If the file exists but is not a valid SQLite database,
        it will be backed up and a new one created.
        """
        if not os.path.exists(self._db_path):
            return
        
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("SELECT name FROM sqlite_master LIMIT 1;")
        except sqlite3.DatabaseError:
            backup_path = self._db_path + ".bak"
            shutil.move(self._db_path, backup_path)
            print(f"[DB] Backed up invalid DB to {backup_path} and will create a new one.")
    
    def _ensure_schema(self) -> None:
        """Create all required tables if they don't exist."""
        with self.connection() as conn:
            # Sounds table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sounds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT UNIQUE NOT NULL,
                    data BLOB NOT NULL,
                    created_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            # Interval config table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS interval_config (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    interval INTEGER NOT NULL
                )
            """)
            
            # Insert default interval if not present
            cur = conn.execute("SELECT interval FROM interval_config WHERE id = 1")
            if cur.fetchone() is None:
                conn.execute("INSERT INTO interval_config (id, interval) VALUES (1, 30)")
            
            # Soundboard events table (for audit log)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS soundboard_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    extra TEXT
                )
            """)
