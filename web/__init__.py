"""
Web API for soundboard administration.

This module provides a FastAPI web interface for managing sounds
and configuration. It uses the repository pattern and publishes
events through the EventBus.
"""

import secrets
import urllib.parse
from typing import Callable

import httpx
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Request, Response, APIRouter
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from core.config import Config
from core.events import EventBus, EventType, SoundEvent, ConfigEvent
from repositories import DatabaseManager, SoundRepository, ConfigRepository


# Constants
DISCORD_OAUTH_AUTHORIZE_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_OAUTH_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_API_USER_URL = "https://discord.com/api/users/@me"
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB


class SoundboardWebApp:
    """
    Web application for soundboard administration.

    Provides:
    - Discord OAuth2 authentication
    - Sound file management (upload, rename, delete, download)
    - Configuration management
    - Event publishing for real-time updates
    """

    def __init__(
        self,
        config: Config,
        sound_repository: SoundRepository,
        config_repository: ConfigRepository,
        event_bus: EventBus,
    ):
        """
        Initialize the web application.

        Args:
            config: Application configuration
            sound_repository: Repository for sound operations
            config_repository: Repository for config operations
            event_bus: Event bus for publishing events
        """
        self._config = config
        self._sound_repo = sound_repository
        self._config_repo = config_repository
        self._event_bus = event_bus

        # Create FastAPI app
        self.app = FastAPI(root_path=config.web_root_path)
        self.app.add_middleware(SessionMiddleware, secret_key=secrets.token_urlsafe(32))

        # Setup templates
        self._templates = Jinja2Templates(directory="templates")

        # Register routes
        self._register_routes()

    def _register_routes(self) -> None:
        """Register all API routes."""
        router = APIRouter()

        # Auth routes
        router.get("/login")(self.login)
        router.get("/callback")(self.callback)
        router.get("/logout")(self.logout)

        # Main page
        router.get("/")(self.main_page)

        # Sound management
        router.post("/upload")(self.upload_file)
        router.post("/rename")(self.rename_file)
        router.post("/delete")(self.delete_file)
        router.get("/download/{filename}")(self.download_file)

        # Config
        router.post("/set-interval")(self.set_interval)
        router.post("/set-volume")(self.set_volume)

        self.app.include_router(router)

    def _get_root_path(self, request: Request) -> str:
        """Get the root path from the request scope."""
        return request.scope.get("root_path", "")

    def _ensure_logged_in(self, request: Request) -> dict | None:
        """
        Check if user is logged in.

        Returns:
            User dict if logged in, None otherwise
        """
        return request.session.get("user")

    def _require_login(self, request: Request) -> dict:
        """
        Require login and return user or raise redirect.

        Returns:
            User dict if logged in

        Raises:
            RedirectResponse if not logged in
        """
        user = self._ensure_logged_in(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return user

    # ==================== Auth Routes ====================

    def login(self, request: Request):
        """Redirect to Discord OAuth2 login."""
        params = {
            "client_id": self._config.discord_client_id,
            "redirect_uri": self._config.discord_redirect_uri,
            "response_type": "code",
            "scope": "identify",
            "prompt": "consent"
        }
        url = f"{DISCORD_OAUTH_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"
        return RedirectResponse(url)

    async def callback(self, request: Request, code: str = None):
        """Handle Discord OAuth2 callback."""
        if not code:
            return Response(
                content="<h2>No code provided</h2>",
                media_type="text/html",
                status_code=400
            )

        data = {
            "client_id": self._config.discord_client_id,
            "client_secret": self._config.discord_client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self._config.discord_redirect_uri,
            "scope": "identify"
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with httpx.AsyncClient() as client:
            # Exchange code for token
            token_resp = await client.post(DISCORD_OAUTH_TOKEN_URL, data=data, headers=headers)
            if token_resp.status_code != 200:
                return Response(
                    content="<h2>Failed to authenticate with Discord</h2>",
                    media_type="text/html",
                    status_code=400
                )

            token_json = token_resp.json()
            access_token = token_json["access_token"]

            # Fetch user info
            user_resp = await client.get(
                DISCORD_API_USER_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if user_resp.status_code != 200:
                return Response(
                    content="<h2>Failed to fetch user info</h2>",
                    media_type="text/html",
                    status_code=400
                )

            user_json = user_resp.json()
            request.session["user"] = user_json

        root_path = self._get_root_path(request)
        return RedirectResponse(url=f"{root_path}/")

    def logout(self, request: Request):
        """Log out the current user."""
        request.session.clear()
        root_path = self._get_root_path(request)
        return RedirectResponse(url=f"{root_path}/login")

    # ==================== Main Page ====================

    def main_page(self, request: Request):
        """Render the main admin page."""
        user = self._ensure_logged_in(request)
        if not user:
            return RedirectResponse(url=f"{self._get_root_path(request)}/login")

        # Get data from repositories
        files = self._sound_repo.get_all_filenames()
        interval_value = self._config_repo.get_interval()
        volume_value = self._config_repo.get_volume()

        # User info
        username = user.get("username", "Unknown")
        avatar = user.get("avatar")
        avatar_url = f"https://cdn.discordapp.com/avatars/{user['id']}/{avatar}.png" if avatar else ""

        return self._templates.TemplateResponse(
            "soundboard_admin.html",
            {
                "request": request,
                "files": files,
                "interval_value": interval_value,
                "volume_value": volume_value,
                "username": username,
                "avatar_url": avatar_url
            }
        )

    # ==================== Sound Management ====================

    async def upload_file(self, request: Request, file: UploadFile = File(...)):
        """Upload a new sound file."""
        user = self._ensure_logged_in(request)
        if not user:
            return RedirectResponse(url=f"{self._get_root_path(request)}/login")

        if not file.filename.lower().endswith(".mp3"):
            raise HTTPException(status_code=400, detail="Only .mp3 files are supported.")

        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large. Max size is 1MB.")

        try:
            self._sound_repo.update_or_create(file.filename, contents)

            # Publish event
            await self._event_bus.publish(SoundEvent(
                event_type=EventType.SOUND_UPLOADED,
                source="web",
                filename=file.filename
            ))

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        return RedirectResponse(url=f"{self._get_root_path(request)}/", status_code=303)

    async def rename_file(
        self,
        request: Request,
        old_filename: str = Form(...),
        new_filename: str = Form(...)
    ):
        """Rename an existing sound file."""
        user = self._ensure_logged_in(request)
        if not user:
            return RedirectResponse(url=f"{self._get_root_path(request)}/login")

        new_filename = new_filename.strip()
        if not new_filename.lower().endswith(".mp3"):
            new_filename += ".mp3"

        # Validate filename
        if not new_filename or len(new_filename) > 64 or "/" in new_filename or ".." in new_filename:
            raise HTTPException(status_code=400, detail="Invalid new filename.")

        # Check if target exists
        if self._sound_repo.exists(new_filename):
            raise HTTPException(status_code=400, detail="A sound with that name already exists.")

        if not self._sound_repo.rename(old_filename, new_filename):
            raise HTTPException(status_code=404, detail="Sound not found.")

        # Publish event
        await self._event_bus.publish(SoundEvent(
            event_type=EventType.SOUND_RENAMED,
            source="web",
            filename=old_filename,
            new_filename=new_filename
        ))

        return RedirectResponse(url=f"{self._get_root_path(request)}/", status_code=303)

    async def delete_file(self, request: Request, filename: str = Form(...)):
        """Delete a sound file."""
        user = self._ensure_logged_in(request)
        if not user:
            return RedirectResponse(url=f"{self._get_root_path(request)}/login")

        if not self._sound_repo.delete(filename):
            raise HTTPException(status_code=404, detail="Sound not found.")

        # Publish event
        await self._event_bus.publish(SoundEvent(
            event_type=EventType.SOUND_DELETED,
            source="web",
            filename=filename
        ))

        return RedirectResponse(url=f"{self._get_root_path(request)}/", status_code=303)

    def download_file(self, filename: str):
        """Download a sound file."""
        data = self._sound_repo.get_data_by_filename(filename)
        if not data:
            raise HTTPException(status_code=404, detail="File not found.")

        return StreamingResponse(iter([data]), media_type="audio/mp3")

    # ==================== Configuration ====================

    async def set_interval(self, request: Request, interval: int = Form(...)):
        """Set the playback interval."""
        user = self._ensure_logged_in(request)
        if not user:
            return RedirectResponse(url=f"{self._get_root_path(request)}/login")

        if interval < 30 or interval > 3600:
            raise HTTPException(
                status_code=400,
                detail="Interval must be between 30 and 3600 seconds."
            )

        old_interval = self._config_repo.set_interval(interval)

        # Publish event
        await self._event_bus.publish(ConfigEvent(
            event_type=EventType.INTERVAL_CHANGED,
            source="web",
            key="interval",
            value=interval,
            old_value=old_interval
        ))

        return RedirectResponse(url=f"{self._get_root_path(request)}/", status_code=303)

    async def set_volume(self, request: Request, volume: int = Form(...)):
        """Set the playback volume."""
        user = self._ensure_logged_in(request)
        if not user:
            return RedirectResponse(url=f"{self._get_root_path(request)}/login")

        if volume < 0 or volume > 100:
            raise HTTPException(
                status_code=400,
                detail="Volume must be between 0 and 100."
            )

        old_volume = self._config_repo.get_volume()
        self._config_repo.set_volume(volume)

        # Publish event
        await self._event_bus.publish(ConfigEvent(
            event_type=EventType.VOLUME_CHANGED,
            source="web",
            key="volume",
            value=volume,
            old_value=old_volume
        ))

        return RedirectResponse(url=f"{self._get_root_path(request)}/", status_code=303)


def create_web_app(
    config: Config,
    sound_repository: SoundRepository,
    config_repository: ConfigRepository,
    event_bus: EventBus,
) -> FastAPI:
    """
    Factory function to create the web application.

    Args:
        config: Application configuration
        sound_repository: Repository for sound operations
        config_repository: Repository for config operations
        event_bus: Event bus for publishing events

    Returns:
        Configured FastAPI application
    """
    web_app = SoundboardWebApp(config, sound_repository, config_repository, event_bus)
    return web_app.app
