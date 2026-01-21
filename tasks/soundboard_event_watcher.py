"""
DEPRECATED: This module is kept for backward compatibility.

The event watcher functionality has been moved to:
- services.notification_service.NotificationService

The new implementation uses an event-driven architecture (pub/sub) instead of 
polling the database, which is more efficient and provides instant notifications.

This file can be safely removed once all migrations are complete.
"""

import warnings

warnings.warn(
    "tasks.soundboard_event_watcher is deprecated. Use services.NotificationService instead.",
    DeprecationWarning,
    stacklevel=2
)


async def soundboard_event_watcher(client, notify_channel_id=None, db_path=None):
    """
    DEPRECATED: Use NotificationService instead.
    
    This function is kept for backward compatibility but will raise an error
    if called, as it requires the old architecture.
    """
    raise NotImplementedError(
        "soundboard_event_watcher is deprecated. "
        "Please use services.NotificationService with the new architecture."
    )
