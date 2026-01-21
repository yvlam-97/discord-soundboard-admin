"""
List command - Shows all available sounds.
"""

import discord
from discord import app_commands, Interaction


@app_commands.command(name="list", description="Show all available sounds in the soundboard")
async def list_command(interaction: Interaction):
    """List all available sounds."""
    # Get sound repository from bot
    sound_repo = interaction.client.sound_repository
    
    filenames = sound_repo.get_all_filenames()
    
    if not filenames:
        await interaction.response.send_message(
            "🔇 No sounds available. Upload some sounds via the web interface!",
            ephemeral=True
        )
        return
    
    # Create embed
    embed = discord.Embed(
        title="🎵 Sound Library",
        description=f"**{len(filenames)}** sounds available",
        color=discord.Color.blurple()
    )
    
    # Group sounds in chunks for display
    chunk_size = 15
    sound_chunks = [filenames[i:i + chunk_size] for i in range(0, len(filenames), chunk_size)]
    
    for i, chunk in enumerate(sound_chunks[:3]):  # Limit to 3 fields (45 sounds)
        sounds_text = "\n".join(f"• `{name}`" for name in chunk)
        field_name = "Sounds" if i == 0 else f"Sounds (cont.)"
        embed.add_field(name=field_name, value=sounds_text, inline=False)
    
    if len(sound_chunks) > 3:
        remaining = len(filenames) - 45
        embed.set_footer(text=f"... and {remaining} more sounds")
    
    await interaction.response.send_message(embed=embed)
