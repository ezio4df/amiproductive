#!/usr/bin/env python3
import time
import os
from datetime import datetime

from watchers import DataStore
from watchers.mouse import MouseWatcher

# === CONFIG ===
INTERVAL = 5
OUTPUT_DIR = "productivity_data"
DB_PATH = os.path.join(OUTPUT_DIR, "productivity.db")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def run_core(watchers: list):
    store = DataStore(DB_PATH, watchers)  # ← passes watchers to infer schema

    for w in watchers:
        w.start(store)

    print(f"▶️  Core running — saving every {INTERVAL}s to {DB_PATH}")
    try:
        while True:
            time.sleep(INTERVAL)
            timestamp = datetime.utcnow().isoformat()
            store.save_to_db(timestamp, INTERVAL)
            print(f"✅ Saved metrics to DB at {timestamp}")
            store.reset()

    except KeyboardInterrupt:
        print("\n🛑 Stopping...")

if __name__ == "__main__":
    watchers = [
        MouseWatcher(),
        # Add more watchers here later — no config changes needed!
    ]
    run_core(watchers)