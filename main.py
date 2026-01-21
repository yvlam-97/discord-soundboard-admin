
# Ensure the database is valid and all tables exist before anything else
import os
from db_util import ensure_valid_sqlite_db, ensure_tables_exist
import importlib
import pathlib
import os
from dotenv import load_dotenv
import discord
from discord import app_commands
from tasks.voice_soundboard import periodic_voice_task
from tasks.soundboard_event_watcher import soundboard_event_watcher
import asyncio

# Load environment variables from .env file
load_dotenv()

GUILD_ID = int(os.getenv('GUILD_ID'))
DB_PATH = os.getenv("SOUNDBOARD_DB_PATH", os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "soundboard.db")))
ensure_valid_sqlite_db(DB_PATH)
ensure_tables_exist(DB_PATH)

class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents, interval=30):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self._soundboard_interval = interval
        self._notify_channel_id = int(os.getenv("SOUNDBOARD_NOTIFY_CHANNEL_ID", "0"))
        self._event_watcher = None

    async def setup_hook(self):
        commands_path = pathlib.Path(__file__).parent / "commands"
        for file in commands_path.glob("*.py"):
            if file.name.startswith("_"):
                continue
            mod_name = f"commands.{file.stem}"
            mod = importlib.import_module(mod_name)
            for obj in vars(mod).values():
                if isinstance(obj, app_commands.Command):
                    self.tree.add_command(obj, guild=discord.Object(id=GUILD_ID))
        # Start the periodic voice task as a background task
        asyncio.create_task(periodic_voice_task(self, interval=self._soundboard_interval, db_path=DB_PATH))
        # Start the event watcher task (database-driven only)
        if self._notify_channel_id:
            asyncio.create_task(soundboard_event_watcher(self, self._notify_channel_id, db_path=DB_PATH))


intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True  # Required for channel cache and get_channel to work

try:
    interval = int(os.getenv('SOUNDBOARD_INTERVAL', '30'))
except ValueError:
    interval = 30

client = MyClient(intents=intents, interval=interval)

TOKEN = os.getenv('DISCORD_BOT_TOKEN')

if not TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN not set in environment. Please create a .env file.")

client.run(TOKEN)