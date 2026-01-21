"""
Application configuration management.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    discord_bot_token: str
    guild_id: int
    soundboard_db_path: str
    soundboard_interval: int
    notify_channel_id: int

    # Web server config
    web_root_path: str
    web_host: str
    web_port: int
    discord_client_id: str
    discord_client_secret: str
    discord_redirect_uri: str

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        load_dotenv()

        # Required
        token = os.getenv("DISCORD_BOT_TOKEN")
        if not token:
            raise ValueError("DISCORD_BOT_TOKEN not set in environment")

        guild_id_str = os.getenv("GUILD_ID")
        if not guild_id_str:
            raise ValueError("GUILD_ID not set in environment")

        # Optional with defaults
        db_path = os.getenv(
            "SOUNDBOARD_DB_PATH",
            os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "soundboard.db"))
        )

        try:
            interval = int(os.getenv("SOUNDBOARD_INTERVAL", "30"))
        except ValueError:
            interval = 30

        notify_channel_id = int(os.getenv("SOUNDBOARD_NOTIFY_CHANNEL_ID", "0"))

        # Web server config
        try:
            web_port = int(os.getenv("SOUNDBOARD_WEB_PORT", "8000"))
        except ValueError:
            web_port = 8000

        return cls(
            discord_bot_token=token,
            guild_id=int(guild_id_str),
            soundboard_db_path=db_path,
            soundboard_interval=interval,
            notify_channel_id=notify_channel_id,
            web_root_path=os.getenv("SOUNDBOARD_WEB_ROOT_PATH", ""),
            web_host=os.getenv("SOUNDBOARD_WEB_HOST", "0.0.0.0"),
            web_port=web_port,
            discord_client_id=os.getenv("DISCORD_CLIENT_ID", ""),
            discord_client_secret=os.getenv("DISCORD_CLIENT_SECRET", ""),
            discord_redirect_uri=os.getenv("DISCORD_REDIRECT_URI", ""),
        )
