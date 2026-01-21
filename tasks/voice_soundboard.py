
import asyncio
import discord
import sqlite3
import tempfile
from db_util import ensure_tables_exist

async def play_random_sound(vc, db_path):
    # Fetch a random sound from the SQLite database
    try:
        with sqlite3.connect(db_path) as conn:
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
        # Update last played timestamp in the database
        import time
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE soundboard_state SET last_played = ? WHERE id = 1", (int(time.time()),))
    except Exception as e:
        print(f"Error playing sound: {e}")


async def periodic_voice_task(client, interval=None, db_path=None):
    if db_path is None:
        raise RuntimeError("No database path provided to soundboard_event_watcher")
    ensure_tables_exist(db_path)
    await client.wait_until_ready()
    sleep_step = 1  # seconds
    while not client.is_closed():
        try:
            # Get the current interval and sound count from the database
            with sqlite3.connect(db_path) as conn:
                row = conn.execute("SELECT interval FROM interval_config WHERE id = 1").fetchone()
                current_interval = row[0] if row else 30
                sound_count = conn.execute("SELECT COUNT(*) FROM sounds").fetchone()[0]
                print(f"[Voice Task] Current interval: {current_interval} seconds")
            if sound_count == 0:
                print("No sound files found in database. Bot will not connect to voice channels.")
                # Sleep in small steps, re-check interval each second
                slept = 0
                while slept < current_interval:
                    await asyncio.sleep(sleep_step)
                    slept += sleep_step
                    with sqlite3.connect(db_path) as conn:
                        row = conn.execute("SELECT interval FROM interval_config WHERE id = 1").fetchone()
                        new_interval = row[0] if row else 30
                    if new_interval != current_interval:
                        print(f"Interval changed to {new_interval}, restarting wait.")
                        current_interval = new_interval
                        slept = 0
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
                    await play_random_sound(vc, db_path)
        except Exception as e:
            print(f"Error in periodic voice task: {e}")
        # Sleep in small steps, re-check interval each second
        slept = 0
        with sqlite3.connect(db_path) as conn:
            row = conn.execute("SELECT interval FROM interval_config WHERE id = 1").fetchone()
            current_interval = row[0] if row else 30
        while slept < current_interval:
            await asyncio.sleep(sleep_step)
            slept += sleep_step
            with sqlite3.connect(db_path) as conn:
                row = conn.execute("SELECT interval FROM interval_config WHERE id = 1").fetchone()
                new_interval = row[0] if row else 30
            if new_interval != current_interval:
                print(f"Interval changed to {new_interval}, restarting wait.")
                current_interval = new_interval
                slept = 0