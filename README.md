# Audio Ambush - Discord Soundboard Bot

A Discord bot that periodically joins voice channels and plays random sounds from a web-managed library. Built with a clean, event-driven architecture using Python, discord.py, and FastAPI.

## Features

- 🔊 **Automatic Soundboard** - Bot joins the most populated voice channel and plays random sounds at configurable intervals
- �️ **Volume Control** - Adjust playback volume via web interface or Discord commands
- 🌐 **Web Admin Interface** - Upload, rename, and delete sounds through a modern web UI
- 🔐 **Discord OAuth2** - Secure authentication using your Discord account
- 📢 **Real-time Notifications** - Get Discord messages when sounds are added, renamed, deleted, or settings changed
- ⚡ **Event-Driven Architecture** - No database polling; instant updates via pub/sub pattern
- 💾 **SQLite Storage** - Sounds stored as BLOBs for easy backup and portability
- 🤖 **Slash Commands** - `/list`, `/status`, `/volume`, and `/ping` commands

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          main.py                                │
│                    (Dependency Injection)                       │
└─────────────────────────────────────────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  AudioAmbush  │  │    EventBus     │  │  Repositories   │
│   (Discord)     │  │   (Pub/Sub)     │  │   (Data Layer)  │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                     │                     │
         │           ┌─────────┴─────────┐           │
         ▼           ▼                   ▼           ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Services                                │
├─────────────────┬─────────────────────┬─────────────────────────┤
│ SoundboardSvc   │ NotificationSvc     │ WebServerSvc            │
│ (Voice playback)│ (Discord messages)  │ (FastAPI + Uvicorn)     │
└─────────────────┴─────────────────────┴─────────────────────────┘
```

### Project Structure

```
audio-ambush/
├── main.py                 # Entry point, wires dependencies
├── core/
│   ├── config.py           # Configuration from environment
│   └── events.py           # EventBus and event types
├── bot/
│   └── client.py           # AudioAmbush Discord client
├── repositories/
│   ├── base.py             # DatabaseManager
│   ├── sound_repository.py # Sound CRUD operations
│   └── config_repository.py# Config persistence
├── services/
│   ├── soundboard_service.py    # Voice channel playback
│   ├── notification_service.py  # Discord notifications
│   └── web_server_service.py    # FastAPI server
├── web/
│   └── __init__.py         # Web routes and handlers
├── commands/
│   ├── ping.py             # Ping command
│   ├── list.py             # List all sounds
│   ├── status.py           # Show bot status
│   └── volume.py           # Set playback volume
└── templates/
    └── soundboard_admin.html
```

### Key Design Patterns

| Pattern | Implementation | Purpose |
|---------|---------------|---------|
| **Repository** | `SoundRepository`, `ConfigRepository` | Abstracts database operations |
| **Pub/Sub** | `EventBus` | Decouples components, enables real-time updates |
| **Dependency Injection** | `main.py` | Testable, loosely coupled components |
| **Service Layer** | `*Service` classes | Encapsulates business logic |

### Event Flow Example

When a user uploads a sound via the web interface:

```
Web Upload → SoundRepository.create() → EventBus.publish(SOUND_UPLOADED, source="web")
                                                    │
                    ┌───────────────────────────────┘
                    ▼
        NotificationService._on_sound_uploaded()
                    │
                    ▼
        Discord Channel: "📥 Sound uploaded: **mysound.mp3** (web)"
