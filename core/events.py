"""
Event bus implementation for publish/subscribe pattern.

This replaces database polling with an event-driven architecture.
"""

import asyncio
from abc import ABC
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Coroutine, Any, TypeVar, Generic
from collections import defaultdict


class EventType(Enum):
    """Types of events that can be published."""

    # Sound events
    SOUND_UPLOADED = auto()
    SOUND_DELETED = auto()
    SOUND_RENAMED = auto()

    # Config events
    INTERVAL_CHANGED = auto()
    VOLUME_CHANGED = auto()

    # System events
    BOT_READY = auto()
    SHUTDOWN = auto()


@dataclass
class Event(ABC):
    """Base class for all events."""
    event_type: EventType
    source: str | None = field(default=None, kw_only=True)  # e.g., "web", "command", None for system


@dataclass
class SoundEvent(Event):
    """Event related to sound files."""
    filename: str
    new_filename: str | None = None  # Used for rename events


@dataclass
class ConfigEvent(Event):
    """Event related to configuration changes."""
    key: str
    value: Any
    old_value: Any = None


@dataclass
class SystemEvent(Event):
    """System-level events."""
    pass


# Type for event handlers
EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """
    Async event bus for publish/subscribe pattern.

    Allows components to subscribe to specific event types and
    receive notifications when those events are published.

    Usage:
        event_bus = EventBus()

        async def on_sound_uploaded(event: SoundEvent):
            print(f"Sound uploaded: {event.filename}")

        event_bus.subscribe(EventType.SOUND_UPLOADED, on_sound_uploaded)

        await event_bus.publish(SoundEvent(
            event_type=EventType.SOUND_UPLOADED,
            filename="test.mp3"
        ))
    """

    def __init__(self):
        self._handlers: dict[EventType, list[EventHandler]] = defaultdict(list)
        self._lock = asyncio.Lock()

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """
        Subscribe a handler to a specific event type.

        Args:
            event_type: The type of event to subscribe to
            handler: Async function to call when event is published
        """
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> bool:
        """
        Unsubscribe a handler from an event type.

        Args:
            event_type: The type of event to unsubscribe from
            handler: The handler to remove

        Returns:
            True if handler was removed, False if it wasn't subscribed
        """
        try:
            self._handlers[event_type].remove(handler)
            return True
        except ValueError:
            return False

    async def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribed handlers.

        Handlers are called concurrently using asyncio.gather.
        Exceptions in handlers are logged but don't stop other handlers.

        Args:
            event: The event to publish
        """
        handlers = self._handlers.get(event.event_type, [])
        if not handlers:
            return

        async def safe_call(handler: EventHandler) -> None:
            try:
                await handler(event)
            except Exception as e:
                print(f"[EventBus] Error in handler for {event.event_type}: {e}")

        await asyncio.gather(*[safe_call(h) for h in handlers])

    def clear(self) -> None:
        """Remove all subscriptions."""
        self._handlers.clear()


# Global event bus instance for the application
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get or create the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def set_event_bus(event_bus: EventBus) -> None:
    """Set the global event bus instance (useful for testing)."""
    global _event_bus
    _event_bus = event_bus
