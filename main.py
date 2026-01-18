import os
from dotenv import load_dotenv
import discord
from discord import app_commands

# Load environment variables from .env file
load_dotenv()

GUILD_ID = int(os.getenv('GUILD_ID'))


from tasks.voice_soundboard import periodic_voice_task

class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents, interval=30):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self._soundboard_interval = interval

    async def setup_hook(self):
        # Dynamically import and add commands from the commands/ directory
        import importlib
        import pathlib
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
        import asyncio
        asyncio.create_task(periodic_voice_task(self, interval=self._soundboard_interval))

    async def on_ready(self):
        print(f'Logged on as {self.user}!')
        try:
            # Sync only to the test guild for instant update
            guild = discord.Object(id=GUILD_ID)
            synced = await self.tree.sync(guild=guild)
            print(f'Synced {len(synced)} command(s) to guild {GUILD_ID}')
        except Exception as e:
            print(f'Error syncing commands: {e}')


intents = discord.Intents.default()
intents.message_content = True

try:
    interval = int(os.getenv('SOUNDBOARD_INTERVAL', '30'))
except ValueError:
    interval = 30

client = MyClient(intents=intents, interval=interval)


# --- Periodic voice join and soundboard logic ---




TOKEN = os.getenv('DISCORD_BOT_TOKEN')

if not TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN not set in environment. Please create a .env file.")

client.run(TOKEN)