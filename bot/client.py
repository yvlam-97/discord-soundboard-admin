"""
Main Discord bot client.
"""

import importlib
import pathlib
from typing import TYPE_CHECKING

import discord
from discord import app_commands

from core.events import EventBus, EventType, SystemEvent

if TYPE_CHECKING:
    from core.config import Config
    from repositories import SoundRepository, ConfigRepository


class SjefBot(discord.Client):
    """
    Main Discord bot client with dependency injection.

    This client manages:
    - Command loading and registration
    - Service lifecycle (soundboard, notifications)
    - Event bus integration
    """

    def __init__(
        self,
        config: "Config",
        event_bus: EventBus,
        sound_repository: "SoundRepository",
        config_repository: "ConfigRepository",
        *,
        intents: discord.Intents,
    ):
        """
        Initialize the bot client.

        Args:
            config: Application configuration
            event_bus: Event bus for pub/sub
            sound_repository: Repository for sound operations
            config_repository: Repository for config operations
            intents: Discord intents
        """
        super().__init__(intents=intents)

        self.config = config
        self.event_bus = event_bus
        self.sound_repository = sound_repository
        self.config_repository = config_repository

        self.tree = app_commands.CommandTree(self)
        self._services: list = []

    def register_service(self, service) -> None:
        """
        Register a service to be started when the bot is ready.

        Services should have a start() method that returns an awaitable.

        Args:
            service: Service instance with start() method
        """
        self._services.append(service)

    async def setup_hook(self) -> None:
        """
        Called when the bot is starting up.

        This loads commands and prepares the bot.
        """
        await self._load_commands()

    async def on_ready(self) -> None:
        """
        Called when the bot has connected to Discord.

        This starts all registered services and publishes the BOT_READY event.
        """
        print(f"[Bot] Logged in as {self.user}")

        # Sync commands with guild
        guild = discord.Object(id=self.config.guild_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print(f"[Bot] Commands synced to guild {self.config.guild_id}")

        # Start all services
        for service in self._services:
            await service.start()
            print(f"[Bot] Started service: {service.__class__.__name__}")

        # Publish ready event
        await self.event_bus.publish(SystemEvent(event_type=EventType.BOT_READY))

    async def close(self) -> None:
        """Clean up when the bot is shutting down."""
        # Publish shutdown event
        await self.event_bus.publish(SystemEvent(event_type=EventType.SHUTDOWN))

        # Stop all services
        for service in self._services:
            if hasattr(service, "stop"):
                await service.stop()
                print(f"[Bot] Stopped service: {service.__class__.__name__}")

        await super().close()

    async def _load_commands(self) -> None:
        """Load all commands from the commands directory."""
        commands_path = pathlib.Path(__file__).parent.parent / "commands"

        if not commands_path.exists():
            print(f"[Bot] Commands directory not found: {commands_path}")
            return

        for file in commands_path.glob("*.py"):
            if file.name.startswith("_"):
                continue

            mod_name = f"commands.{file.stem}"
            try:
                mod = importlib.import_module(mod_name)

                for obj in vars(mod).values():
                    if isinstance(obj, app_commands.Command):
                        self.tree.add_command(
                            obj,
                            guild=discord.Object(id=self.config.guild_id)
                        )
                        print(f"[Bot] Loaded command: {obj.name}")

            except Exception as e:
                print(f"[Bot] Failed to load command module {mod_name}: {e}")
