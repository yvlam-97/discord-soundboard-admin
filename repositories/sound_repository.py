"""
Repository for sound file operations.
"""

import time
from dataclasses import dataclass
from typing import Optional

from .base import DatabaseManager


@dataclass
class Sound:
    """Represents a sound file in the database."""
    id: int
    filename: str
    data: bytes
    created_at: int | None = None


class SoundRepository:
    """
    Repository for managing sound files in the database.

    Provides CRUD operations for sound files with clean separation
    from business logic.
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize the repository.

        Args:
            db_manager: Database manager for connections
        """
        self._db = db_manager

    def get_all_filenames(self) -> list[str]:
        """
        Get all sound filenames.

        Returns:
            List of all sound filenames
        """
        with self._db.connection() as conn:
            rows = conn.execute("SELECT filename FROM sounds ORDER BY filename").fetchall()
            return [row["filename"] for row in rows]

    def get_count(self) -> int:
        """
        Get the total number of sounds.

        Returns:
            Count of sounds in the database
        """
        with self._db.connection() as conn:
            row = conn.execute("SELECT COUNT(*) as count FROM sounds").fetchone()
            return row["count"]

    def get_random(self) -> Optional[Sound]:
        """
        Get a random sound from the database.

        Returns:
            Random Sound object or None if no sounds exist
        """
        with self._db.connection() as conn:
            row = conn.execute(
                "SELECT id, filename, data, created_at FROM sounds ORDER BY RANDOM() LIMIT 1"
            ).fetchone()

            if not row:
                return None

            return Sound(
                id=row["id"],
                filename=row["filename"],
                data=row["data"],
                created_at=row["created_at"]
            )

    def get_by_filename(self, filename: str) -> Optional[Sound]:
        """
        Get a sound by its filename.

        Args:
            filename: The filename to look up

        Returns:
            Sound object or None if not found
        """
        with self._db.connection() as conn:
            row = conn.execute(
                "SELECT id, filename, data, created_at FROM sounds WHERE filename = ?",
                (filename,)
            ).fetchone()

            if not row:
                return None

            return Sound(
                id=row["id"],
                filename=row["filename"],
                data=row["data"],
                created_at=row["created_at"]
            )

    def get_data_by_filename(self, filename: str) -> Optional[bytes]:
        """
        Get only the sound data by filename (more efficient than full Sound).

        Args:
            filename: The filename to look up

        Returns:
            Sound data bytes or None if not found
        """
        with self._db.connection() as conn:
            row = conn.execute(
                "SELECT data FROM sounds WHERE filename = ?",
                (filename,)
            ).fetchone()
            return row["data"] if row else None

    def exists(self, filename: str) -> bool:
        """
        Check if a sound with the given filename exists.

        Args:
            filename: The filename to check

        Returns:
            True if the sound exists
        """
        with self._db.connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM sounds WHERE filename = ?",
                (filename,)
            ).fetchone()
            return row is not None

    def create(self, filename: str, data: bytes) -> Sound:
        """
        Create a new sound.

        Args:
            filename: The filename for the sound
            data: The sound file data

        Returns:
            The created Sound object
        """
        with self._db.connection() as conn:
            timestamp = int(time.time())
            cursor = conn.execute(
                "INSERT INTO sounds (filename, data, created_at) VALUES (?, ?, ?)",
                (filename, data, timestamp)
            )
            self._log_event(conn, "upload", filename)

            return Sound(
                id=cursor.lastrowid,
                filename=filename,
                data=data,
                created_at=timestamp
            )

    def update_or_create(self, filename: str, data: bytes) -> Sound:
        """
        Update an existing sound or create a new one.

        Args:
            filename: The filename for the sound
            data: The sound file data

        Returns:
            The created/updated Sound object
        """
        with self._db.connection() as conn:
            timestamp = int(time.time())
            conn.execute(
                "INSERT OR REPLACE INTO sounds (filename, data, created_at) VALUES (?, ?, ?)",
                (filename, data, timestamp)
            )
            self._log_event(conn, "upload", filename)

            # Fetch the ID
            row = conn.execute(
                "SELECT id FROM sounds WHERE filename = ?",
                (filename,)
            ).fetchone()

            return Sound(
                id=row["id"],
                filename=filename,
                data=data,
                created_at=timestamp
            )

    def rename(self, old_filename: str, new_filename: str) -> bool:
        """
        Rename a sound file.

        Args:
            old_filename: Current filename
            new_filename: New filename

        Returns:
            True if successful, False if sound not found
        """
        with self._db.connection() as conn:
            cursor = conn.execute(
                "UPDATE sounds SET filename = ? WHERE filename = ?",
                (new_filename, old_filename)
            )

            if cursor.rowcount > 0:
                self._log_event(conn, "rename", old_filename, new_filename)
                return True
            return False

    def delete(self, filename: str) -> bool:
        """
        Delete a sound by filename.

        Args:
            filename: The filename to delete

        Returns:
            True if deleted, False if not found
        """
        with self._db.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM sounds WHERE filename = ?",
                (filename,)
            )

            if cursor.rowcount > 0:
                self._log_event(conn, "delete", filename)
                return True
            return False

    def _log_event(
        self,
        conn,
        event_type: str,
        filename: str,
        extra: str | None = None
    ) -> None:
        """Log an event to the soundboard_events table."""
        conn.execute(
            "INSERT INTO soundboard_events (timestamp, event_type, filename, extra) VALUES (?, ?, ?, ?)",
            (int(time.time()), event_type, filename, extra)
        )