```

Events include a `source` field to indicate where the action originated (e.g., "web" for web interface actions).

## Quick Start

### Prerequisites

- Python 3.11+
- FFmpeg (for audio playback)
- Discord Bot Token ([Discord Developer Portal](https://discord.com/developers/applications))

### Installation

1. **Clone the repository:**
   ```sh
   git clone https://github.com/yourusername/audio-ambush.git
   cd audio-ambush
   ```

2. **Create and activate a virtual environment:**
   ```sh
   python -m venv bot-env
   
   # Linux/macOS
   source bot-env/bin/activate
   
   # Windows
   bot-env\Scripts\activate
   ```

3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   
   Create a `.env` file in the project root:
   ```ini
   # Required
   DISCORD_BOT_TOKEN=your_bot_token
   GUILD_ID=your_server_id
   
   # Required for web admin
   DISCORD_CLIENT_ID=your_client_id
   DISCORD_CLIENT_SECRET=your_client_secret
   DISCORD_REDIRECT_URI=http://localhost:8000/callback
   
   # Optional
   SOUNDBOARD_DB_PATH=./soundboard.db
   SOUNDBOARD_INTERVAL=30
   SOUNDBOARD_NOTIFY_CHANNEL_ID=your_channel_id
   SOUNDBOARD_WEB_HOST=0.0.0.0
   SOUNDBOARD_WEB_PORT=8000
   SOUNDBOARD_WEB_ROOT_PATH=
   ```

5. **Run the bot:**
   ```sh
   python main.py
   ```
   
   Or use the provided scripts:
   ```sh
   # Linux/macOS
   ./run_linux.sh
   
   # Windows
   .\run_windows.bat
   ```

6. **Access the web interface:**
   
   Open [http://localhost:8000](http://localhost:8000) and log in with Discord.

## Configuration Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DISCORD_BOT_TOKEN` | ✅ | - | Bot token from Discord Developer Portal |
| `GUILD_ID` | ✅ | - | Your Discord server ID |
| `DISCORD_CLIENT_ID` | ✅ | - | OAuth2 client ID for web login |
| `DISCORD_CLIENT_SECRET` | ✅ | - | OAuth2 client secret |
| `DISCORD_REDIRECT_URI` | ✅ | - | OAuth2 callback URL (must match portal) |
| `SOUNDBOARD_DB_PATH` | ❌ | `./soundboard.db` | SQLite database path |
| `SOUNDBOARD_INTERVAL` | ❌ | `30` | Seconds between sound plays (30-3600) |
| `SOUNDBOARD_VOLUME` | ❌ | `100` | Playback volume percentage (0-100) |
| `SOUNDBOARD_NOTIFY_CHANNEL_ID` | ❌ | - | Channel for upload/delete notifications |
| `SOUNDBOARD_WEB_HOST` | ❌ | `0.0.0.0` | Web server bind address |
| `SOUNDBOARD_WEB_PORT` | ❌ | `8000` | Web server port |
| `SOUNDBOARD_WEB_ROOT_PATH` | ❌ | `` | URL prefix for reverse proxy setups |

## Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to **Bot** → Create bot → Copy token → Set as `DISCORD_BOT_TOKEN`
4. Enable **Message Content Intent** under Privileged Gateway Intents
5. Go to **OAuth2** → Copy Client ID and Secret
6. Add redirect URI: `http://localhost:8000/callback`
7. Go to **OAuth2 → URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Connect`, `Speak`, `Send Messages`
8. Use generated URL to invite bot to your server

## Adding Slash Commands

Create a new file in `commands/`:

```python
# commands/hello.py
from discord import app_commands, Interaction

@app_commands.command(name="hello", description="Say hello!")
async def hello_command(interaction: Interaction):
    await interaction.response.send_message(f"Hello, {interaction.user.mention}!")
```

Commands are automatically loaded on startup.

### Built-in Commands

| Command | Description |
|---------|-------------|
| `/ping` | Check if the bot is responding |
| `/list` | Show all available sounds in the library |
| `/status` | Display bot status, voice connection, interval, volume, and sound count |
| `/volume <level>` | Set playback volume (0-100) |

## Extending the Bot

### Adding a New Service

```python
# services/my_service.py
class MyService:
    def __init__(self, client, event_bus):
        self._client = client
        self._event_bus = event_bus
    
    async def start(self):
        # Subscribe to events, start background tasks
        pass
    
    async def stop(self):
        # Cleanup
        pass
```

Register in `main.py`:
```python
my_service = MyService(client=bot, event_bus=event_bus)
bot.register_service(my_service)
```

### Custom Events

```python
from core.events import Event, EventType, ConfigEvent, get_event_bus

# Define new event type in core/events.py
class EventType(Enum):
    MY_CUSTOM_EVENT = auto()

# Publish (use source to track origin)
await event_bus.publish(ConfigEvent(
    event_type=EventType.MY_CUSTOM_EVENT,
    key="my_key",
    value="new_value",
    source="web"  # Optional: track where event originated
))

# Subscribe
event_bus.subscribe(EventType.MY_CUSTOM_EVENT, my_handler)
```

### Available Event Types

| Event Type | Event Class | Description |
|------------|-------------|-------------|
| `SOUND_UPLOADED` | `SoundEvent` | A new sound was added |
| `SOUND_DELETED` | `SoundEvent` | A sound was removed |
| `SOUND_RENAMED` | `SoundEvent` | A sound was renamed |
| `INTERVAL_CHANGED` | `ConfigEvent` | Playback interval was changed |
| `VOLUME_CHANGED` | `ConfigEvent` | Playback volume was changed |
| `BOT_READY` | `SystemEvent` | Bot has connected to Discord |
| `SHUTDOWN` | `SystemEvent` | Bot is shutting down |

## Deployment

### Reverse Proxy (nginx)

```nginx
location /audio-ambush/ {
    proxy_pass http://127.0.0.1:8000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

Set `SOUNDBOARD_WEB_ROOT_PATH=/audio-ambush` in `.env`.

### Docker

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y ffmpeg
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

## Security Notes

- OAuth2 login required for all admin actions
- Session cookies are encrypted with a random key
- Sounds are stored in SQLite, not the filesystem
- Configure firewall to restrict web interface access if needed

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -am 'Add my feature'`
4. Push to branch: `git push origin feature/my-feature`
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details.

---

**Issues or questions?** Open an issue on GitHub!
