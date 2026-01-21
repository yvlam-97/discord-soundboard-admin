"""
DEPRECATED: This module is kept for backward compatibility.

The web API functionality has been moved to:
- web.SoundboardWebApp
- web.create_web_app()

The new implementation uses:
- Repository pattern for clean data access
- Event-driven architecture for real-time updates
- Proper dependency injection

This file provides a compatibility layer for running the web server standalone.
"""

import warnings

warnings.warn(
    "soundboard_web is deprecated. Use web.create_web_app() instead.",
    DeprecationWarning,
    stacklevel=2
)

from core.config import Config
from core.events import EventBus
from repositories import DatabaseManager, SoundRepository, ConfigRepository
from web import create_web_app

# Create the app using the new architecture
config = Config.from_env()
event_bus = EventBus()
db_manager = DatabaseManager(config.soundboard_db_path)
sound_repository = SoundRepository(db_manager)
config_repository = ConfigRepository(db_manager)

app = create_web_app(
    config=config,
    sound_repository=sound_repository,
    config_repository=config_repository,
    event_bus=event_bus,
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    host = os.getenv("SOUNDBOARD_WEB_HOST", "127.0.0.1")
    port = int(os.getenv("SOUNDBOARD_WEB_PORT", 8080))
    uvicorn.run(app, host=host, port=port)
