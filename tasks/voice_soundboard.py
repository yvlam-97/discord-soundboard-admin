"""
DEPRECATED: This module is kept for backward compatibility.

The voice soundboard functionality has been moved to:
- services.soundboard_service.SoundboardService

The new implementation uses an event-driven architecture instead of 
polling the database, which is more efficient and responsive.

This file can be safely removed once all migrations are complete.
"""

import warnings

warnings.warn(
    "tasks.voice_soundboard is deprecated. Use services.SoundboardService instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export for backward compatibility (but this won't work with new architecture)
async def periodic_voice_task(client, interval=None, db_path=None):
    """
    DEPRECATED: Use SoundboardService instead.
    
    This function is kept for backward compatibility but will raise an error
    if called, as it requires the old architecture.
    """
    raise NotImplementedError(
        "periodic_voice_task is deprecated. "
        "Please use services.SoundboardService with the new architecture."
    )