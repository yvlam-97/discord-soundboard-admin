import os
import asyncio
import discord
import sqlite3

from dotenv import load_dotenv
from db_util import ensure_tables_exist

load_dotenv()

async def soundboard_event_watcher(client, notify_channel_id=None, db_path=None):
    if notify_channel_id is None:
        raise RuntimeError("No notify channel ID provided to soundboard_event_watcher")
    if db_path is None:
        raise RuntimeError("No database path provided to soundboard_event_watcher")
    ensure_tables_exist(db_path)
    last_event_id = 0
    while not client.is_closed():
        try:
            with sqlite3.connect(db_path) as conn:
                row = conn.execute("SELECT id, timestamp, event_type, filename, extra FROM soundboard_events ORDER BY id DESC LIMIT 1").fetchone()
            if row:
                event_id, ts, event_type, filename, extra = row
                if event_id is not None and event_id > last_event_id:
                    msg = None
                    if event_type == "upload":
                        msg = f"📥 Sound uploaded: **{filename}**"
                    elif event_type == "rename" and extra:
                        msg = f"✏️ Sound renamed: **{filename}** → **{extra}**"
                    elif event_type == "delete":
                        msg = f"🗑️ Sound deleted: **{filename}**"
                    elif event_type == "interval_change":
                        msg = f"⏱️ Playback interval changed to **{filename}** seconds"
                    if msg:
                        channel = await client.fetch_channel(notify_channel_id)
                        if channel:
                            await channel.send(msg)
                    last_event_id = event_id
            await asyncio.sleep(5)
        except Exception as e:
            print(f"[EventWatcher] Error: {e}")
            await asyncio.sleep(10)
