import threading
from collections import defaultdict

# === SHARED STATE (thread-safe) ===
class DataStore:
    def __init__(self):
        self.lock = threading.Lock()
        self.metrics = defaultdict(int)          # e.g., keystrokes.letter += 1
        self.events = defaultdict(list)          # e.g., window_focus.append(win_id)
        self.metadata = {}                       # e.g., current windows snapshot

    def reset(self):
        with self.lock:
            self.metrics.clear()
            self.events.clear()
            self.metadata.clear()

    def snapshot(self):
        with self.lock:
            return {
                'metrics': dict(self.metrics),
                'events': {k: list(v) for k, v in self.events.items()},
                'metadata': self.metadata.copy()
            }


# === PLUGGABLE WATCHER INTERFACE ===
class Watcher:
    """Subclass this to add a new data source"""
    def start(self, store: DataStore):
        """Launch your watcher in background (e.g., thread)"""
        raise NotImplementedError

