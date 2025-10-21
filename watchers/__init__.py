import sys
import shutil
from datetime import datetime
import threading
import sqlite3
from collections import defaultdict
from typing import Set, List


class Watcher:
    METRIC_KEYS: Set[str] = set()

    def start(self, store: 'DataStore'):
        raise NotImplementedError


class DataStore:
    def __init__(self, db_path: str, watchers: List[Watcher]):
        self.lock = threading.Lock()
        self.db_path = db_path
        self.watchers = watchers
        self.metric_keys = sorted({key for w in watchers for key in w.METRIC_KEYS})

        self._ensure_schema()
        self.reset()

    def _get_table_columns(self) -> Set[str]:
        """Return set of column names in the metrics table, or empty set if table missing."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.execute("PRAGMA table_info(metrics);")
                cols = {row[1] for row in cur.fetchall()}
                return cols
        except sqlite3.OperationalError:
            return set()

    def _ensure_schema(self):
        expected_cols = {'timestamp', 'interval_seconds'} | set(self.metric_keys)
        actual_cols = self._get_table_columns()

        if actual_cols == expected_cols:
            return  # schema matches

        # Schema mismatch or missing table
        print("⚠️  Database schema mismatch or missing.")
        print(f"Expected columns: {sorted(expected_cols)}")
        print(f"Found columns:    {sorted(actual_cols) if actual_cols else '(none)'}")
        resp = input("Proceed? This will BACK UP the current DB and create a new one. (y/N): ").strip().lower()
        if resp != 'y':
            print("🛑 Aborted by user.")
            sys.exit(1)

        # Backup
        backup_name = self.db_path + ".bak." + datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(self.db_path, backup_name)
        print(f"✅ Backed up to: {backup_name}")

        # Create new DB with correct schema
        with sqlite3.connect(self.db_path) as conn:
            cols_def = ", ".join([f'"{key}" INTEGER NOT NULL' for key in self.metric_keys])
            conn.execute(f'''
                CREATE TABLE metrics (
                    timestamp TEXT NOT NULL,
                    interval_seconds INTEGER NOT NULL,
                    {cols_def}
                )
            ''')
            conn.commit()

    def reset(self):
        with self.lock:
            self.metrics = {key: 0 for key in self.metric_keys}
            self.events = defaultdict(list)
            self.metadata = {}

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
                col_names = ",".join(['timestamp', 'interval_seconds'] + [f'"{k}"' for k in self.metric_keys])
                placeholders = ",".join(["?"] * (2 + len(self.metric_keys)))
                values = [timestamp, interval_seconds] + [self.metrics.get(k, 0) for k in self.metric_keys]
                conn.execute(f"INSERT INTO metrics ({col_names}) VALUES ({placeholders})", values)
                conn.commit()
