import os
from discord import app_commands, Interaction
from tasks.voice_soundboard import get_time_until_next_sound

DB_PATH = os.getenv("SOUNDBOARD_DB_PATH", os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "soundboard.db")))

@app_commands.command(name="nextsound", description="Show time left until next sound is played.")
async def nextsound_command(interaction: Interaction):
    time_left = get_time_until_next_sound(DB_PATH)
    if time_left == 0:
        await interaction.response.send_message("A sound can be played now!")
    else:
        await interaction.response.send_message(f"Next sound in {time_left} seconds.")
