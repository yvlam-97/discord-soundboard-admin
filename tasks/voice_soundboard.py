
import os
import asyncio
import random
import discord
import sqlite3
import tempfile


# Use SOUNDBOARD_DB_PATH from environment or default to soundboard.db in the root
DB_PATH = os.getenv("SOUNDBOARD_DB_PATH", os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "soundboard.db")))

# Ensure the interval table exists
def init_interval_table():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS interval_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            interval INTEGER NOT NULL
        )
        """)
        # Insert default interval if not present
        cur = conn.execute("SELECT interval FROM interval_config WHERE id = 1")
        if cur.fetchone() is None:
            conn.execute("INSERT INTO interval_config (id, interval) VALUES (1, 30)")

init_interval_table()

async def play_random_sound(vc):
    # Fetch a random sound from the SQLite database
    try:
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute("SELECT filename, data FROM sounds ORDER BY RANDOM() LIMIT 1").fetchone()
        if not row:
            print("No sound files found in database.")
            return
        filename, data = row
        # Write to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        source = discord.FFmpegPCMAudio(tmp_path)
        vc.play(source)
        while vc.is_playing():
            await asyncio.sleep(1)
        await vc.disconnect()
        os.remove(tmp_path)
    except Exception as e:
        print(f"Error playing sound: {e}")

async def periodic_voice_task(client, interval=None):
    await client.wait_until_ready()
    while not client.is_closed():
        try:
            # Get the current interval from the database
            with sqlite3.connect(DB_PATH) as conn:
                row = conn.execute("SELECT interval FROM interval_config WHERE id = 1").fetchone()
                current_interval = row[0] if row else 30
                sound_count = conn.execute("SELECT COUNT(*) FROM sounds").fetchone()[0]
                print(f"[Voice Task] Current interval: {current_interval} seconds")
            if sound_count == 0:
                print("No sound files found in database. Bot will not connect to voice channels.")
                await asyncio.sleep(current_interval)
                continue
            for guild in client.guilds:
                # Find the voice channel with the most members
                voice_channels = [c for c in guild.voice_channels if len(c.members) > 0]
                if not voice_channels:
                    continue
                target_channel = max(voice_channels, key=lambda c: len(c.members))
                # Only join if not already connected
                if guild.voice_client is None or not guild.voice_client.is_connected():
                    vc = await target_channel.connect()
                    await play_random_sound(vc)
        except Exception as e:
            print(f"Error in periodic voice task: {e}")
        await asyncio.sleep(current_interval)
