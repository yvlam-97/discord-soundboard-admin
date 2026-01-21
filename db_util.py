# No changes needed; utility only
import os
import sqlite3
import shutil

def ensure_valid_sqlite_db(db_path):
    """
    If db_path is not a valid SQLite database, back it up and create a new one.
    """
    if not os.path.exists(db_path):
        return
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute("SELECT name FROM sqlite_master LIMIT 1;")
    except sqlite3.DatabaseError:
        # Backup the invalid/corrupt file
        backup_path = db_path + ".bak"
        shutil.move(db_path, backup_path)
        print(f"[DB] Backed up invalid DB to {backup_path} and will create a new one.")

def ensure_tables_exist(db_path):
    """
    Ensure all required tables exist in the database. Safe to call at any time.
    """
    with sqlite3.connect(db_path) as conn:
        # Sounds table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS sounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE,
            data BLOB
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
        # Soundboard events table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS soundboard_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            filename TEXT NOT NULL,
            extra TEXT
        )
        """)
