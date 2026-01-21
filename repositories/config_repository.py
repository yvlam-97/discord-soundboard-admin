"""
Repository for configuration settings.
"""

import time
from .base import DatabaseManager


class ConfigRepository:
    """
    Repository for managing application configuration in the database.
    
    Currently manages:
    - Playback interval settings
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize the repository.
        
        Args:
            db_manager: Database manager for connections
        """
        self._db = db_manager
    
    def get_interval(self) -> int:
        """
        Get the current playback interval.
        
        Returns:
            Interval in seconds (default: 30)
        """
        with self._db.connection() as conn:
            row = conn.execute(
                "SELECT interval FROM interval_config WHERE id = 1"
            ).fetchone()
            return row["interval"] if row else 30
    
    def set_interval(self, interval: int) -> int:
        """
        Set the playback interval.
        
        Args:
            interval: New interval in seconds
            
        Returns:
            The old interval value
        """
        with self._db.connection() as conn:
            # Get old value
            old_row = conn.execute(
                "SELECT interval FROM interval_config WHERE id = 1"
            ).fetchone()
            old_value = old_row["interval"] if old_row else 30
            
            # Update
            conn.execute(
                "UPDATE interval_config SET interval = ? WHERE id = 1",
                (interval,)
            )
            
            # Log event
            conn.execute(
                "INSERT INTO soundboard_events (timestamp, event_type, filename, extra) VALUES (?, ?, ?, ?)",
                (int(time.time()), "interval_change", str(interval), str(old_value))
            )
            
            return old_value
