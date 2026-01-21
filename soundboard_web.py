

import os
import sqlite3
import secrets
import urllib.parse
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Request, Response, Depends, APIRouter
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2AuthorizationCodeBearer
from starlette.middleware.sessions import SessionMiddleware
import httpx
from dotenv import load_dotenv
from db_util import ensure_valid_sqlite_db, ensure_tables_exist
import time

load_dotenv()
ROOT_PATH = os.getenv("SOUNDBOARD_WEB_ROOT_PATH", "")
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")
DISCORD_OAUTH_AUTHORIZE_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_OAUTH_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_API_USER_URL = "https://discord.com/api/users/@me"
DB_PATH = os.getenv("SOUNDBOARD_DB_PATH", os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "soundboard.db")))
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB
ensure_valid_sqlite_db(DB_PATH)
ensure_tables_exist(DB_PATH)
app = FastAPI(root_path=ROOT_PATH)
router = APIRouter()
templates = Jinja2Templates(directory="templates")
app.add_middleware(SessionMiddleware, secret_key=secrets.token_urlsafe(32))


def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

def get_root_path(request: Request):
    return request.scope.get("root_path", "")

def get_db_conn():
    return sqlite3.connect(DB_PATH)

def ensure_logged_in(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url=f"{get_root_path(request)}/login")
    return user

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
        return Response(content="<h2>No code provided</h2>", media_type="text/html", status_code=400)
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
            return Response(content="<h2>Failed to authenticate with Discord</h2>", media_type="text/html", status_code=400)
        token_json = token_resp.json()
        access_token = token_json["access_token"]
        user_resp = await client.get(DISCORD_API_USER_URL, headers={"Authorization": f"Bearer {access_token}"})
        if user_resp.status_code != 200:
            return Response(content="<h2>Failed to fetch user info</h2>", media_type="text/html", status_code=400)
        user_json = user_resp.json()
        request.session["user"] = user_json
        root_path = request.scope.get("root_path", "")
    return RedirectResponse(url=f"{root_path}/")

@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    root_path = request.scope.get("root_path", "")
    return RedirectResponse(url=f"{root_path}/login")


@router.get("/")
def main(request: Request):
    user = ensure_logged_in(request)
    if not isinstance(user, dict):
        return user
    with get_db_conn() as conn:
        files = [row[0] for row in conn.execute("SELECT filename FROM sounds").fetchall()]
        interval_row = conn.execute("SELECT interval FROM interval_config WHERE id = 1").fetchone()
        interval_value = interval_row[0] if interval_row else 30
    username = user.get('username', 'Unknown')
    avatar = user.get('avatar')
    avatar_url = f"https://cdn.discordapp.com/avatars/{user['id']}/{avatar}.png" if avatar else ""
    return templates.TemplateResponse(
        "soundboard_admin.html",
        {
            "request": request,
            "files": files,
            "interval_value": interval_value,
            "username": username,
            "avatar_url": avatar_url
        }
    )

# Add endpoint for renaming sounds (must be at module level, not inside HTML)
@router.post("/rename")
async def rename_file(request: Request, old_filename: str = Form(...), new_filename: str = Form(...)):
    user = ensure_logged_in(request)
    if not isinstance(user, dict):
        return user
    new_filename = new_filename.strip()
    if not new_filename.lower().endswith(".mp3"):
        new_filename += ".mp3"
    if not new_filename or len(new_filename) > 64 or "/" in new_filename or ".." in new_filename:
        raise HTTPException(status_code=400, detail="Invalid new filename.")
    with get_db_conn() as conn:
        exists = conn.execute("SELECT 1 FROM sounds WHERE filename = ?", (new_filename,)).fetchone()
        if exists:
            raise HTTPException(status_code=400, detail="A sound with that name already exists.")
        conn.execute("UPDATE sounds SET filename = ? WHERE filename = ?", (new_filename, old_filename))
        # Insert event into events table
        conn.execute("INSERT INTO soundboard_events (timestamp, event_type, filename, extra) VALUES (?, ?, ?, ?)", (int(time.time()), 'rename', old_filename, new_filename))

    return RedirectResponse(url=f"{get_root_path(request)}/", status_code=303)

@router.post("/delete")
async def delete_file(request: Request, filename: str = Form(...)):
    user = ensure_logged_in(request)
    if not isinstance(user, dict):
        return user
    with get_db_conn() as conn:
        conn.execute("DELETE FROM sounds WHERE filename = ?", (filename,))
        # Insert event into events table
        conn.execute("INSERT INTO soundboard_events (timestamp, event_type, filename) VALUES (?, ?, ?)", (int(time.time()), 'delete', filename))
    return RedirectResponse(url=f"{get_root_path(request)}/", status_code=303)


@router.post("/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
    user = ensure_logged_in(request)
    if not isinstance(user, dict):
        return user
    if not file.filename.lower().endswith(".mp3"):
        raise HTTPException(status_code=400, detail="Only .mp3 files are supported.")
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Max size is 1MB.")
    with get_db_conn() as conn:
        try:
            conn.execute("INSERT OR REPLACE INTO sounds (filename, data) VALUES (?, ?)", (file.filename, contents))
            # Insert event into events table
            conn.execute("INSERT INTO soundboard_events (timestamp, event_type, filename) VALUES (?, ?, ?)", (int(time.time()), 'upload', file.filename))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return RedirectResponse(url=f"{get_root_path(request)}/", status_code=303)

@router.get("/download/{filename}")
def download_file(filename: str):
    with get_db_conn() as conn:
        row = conn.execute("SELECT data FROM sounds WHERE filename = ?", (filename,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="File not found.")
    return StreamingResponse(iter([row[0]]), media_type="audio/mp3")

@router.post("/set-interval")
async def set_interval(request: Request, interval: int = Form(...)):
    user = ensure_logged_in(request)
    if not isinstance(user, dict):
        return user
    if interval < 30 or interval > 3600:
        raise HTTPException(status_code=400, detail="Interval must be between 30 and 3600 seconds.")
    with get_db_conn() as conn:
        conn.execute("UPDATE interval_config SET interval = ? WHERE id = 1", (interval,))
        conn.execute("INSERT INTO soundboard_events (timestamp, event_type, filename) VALUES (?, ?, ?)", (int(time.time()), 'interval_change', str(interval)))
    return RedirectResponse(url=f"{get_root_path(request)}/", status_code=303)



# Mount the router at root
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("SOUNDBOARD_WEB_HOST", "127.0.0.1")
    port = int(os.getenv("SOUNDBOARD_WEB_PORT", 8080))
    uvicorn.run(app, host=host, port=port)
