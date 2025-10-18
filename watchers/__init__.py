import threading
import sqlite3
from collections import defaultdict
from typing import Set

class Watcher:
    """Subclass this to add a new data source"""
    # Declare metrics this watcher produces
    METRIC_KEYS: Set[str] = set()

    def start(self, store: 'DataStore'):
        raise NotImplementedError


class DataStore:
    def __init__(self, db_path: str, watchers: list[Watcher]):
        self.lock = threading.Lock()
        self.db_path = db_path
        # Aggregate all metric keys from registered watchers
        self.metric_keys = set()
        for w in watchers:
            self.metric_keys.update(w.METRIC_KEYS)
        self._init_db()
        self._reset_metrics()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS metrics_log (
                    timestamp TEXT NOT NULL,
                    interval_seconds INTEGER NOT NULL,
                    metric_key TEXT NOT NULL,
                    value INTEGER NOT NULL
                )
            ''')
            conn.commit()

    def _reset_metrics(self):
        with self.lock:
            self.metrics = {key: 0 for key in self.metric_keys}
            self.events = defaultdict(list)
            self.metadata = {}

    def reset(self):
        self._reset_metrics()

    def snapshot(self):
        with self.lock:
            return {
                'metrics': self.metrics.copy(),
                'events': {k: list(v) for k, v in self.events.items()},
                'metadata': self.metadata.copy()
            }

    def save_to_db(self, timestamp: str, interval_seconds: int):
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                rows = [
                    (timestamp, interval_seconds, key, self.metrics.get(key, 0))
                    for key in self.metric_keys
                ]
                conn.executemany(
                    'INSERT INTO metrics_log (timestamp, interval_seconds, metric_key, value) VALUES (?, ?, ?, ?)',
                    rows
                )
                conn.commit()