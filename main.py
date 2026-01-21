"""
SjefBot - Discord Soundboard Bot

Main entry point that wires together all components using dependency injection.
"""

import discord

from core.config import Config
from core.events import EventBus, set_event_bus
from repositories import DatabaseManager, SoundRepository, ConfigRepository
from bot import SjefBot
from services import SoundboardService, NotificationService, WebServerService


def create_intents() -> discord.Intents:
    """Create Discord intents for the bot."""
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True  # Required for channel cache and get_channel
    return intents


def main() -> None:
    """Main entry point for the bot."""
    # Load configuration
    config = Config.from_env()
    
    # Create event bus (singleton)
    event_bus = EventBus()
    set_event_bus(event_bus)
    
    # Create database manager and repositories
    db_manager = DatabaseManager(config.soundboard_db_path)
    sound_repository = SoundRepository(db_manager)
    config_repository = ConfigRepository(db_manager)
    
    # Create bot client
    intents = create_intents()
    bot = SjefBot(
        config=config,
        event_bus=event_bus,
        sound_repository=sound_repository,
        config_repository=config_repository,
        intents=intents,
    )
    
    # Create and register services
    soundboard_service = SoundboardService(
        client=bot,
        sound_repository=sound_repository,
        config_repository=config_repository,
        event_bus=event_bus,
    )
    bot.register_service(soundboard_service)
    
    if config.notify_channel_id:
        notification_service = NotificationService(
            client=bot,
            event_bus=event_bus,
            notify_channel_id=config.notify_channel_id,
        )
        bot.register_service(notification_service)
    
    # Create and register web server service (shares EventBus with bot)
    web_service = WebServerService(
        config=config,
        sound_repository=sound_repository,
        config_repository=config_repository,
        event_bus=event_bus,
        host=config.web_host,
        port=config.web_port,
    )
    bot.register_service(web_service)
    
    # Run the bot
    print("[Main] Starting SjefBot...")
    bot.run(config.discord_bot_token)


if __name__ == "__main__":
    main()