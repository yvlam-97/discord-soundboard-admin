from discord import app_commands, Interaction


@app_commands.command(name="ping", description="Ping the bot and get a response.")
async def ping_command(interaction: Interaction):
    await interaction.response.send_message(f"🔊 Pong! Audio Ambush is ready, {interaction.user.mention}!")