
import os
import sqlite3
import secrets
import urllib.parse
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Request, Response, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.security import OAuth2AuthorizationCodeBearer
from starlette.middleware.sessions import SessionMiddleware
import httpx
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Use FastAPI root_path for subpath deployment
ROOT_PATH = os.getenv("SOUNDBOARD_WEB_ROOT_PATH", "")
from fastapi import APIRouter
app = FastAPI(root_path=ROOT_PATH)
router = APIRouter()

# Load environment variables from .env file
load_dotenv()

# Add session middleware for login state
app.add_middleware(SessionMiddleware, secret_key=secrets.token_urlsafe(32))

# Discord OAuth2 config
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")
DISCORD_OAUTH_AUTHORIZE_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_OAUTH_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_API_USER_URL = "https://discord.com/api/users/@me"

def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
DB_PATH = os.getenv("SOUNDBOARD_DB_PATH", os.path.abspath("soundboard.db"))  # Configurable via .env (SOUNDBOARD_DB_PATH)
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB

# Ensure table exists
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS sounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE,
            data BLOB
        )
        """)
        # Ensure interval_config table exists
        conn.execute("""
        CREATE TABLE IF NOT EXISTS interval_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            interval INTEGER NOT NULL
        )
        """)
        # Insert default interval if not present
        cur = conn.execute("SELECT interval FROM interval_config WHERE id = 1")
        if cur.fetchone() is None:
            conn.execute("INSERT INTO interval_config (id, interval) VALUES (1, 30)")
init_db()

@router.get("/login")
def login(request: Request):
    params = {
        "client_id": DISCORD_CLIENT_ID,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "response_type": "code",
        "scope": "identify",
        "prompt": "consent"
    }
    url = f"{DISCORD_OAUTH_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url)

@router.get("/callback")
async def callback(request: Request, code: str = None):
    if not code:
        return HTMLResponse("<h2>No code provided</h2>", status_code=400)
    data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "scope": "identify"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(DISCORD_OAUTH_TOKEN_URL, data=data, headers=headers)
        if token_resp.status_code != 200:
            return HTMLResponse("<h2>Failed to authenticate with Discord</h2>", status_code=400)
        token_json = token_resp.json()
        access_token = token_json["access_token"]
        user_resp = await client.get(DISCORD_API_USER_URL, headers={"Authorization": f"Bearer {access_token}"})
        if user_resp.status_code != 200:
            return HTMLResponse("<h2>Failed to fetch user info</h2>", status_code=400)
        user_json = user_resp.json()
        request.session["user"] = user_json
        root_path = request.scope.get("root_path", "")
    return RedirectResponse(url=f"{root_path}/")

@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    root_path = request.scope.get("root_path", "")
    return RedirectResponse(url=f"{root_path}/login")

def require_login(request: Request):
    user = request.session.get("user")
    if not user:
        root_path = request.scope.get("root_path", "")
        return RedirectResponse(url=f"{root_path}/login")
    return user

@router.get("/", response_class=HTMLResponse)
def main(request: Request):
    user = request.session.get("user")
    if not user:
        root_path = request.scope.get("root_path", "")
        return RedirectResponse(url=f"{root_path}/login")
    with sqlite3.connect(DB_PATH) as conn:
        files = conn.execute("SELECT filename FROM sounds").fetchall()
        interval_row = conn.execute("SELECT interval FROM interval_config WHERE id = 1").fetchone()
        interval_value = interval_row[0] if interval_row else 30
    file_list_html = "".join([
        f'''
        <li class="sound-item">
            <span class="sound-filename">{fname[0]}</span>
            <div class="sound-actions">
                <a class="play-btn" href="/download/{fname[0]}" title="Play" target="_blank">▶️</a>
                <form class="rename-form" action="/rename" method="post" style="display:inline; margin:0; padding:0;">
                    <input type="hidden" name="old_filename" value="{fname[0]}">
                    <input class="rename-input" type="text" name="new_filename" value="{fname[0]}" maxlength="64" required style="width:110px; font-size:0.95em; margin-right:4px;">
                    <button class="rename-btn" type="submit" title="Rename">✏️</button>
                </form>
                <form class="delete-form" action="/delete" method="post">
                    <input type="hidden" name="filename" value="{fname[0]}">
                    <button class="delete-btn" type="submit" title="Delete">🗑️</button>
                </form>
            </div>
        </li>
        ''' for fname in files
    ])
    username = user.get('username', 'Unknown')
    discriminator = user.get('discriminator', '')
    avatar = user.get('avatar')
    avatar_url = f"https://cdn.discordapp.com/avatars/{user['id']}/{avatar}.png" if avatar else ""
    return f"""
    <html>
    <head>
        <title>Soundboard Admin</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                background: #181c20;
                color: #f3f3f3;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 600px;
                margin: 40px auto;
                background: #23272b;
                border-radius: 12px;
                box-shadow: 0 4px 24px #000a;
                padding: 32px 28px 24px 28px;
            }}
            .user-info {{
                display: flex;
                align-items: center;
                margin-bottom: 18px;
            }}
            .user-avatar {{
                width: 40px;
                height: 40px;
                border-radius: 50%;
                margin-right: 12px;
            }}
            h2, h3 {{
                color: #ffb347;
                margin-top: 0;
            }}
            form {{
                margin-bottom: 24px;
            }}
            input[type="file"] {{
                background: #23272b;
                color: #f3f3f3;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 8px;
            }}
            input[type="submit"], button {{
                background: #ffb347;
                color: #23272b;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                cursor: pointer;
                margin-left: 8px;
                transition: background 0.2s;
            }}
            input[type="submit"]:hover, button:hover {{
                background: #ffd580;
            }}
            ul {{
                list-style: none;
                padding: 0;
            }}
            .sound-item {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                background: #23272b;
                border-bottom: 1px solid #333;
                padding: 10px 0;
            }}
            .sound-filename {{
                flex: 1;
                font-size: 1.08em;
                word-break: break-all;
            }}
            .sound-actions {{
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            .play-btn {{
                font-size: 1.2em;
                text-decoration: none;
                color: #ffb347;
                transition: color 0.2s;
                margin: 0;
                padding: 0 4px;
            }}
            .play-btn:hover {{
                color: #ffd580;
            }}
            .rename-form {{
                display: inline;
                margin: 0;
                padding: 0;
            }}
            .rename-input {{
                background: #181c20;
                color: #f3f3f3;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 2px 6px;
                margin-right: 2px;
            }}
            .rename-btn {{
                background: none;
                color: #4da6ff;
                border: none;
                font-size: 1.1em;
                cursor: pointer;
                padding: 0 4px;
                transition: color 0.2s;
            }}
            .rename-btn:hover {{
                color: #ffb347;
            }}
            .delete-form {{
                display: inline;
                margin: 0;
                padding: 0;
            }}
            .delete-btn {{
                background: none;
                color: #ff4d4d;
                border: none;
                font-size: 1.2em;
                cursor: pointer;
                padding: 0 4px;
                transition: color 0.2s;
            }}
            .delete-btn:hover {{
                color: #ffb347;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="user-info" style="margin-bottom: 24px;">
                {f'<img class="user-avatar" src="{avatar_url}" alt="avatar">' if avatar_url else ''}
                <span style="font-size:1.1em; font-weight:bold;">{username}#{discriminator}</span>
            </div>
            <h2 style="margin-bottom: 10px;">Soundboard Admin</h2>
            <form action="/set-interval" method="post" style="margin-bottom: 28px; display: flex; align-items: center; gap: 12px;">
                <label for="interval" style="color:#ffb347; font-weight:bold; font-size:1.08em;">Bot Sound Interval (seconds):</label>
                <input id="interval" name="interval" type="number" min="30" max="3600" value="{interval_value}" style="width:80px; font-size:1.08em;">
                <input type="submit" value="Update" style="background:#ffb347; color:#23272b; border:none; border-radius:6px; padding:7px 18px; font-weight:bold; font-size:1.08em; cursor:pointer;">
                <span style="color:#aaa; font-size:0.98em; margin-left:10px;">Controls how often the bot plays a sound in voice channels. (Minimum: 30s)</span>
            </form>
            <form action="upload" enctype="multipart/form-data" method="post" style="margin-bottom: 30px;">
                <label for="file" style="color:#ffb347; font-weight:bold;">Upload New Sound (.mp3):</label>
                <input name="file" id="file" type="file" accept="audio/mp3" required style="margin-left:10px;">
                <input type="submit" value="Upload" style="background:#ffb347; color:#23272b; border:none; border-radius:6px; padding:7px 18px; font-weight:bold; cursor:pointer;">
            </form>
            <h3 style="margin-bottom: 10px;">Available Sound Effects</h3>
            <ul>{file_list_html}</ul>
        </div>
    </body>
    </html>
    """

# Add endpoint for renaming sounds (must be at module level, not inside HTML)
@router.post("/rename")
async def rename_file(request: Request, old_filename: str = Form(...), new_filename: str = Form(...)):
    user = require_login(request)
    # Ensure .mp3 extension is present
    new_filename = new_filename.strip()
    if not new_filename.lower().endswith(".mp3"):
        new_filename += ".mp3"
    # Basic validation: non-empty, .mp3 extension, reasonable length, no path traversal
    if not new_filename or len(new_filename) > 64 or "/" in new_filename or ".." in new_filename:
        raise HTTPException(status_code=400, detail="Invalid new filename.")
    if not new_filename.lower().endswith(".mp3"):
        raise HTTPException(status_code=400, detail="Filename must end with .mp3")
    with sqlite3.connect(DB_PATH) as conn:
        # Check if new filename already exists
        exists = conn.execute("SELECT 1 FROM sounds WHERE filename = ?", (new_filename,)).fetchone()
        if exists:
            raise HTTPException(status_code=400, detail="A sound with that name already exists.")
        conn.execute("UPDATE sounds SET filename = ? WHERE filename = ?", (new_filename, old_filename))
        root_path = request.scope.get("root_path", "")
    return RedirectResponse(url=f"{root_path}/", status_code=303)

@router.post("/delete")
async def delete_file(request: Request, filename: str = Form(...)):
    user = require_login(request)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM sounds WHERE filename = ?", (filename,))
        root_path = request.scope.get("root_path", "")
    return RedirectResponse(url=f"{root_path}/", status_code=303)


@router.post("/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
    user = require_login(request)
    if not file.filename.lower().endswith(".mp3"):
        raise HTTPException(status_code=400, detail="Only .mp3 files are supported.")
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Max size is 1MB.")
    with sqlite3.connect(DB_PATH) as conn:
        try:
            conn.execute("INSERT OR REPLACE INTO sounds (filename, data) VALUES (?, ?)", (file.filename, contents))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        root_path = request.scope.get("root_path", "")
    return RedirectResponse(url=f"{root_path}/", status_code=303)

@router.get("/download/{filename}")
def download_file(filename: str):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT data FROM sounds WHERE filename = ?", (filename,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="File not found.")
    return StreamingResponse(iter([row[0]]), media_type="audio/mp3")

@router.post("/set-interval")
async def set_interval(request: Request, interval: int = Form(...)):
    user = require_login(request)
    if interval < 30 or interval > 3600:
        raise HTTPException(status_code=400, detail="Interval must be between 30 and 3600 seconds.")
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE interval_config SET interval = ? WHERE id = 1", (interval,))
    root_path = request.scope.get("root_path", "")
    return RedirectResponse(url=f"{root_path}/", status_code=303)



# Mount the router at root
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("SOUNDBOARD_WEB_HOST", "127.0.0.1")
    port = int(os.getenv("SOUNDBOARD_WEB_PORT", 8080))
    uvicorn.run(app, host=host, port=port)
