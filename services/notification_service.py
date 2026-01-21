"""
Notification service for sending Discord messages when soundboard events occur.

Uses event-driven architecture - subscribes to events instead of polling.
"""

import asyncio
from typing import TYPE_CHECKING

from core.events import EventBus, EventType, SoundEvent, ConfigEvent

if TYPE_CHECKING:
    from bot.client import SjefBot


class NotificationService:
    """
    Service that sends Discord notifications for soundboard events.
    
    Features:
    - Sends messages when sounds are uploaded, renamed, or deleted
    - Notifies when playback interval changes
    - Fully event-driven - no polling required
    """
    
    def __init__(
        self,
        client: "SjefBot",
        event_bus: EventBus,
        notify_channel_id: int,
    ):
        """
        Initialize the notification service.
        
        Args:
            client: Discord bot client
            event_bus: Event bus for receiving events
            notify_channel_id: Discord channel ID to send notifications to
        """
        self._client = client
        self._event_bus = event_bus
        self._channel_id = notify_channel_id
        self._channel = None
    
    async def start(self) -> None:
        """Start the notification service."""
        if not self._channel_id:
            print("[NotificationService] No channel ID configured, skipping")
            return
        
        # Subscribe to events
        self._event_bus.subscribe(EventType.SOUND_UPLOADED, self._on_sound_uploaded)
        self._event_bus.subscribe(EventType.SOUND_DELETED, self._on_sound_deleted)
        self._event_bus.subscribe(EventType.SOUND_RENAMED, self._on_sound_renamed)
        self._event_bus.subscribe(EventType.INTERVAL_CHANGED, self._on_interval_changed)
        
        print(f"[NotificationService] Listening for events, will notify channel {self._channel_id}")
    
    async def stop(self) -> None:
        """Stop the notification service."""
        self._event_bus.unsubscribe(EventType.SOUND_UPLOADED, self._on_sound_uploaded)
        self._event_bus.unsubscribe(EventType.SOUND_DELETED, self._on_sound_deleted)
        self._event_bus.unsubscribe(EventType.SOUND_RENAMED, self._on_sound_renamed)
        self._event_bus.unsubscribe(EventType.INTERVAL_CHANGED, self._on_interval_changed)
    
    async def _get_channel(self):
        """Get or fetch the notification channel."""
        if self._channel is None:
            try:
                self._channel = await self._client.fetch_channel(self._channel_id)
            except Exception as e:
                print(f"[NotificationService] Failed to fetch channel: {e}")
                return None
        return self._channel
    
    async def _send_notification(self, message: str) -> None:
        """
        Send a notification to the configured channel.
        
        Args:
            message: Message to send
        """
        channel = await self._get_channel()
        if channel:
            try:
                await channel.send(message)
            except Exception as e:
                print(f"[NotificationService] Failed to send message: {e}")
    
    async def _on_sound_uploaded(self, event: SoundEvent) -> None:
        """Handle sound upload events."""
        await self._send_notification(f"📥 Sound uploaded: **{event.filename}**")
    
    async def _on_sound_deleted(self, event: SoundEvent) -> None:
        """Handle sound deletion events."""
        await self._send_notification(f"🗑️ Sound deleted: **{event.filename}**")
    
    async def _on_sound_renamed(self, event: SoundEvent) -> None:
        """Handle sound rename events."""
        await self._send_notification(
            f"✏️ Sound renamed: **{event.filename}** → **{event.new_filename}**"
        )
    
    async def _on_interval_changed(self, event: ConfigEvent) -> None:
        """Handle interval change events."""
        await self._send_notification(
            f"⏱️ Playback interval changed to **{event.value}** seconds"
        )
