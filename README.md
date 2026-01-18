# Discord Soundboard Admin

This project provides a Discord bot with a web-based soundboard admin interface. It allows you to upload, delete, rename, and play sound effects (mp3 files) stored in a SQLite database, with Discord OAuth2 authentication for secure access.

## Features
- Discord bot with slash command support (discord.py 2.x)
- Periodic voice join and soundboard playback (interval configurable, minimum 30s)
- FastAPI web interface for soundboard management
- Upload, delete, and rename mp3 sound effects
- Sound files stored as BLOBs in SQLite (configurable path)
- Modern, responsive web UI
- Discord OAuth2 authentication (identify scope)
- Session management with configurable secret

## Quick Start

1. **Clone the repository:**
   ```sh
   git clone https://github.com/yourusername/discord-soundboard-admin.git
   cd discord-soundboard-admin
   ```

2. **Create and activate a Python virtual environment:**
   ```sh
   python -m venv bot-env
   source bot-env/bin/activate  # On Windows: bot-env\Scripts\activate
   ```

3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   Create a `.env` file in the project root with the following:
   ```ini
   DISCORD_BOT_TOKEN=your_discord_bot_token
   DISCORD_CLIENT_ID=your_discord_client_id
   DISCORD_CLIENT_SECRET=your_discord_client_secret
   DISCORD_REDIRECT_URI=http://localhost:8080/callback
   SESSION_SECRET=your_random_secret_key
   SOUNDBOARD_DB_PATH=./soundboard.db  # Optional, defaults to ./soundboard.db
   GUILD_ID=your_guild_id_here  # Optional
   SOUNDBOARD_WEB_HOST=0.0.0.0         # Optional, defaults to 127.0.0.1
   SOUNDBOARD_WEB_PORT=8080            # Optional, defaults to 8080
   ```

5. **Run the bot and web server:**
   ```sh
   python main.py
   # or (web admin only, host/port configurable via .env)
   uvicorn soundboard_web:app --host $SOUNDBOARD_WEB_HOST --port $SOUNDBOARD_WEB_PORT
   # Defaults: --host 127.0.0.1 --port 8080
   ```

6. **Access the web interface:**
   Open [http://localhost:8080](http://localhost:8080) in your browser. Log in with your Discord account.


## Configuration

All configuration is handled via environment variables in your `.env` file:


| Variable                | Description                                                      | Example/Default                  |
|-------------------------|------------------------------------------------------------------|----------------------------------|
| `DISCORD_BOT_TOKEN`     | Your Discord bot token                                           | (required)                       |
| `DISCORD_CLIENT_ID`     | Discord OAuth2 client ID                                         | (required)                       |
| `DISCORD_CLIENT_SECRET` | Discord OAuth2 client secret                                     | (required)                       |
| `DISCORD_REDIRECT_URI`  | OAuth2 redirect URI (must match Discord app settings)            | http://localhost:8080/callback   |
| `SESSION_SECRET`        | Secret key for session encryption (keep this safe!)              | (required, random string)        |
| `SOUNDBOARD_DB_PATH`    | Path to the SQLite database file for soundboard storage          | ./soundboard.db                  |
| `GUILD_ID`              | (Optional) Your Discord server's guild ID (for some features)    |                                  |
| `SOUNDBOARD_WEB_HOST`   | Host for the web admin (FastAPI/uvicorn)                         | 127.0.0.1                        |
| `SOUNDBOARD_WEB_PORT`   | Port for the web admin (FastAPI/uvicorn)                         | 8080                             |
| `SOUNDBOARD_WEB_ROOT_PATH` | (Optional) Root path for FastAPI app (for subpath mounting, e.g. /sjefbot) | (empty string for root)          |


### Sound Interval

- The bot's sound playback interval is configurable from the web admin page.
- **Minimum allowed interval is 30 seconds.**



**Notes:**
- All variables except `GUILD_ID` and `SOUNDBOARD_DB_PATH` are required for normal operation.
- If `SOUNDBOARD_DB_PATH` is not set, the database defaults to `./soundboard.db` in the project root.
- `SESSION_SECRET` must be the same for all web server instances to keep sessions valid.
- `DISCORD_REDIRECT_URI` must match the value set in your Discord developer portal.
- The minimum allowed interval for bot sound playback is 30 seconds.
- Set `SOUNDBOARD_WEB_ROOT_PATH=/sjefbot` in your `.env` to serve the app at a subpath (e.g., https://yourdomain/sjefbot/), or leave it empty for root. Restart your app after changing this value.


## Security Notes
- Sessions are secured with a secret key from `.env` (`SESSION_SECRET`).
- OAuth2 login is required for all admin actions.
- The SQLite database path can be configured via `SOUNDBOARD_DB_PATH`.

## Customization
- To change the look and feel, edit the HTML/CSS in `soundboard_web.py`.
- To add more Discord bot features, edit `main.py` and add new command modules.

## License
MIT License

---

For issues or contributions, please open a pull request or issue on GitHub.
