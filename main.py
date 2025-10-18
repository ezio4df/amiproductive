#!/usr/bin/env python3
import time
import json
import os
from datetime import datetime

from watchers import Watcher, DataStore
from watchers.mouse import MouseWatcher

# === CONFIG ===
INTERVAL = 5
OUTPUT_DIR = "productivity_data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

    
# Global store
store = DataStore()

# === CORE ENGINE ===
def run_core(watchers: list[Watcher]):
    # Start all watchers
    for w in watchers:
        w.start(store)

    print(f"▶️  Core running — saving every {INTERVAL}s to {OUTPUT_DIR}")
    try:
        while True:
            time.sleep(INTERVAL)

            # Save current state
            data = {
                "timestamp": datetime.utcnow().isoformat(),
                "interval_seconds": INTERVAL,
                **store.snapshot()
            }
            print(data)

            filename = f"{OUTPUT_DIR}/log_{int(time.time())}.json"
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"✅ Saved {filename}")

            # Reset for next interval
            store.reset()

    except KeyboardInterrupt:
        print("\n🛑 Stopping...")

# === RUN (for testing) ===
if __name__ == "__main__":
    run_core([
        # DummyWatcher(),
        MouseWatcher(),
    ])