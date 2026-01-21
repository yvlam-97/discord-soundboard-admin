"""
Volume command - Adjust the soundboard playback volume.
"""

import discord
from discord import app_commands, Interaction

from core.events import EventType, ConfigEvent


@app_commands.command(name="volume", description="Set the soundboard playback volume")
@app_commands.describe(level="Volume level (0-100)")
async def volume_command(interaction: Interaction, level: int):
    """Set the playback volume."""
    # Validate range
    if not 0 <= level <= 100:
        await interaction.response.send_message(
            "❌ Volume must be between 0 and 100",
            ephemeral=True
        )
        return
    
    # Get services from bot
    bot = interaction.client
    config_repo = bot.config_repository
    event_bus = bot.event_bus
    
    # Update volume
    old_volume = config_repo.get_volume()
    config_repo.set_volume(level)
    
    # Publish event
    await event_bus.publish(ConfigEvent(
        event_type=EventType.VOLUME_CHANGED,
        key="volume",
        value=level,
        old_value=old_volume
    ))
    
    # Response with emoji based on level
    if level == 0:
        emoji = "🔇"
    elif level < 33:
        emoji = "🔈"
    elif level < 66:
        emoji = "🔉"
    else:
        emoji = "🔊"
    
    await interaction.response.send_message(
        f"{emoji} Volume changed from **{old_volume}%** to **{level}%**"
    )
