#!/usr/bin/env python3
import time
import os
from datetime import datetime, UTC

from watchers import DataStore
from watchers.keyboard import KeyboardWatcher
from watchers.mouse import MouseWatcher
from watchers.window import WindowWatcher

INTERVAL = 5
OUTPUT_DIR = "productivity_data"
DB_PATH = os.path.join(OUTPUT_DIR, "productivity.db")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def run_core(watchers):
    store = DataStore(DB_PATH, watchers)

    for w in watchers:
        w.start(store)

    print(f"▶️  Core running — saving every {INTERVAL}s to {DB_PATH}")
    try:
        while True:
            time.sleep(INTERVAL)
            timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
            store.save_to_db(timestamp, INTERVAL)
            print(f"✅ Saved to DB at {timestamp}")
            store.reset()
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")


if __name__ == "__main__":
    run_core([
        # DummyWatcher(),
        MouseWatcher(),
        KeyboardWatcher(),
        WindowWatcher(),
    ])
