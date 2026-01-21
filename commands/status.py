"""
Status command - Shows bot status and configuration.
"""

import discord
from discord import app_commands, Interaction


@app_commands.command(name="status", description="Show the soundboard bot's current status")
async def status_command(interaction: Interaction):
    """Display current bot status."""
    # Get services and repos from bot
    bot = interaction.client
    soundboard_service = bot.soundboard_service
    sound_repo = bot.sound_repository
    
    # Gather status info
    is_running = soundboard_service.is_running
    interval = soundboard_service.interval
    volume = soundboard_service.volume
    sound_count = len(sound_repo.get_all_filenames())
    voice_client = bot.voice_clients[0] if bot.voice_clients else None
    
    # Create embed
    embed = discord.Embed(
        title="📊 Soundboard Status",
        color=discord.Color.green() if is_running else discord.Color.red()
    )
    
    # Service status
    status_emoji = "🟢" if is_running else "🔴"
    status_text = "Active" if is_running else "Stopped"
    embed.add_field(
        name="Service Status",
        value=f"{status_emoji} {status_text}",
        inline=True
    )
    
    # Voice connection
    if voice_client and voice_client.is_connected():
        channel_name = voice_client.channel.name
        guild_name = voice_client.guild.name
        voice_text = f"🔊 Connected to **{channel_name}** in {guild_name}"
    else:
        voice_text = "🔇 Not connected"
    embed.add_field(
        name="Voice Connection",
        value=voice_text,
        inline=False
    )
    
    # Configuration
    embed.add_field(
        name="⏱️ Interval",
        value=f"{interval} seconds",
        inline=True
    )
    
    embed.add_field(
        name="🔊 Volume",
        value=f"{volume}%",
        inline=True
    )
    
    embed.add_field(
        name="🎵 Sounds",
        value=f"{sound_count} available",
        inline=True
    )
    
    # Bot info
    embed.set_footer(text=f"Bot Latency: {round(bot.latency * 1000)}ms")
    
    await interaction.response.send_message(embed=embed)
