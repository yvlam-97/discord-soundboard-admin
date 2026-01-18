from discord import app_commands, Interaction

# Define the hello slash command in this module
@app_commands.command(name="ping", description="Ping the bot and get a response.")
async def ping_command(interaction: Interaction):
    await interaction.response.send_message(f"Bucc or no succ, {interaction.user.mention}?")