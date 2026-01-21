"""
DEPRECATED: This module is kept for backward compatibility.

All database logic has been moved to:
- repositories.base.DatabaseManager
- repositories.sound_repository.SoundRepository  
- repositories.config_repository.ConfigRepository

This file can be safely removed once all migrations are complete.
"""

# For backward compatibility, re-export from new location
from repositories.base import DatabaseManager


def ensure_valid_sqlite_db(db_path: str) -> None:
    """
    DEPRECATED: Use DatabaseManager instead.
    
    If db_path is not a valid SQLite database, back it up and create a new one.
    """
    import os
    import sqlite3
    import shutil
    
    if not os.path.exists(db_path):
        return
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute("SELECT name FROM sqlite_master LIMIT 1;")
    except sqlite3.DatabaseError:
        backup_path = db_path + ".bak"
        shutil.move(db_path, backup_path)
        print(f"[DB] Backed up invalid DB to {backup_path} and will create a new one.")


def ensure_tables_exist(db_path: str) -> None:
    """
    DEPRECATED: Use DatabaseManager instead.
    
    Ensure all required tables exist in the database.
    """
    # Just create a DatabaseManager which handles schema initialization
    _ = DatabaseManager(db_path)
