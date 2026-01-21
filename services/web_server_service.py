"""
Web server service that runs FastAPI within the bot process.

This ensures the EventBus is shared between web and bot,
enabling real-time notifications when sounds are changed.
"""

import asyncio
from typing import TYPE_CHECKING

import uvicorn

from core.config import Config
from core.events import EventBus
from repositories import SoundRepository, ConfigRepository
from web import create_web_app

if TYPE_CHECKING:
    from bot.client import SjefBot


class WebServerService:
    """
    Service that runs the FastAPI web server within the bot process.

    This is critical for the event-driven architecture to work:
    - Web app and bot share the same EventBus instance
    - Events published from web routes reach the NotificationService
    - No need for database polling or external message queues
    """

    def __init__(
        self,
        config: Config,
        sound_repository: SoundRepository,
        config_repository: ConfigRepository,
        event_bus: EventBus,
        host: str = "0.0.0.0",
        port: int = 8000,
    ):
        """
        Initialize the web server service.

        Args:
            config: Application configuration
            sound_repository: Repository for sound operations
            config_repository: Repository for config operations
            event_bus: Shared event bus instance
            host: Host to bind to
            port: Port to listen on
        """
        self._config = config
        self._sound_repo = sound_repository
        self._config_repo = config_repository
        self._event_bus = event_bus
        self._host = host
        self._port = port

        self._server: uvicorn.Server | None = None
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the web server in a background task."""
        # Create the FastAPI app with shared dependencies
        app = create_web_app(
            config=self._config,
            sound_repository=self._sound_repo,
            config_repository=self._config_repo,
            event_bus=self._event_bus,
        )

        # Configure uvicorn
        uvicorn_config = uvicorn.Config(
            app=app,
            host=self._host,
            port=self._port,
            log_level="info",
            loop="asyncio",
        )

        self._server = uvicorn.Server(uvicorn_config)

        # Run server in background task
        self._task = asyncio.create_task(self._server.serve())

        print(f"[WebServerService] Started on http://{self._host}:{self._port}")

    async def stop(self) -> None:
        """Stop the web server."""
        if self._server:
            self._server.should_exit = True

            if self._task:
                try:
                    await asyncio.wait_for(self._task, timeout=5.0)
                except asyncio.TimeoutError:
                    self._task.cancel()
                    try:
                        await self._task
                    except asyncio.CancelledError:
                        pass

        print("[WebServerService] Stopped")
