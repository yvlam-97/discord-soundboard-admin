"""
Soundboard service for playing random sounds in voice channels.

Uses event-driven architecture instead of polling:
- Listens for INTERVAL_CHANGED events to adjust timing
- Caches interval locally to avoid repeated DB queries
"""

import asyncio
import os
import tempfile
from typing import TYPE_CHECKING

import discord

from core.events import EventBus, EventType, ConfigEvent

if TYPE_CHECKING:
    from bot.client import AudioAmbush
    from repositories import SoundRepository, ConfigRepository


class SoundboardService:
    """
    Service that periodically plays random sounds in voice channels.

    Features:
    - Joins the voice channel with the most members
    - Plays a random sound from the database
    - Interval can be changed at runtime via events
    - No database polling - uses event-driven updates
    """

    def __init__(
        self,
        client: "AudioAmbush",
        sound_repository: "SoundRepository",
        config_repository: "ConfigRepository",
        event_bus: EventBus,
    ):
        """
        Initialize the soundboard service.

        Args:
            client: Discord bot client
            sound_repository: Repository for sound operations
            config_repository: Repository for config operations
            event_bus: Event bus for receiving interval changes
        """
        self._client = client
        self._sound_repo = sound_repository
        self._config_repo = config_repository
        self._event_bus = event_bus

        self._task: asyncio.Task | None = None
        self._interval: int = 30  # Will be loaded from DB on start
        self._volume: float = 1.0  # Volume as 0.0-1.0, loaded from DB
        self._interval_changed = asyncio.Event()
        self._running = False

    @property
    def interval(self) -> int:
        """Get current playback interval in seconds."""
        return self._interval

    @property
    def volume(self) -> int:
        """Get current volume as percentage (0-100)."""
        return int(self._volume * 100)

    @property
    def is_running(self) -> bool:
        """Check if the service is running."""
        return self._running

    async def start(self) -> None:
        """Start the soundboard service."""
        # Load initial config from database
        self._interval = self._config_repo.get_interval()
        self._volume = self._config_repo.get_volume() / 100.0  # Convert to 0.0-1.0
        print(f"[SoundboardService] Initial interval: {self._interval}s, volume: {int(self._volume * 100)}%")

        # Subscribe to config change events
        self._event_bus.subscribe(EventType.INTERVAL_CHANGED, self._on_interval_changed)
        self._event_bus.subscribe(EventType.VOLUME_CHANGED, self._on_volume_changed)

        # Start the background task
        self._running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Stop the soundboard service."""
        self._running = False
        self._interval_changed.set()  # Wake up any waiting sleep

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        self._event_bus.unsubscribe(EventType.INTERVAL_CHANGED, self._on_interval_changed)
        self._event_bus.unsubscribe(EventType.VOLUME_CHANGED, self._on_volume_changed)

    async def _on_interval_changed(self, event: ConfigEvent) -> None:
        """Handle interval change events."""
        new_interval = int(event.value)
        print(f"[SoundboardService] Interval changed: {self._interval}s -> {new_interval}s")
        self._interval = new_interval
        self._interval_changed.set()  # Wake up the sleep to use new interval

    async def _on_volume_changed(self, event: ConfigEvent) -> None:
        """Handle volume change events."""
        new_volume = int(event.value) / 100.0
        print(f"[SoundboardService] Volume changed: {int(self._volume * 100)}% -> {int(new_volume * 100)}%")
        self._volume = new_volume

    async def _run_loop(self) -> None:
        """Main service loop."""
        await self._client.wait_until_ready()

        while self._running and not self._client.is_closed():
            try:
                await self._try_play_sound()
            except Exception as e:
                print(f"[SoundboardService] Error: {e}")

            # Sleep with ability to wake up early on interval change
            await self._interruptible_sleep(self._interval)

    async def _interruptible_sleep(self, seconds: int) -> None:
        """
        Sleep that can be interrupted by interval changes.

        Args:
            seconds: Number of seconds to sleep
        """
        self._interval_changed.clear()
        try:
            await asyncio.wait_for(
                self._interval_changed.wait(),
                timeout=seconds
            )
            # If we get here, interval was changed - just continue
        except asyncio.TimeoutError:
            # Normal sleep completion
            pass

    async def _try_play_sound(self) -> None:
        """Attempt to play a sound in a voice channel."""
        # Check if we have any sounds
        sound_count = self._sound_repo.get_count()
        if sound_count == 0:
            print("[SoundboardService] No sounds in database, skipping")
            return

        # Find a guild with occupied voice channels
        for guild in self._client.guilds:
            voice_channels = [
                c for c in guild.voice_channels
                if len(c.members) > 0
            ]

            if not voice_channels:
                continue

            # Find channel with most members
            target_channel = max(voice_channels, key=lambda c: len(c.members))

            # Only join if not already connected
            if guild.voice_client is None or not guild.voice_client.is_connected():
                try:
                    vc = await target_channel.connect()
                    await self._play_random_sound(vc)
                except Exception as e:
                    print(f"[SoundboardService] Failed to play sound: {e}")

    async def _play_random_sound(self, vc: discord.VoiceClient) -> None:
        """
        Play a random sound in the voice channel.

        Args:
            vc: Voice client to play through
        """
        sound = self._sound_repo.get_random()
        if not sound:
            print("[SoundboardService] No sound found")
            await vc.disconnect()
            return

        # Write to temporary file for FFmpeg
        suffix = os.path.splitext(sound.filename)[1]
        tmp_path = None

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(sound.data)
                tmp_path = tmp.name

            source = discord.FFmpegPCMAudio(tmp_path)
            # Apply volume transformation
            source = discord.PCMVolumeTransformer(source, volume=self._volume)
            vc.play(source)

            # Wait for playback to finish
            while vc.is_playing():
                await asyncio.sleep(0.5)

        finally:
            await vc.disconnect()
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
