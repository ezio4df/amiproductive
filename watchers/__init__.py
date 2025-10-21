import os
import sys
import shutil
import json
import copy
from datetime import datetime
import threading
import sqlite3
from typing import Dict, Any, List, Set, Union


class Watcher:
    # Now a dict: {metric_name: default_value}
    METRIC_KEYS: Dict[str, Any] = {}


class DataStore:
    def __init__(self, db_path: str, watchers: List[Watcher]):
        self.lock = threading.Lock()
        self.db_path = db_path
        self.watchers = watchers

        # Build unified metric defaults
        self.metric_defaults: Dict[str, Any] = {}
        for w in watchers:
            if isinstance(w.METRIC_KEYS, set):
                # Auto-upgrade old-style set to dict with 0 defaults
                upgraded = {key: 0 for key in w.METRIC_KEYS}
                self.metric_defaults.update(upgraded)
            else:
                self.metric_defaults.update(w.METRIC_KEYS)

        self._ensure_schema()
        self.reset()

    def _python_to_sql_type(self, value: Any) -> str:
        """Map Python default value to SQLite column type."""
        if isinstance(value, (int, float)):
            return "INTEGER"
        elif isinstance(value, bool):
            return "BOOLEAN"
        elif isinstance(value, str):
            return "TEXT"
        elif isinstance(value, (list, dict, set)):
            return "TEXT"  # JSON stored in TEXT
        else:
            raise TypeError(f"Unsupported metric type: {type(value)} for value {value!r}")

    def _serialize_value(self, value: Any) -> Union[int, bool, str]:
        """Prepare value for SQLite insertion."""
        if isinstance(value, (list, dict, set)):
            return json.dumps(value, ensure_ascii=False, separators=(',', ':'))
        elif isinstance(value, (int, float, bool, str)):
            return value
        else:
            raise TypeError(f"Cannot serialize value of type {type(value)}")

    def _get_table_columns(self) -> Dict[str, str]:
        """Return dict of {column_name: type} in metrics table, or empty dict if missing."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.execute("PRAGMA table_info(metrics);")
                # PRAGMA returns: (cid, name, type, notnull, dflt_value, pk)
                cols = {row[1]: row[2].upper() for row in cur.fetchall()}
                return cols
        except sqlite3.OperationalError:
            return {}

    def _ensure_schema(self):
        # Build expected schema
        expected_cols = {'timestamp': 'TEXT', 'interval_seconds': 'INTEGER'}
        for key, default in self.metric_defaults.items():
            expected_cols[key] = self._python_to_sql_type(default)

        actual_cols = self._get_table_columns()

        if actual_cols == expected_cols:
            return

        print("⚠️  Database schema mismatch or missing.")
        print(f"Expected columns: {expected_cols}")
        print(f"Found columns:    {actual_cols if actual_cols else '(none)'}")
        resp = input("Proceed? This will BACK UP the current DB and create a new one. (y/N): ").strip().lower()
        if resp != 'y':
            print("🛑 Aborted by user.")
            sys.exit(1)

        # Backup if file exists
        if os.path.isfile(self.db_path):
            backup_name = self.db_path + ".bak." + datetime.now().strftime("%Y%m%d_%H%M%S")
            shutil.copy2(self.db_path, backup_name)
            print(f"✅ Backed up to: {backup_name}")

        # Remove old DB
        if os.path.isfile(self.db_path):
            os.remove(self.db_path)

        # Create new DB
        with sqlite3.connect(self.db_path) as conn:
            col_defs = []
            col_defs.append("timestamp TEXT NOT NULL")
            col_defs.append("interval_seconds INTEGER NOT NULL")
            for key, sql_type in list(expected_cols.items())[2:]:  # skip timestamp & interval
                col_defs.append(f'"{key}" {sql_type} NOT NULL')
            conn.execute(f'CREATE TABLE metrics ({", ".join(col_defs)});')
            conn.commit()
        print("✅ Created new database with correct schema.")

    def reset(self):
        with self.lock:
            # Deepcopy to avoid shared mutable state (e.g., lists)
            self.metrics = {
                key: copy.deepcopy(default) for key, default in self.metric_defaults.items()
            }

    def snapshot(self):
        with self.lock:
            return {
                'metrics': copy.deepcopy(self.metrics),
            }

    def save_to_db(self, timestamp: str, interval_seconds: int):
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                col_names = ["timestamp", "interval_seconds"] + [f'"{k}"' for k in self.metric_defaults.keys()]
                placeholders = ",".join(["?"] * len(col_names))
                values = [timestamp, interval_seconds]
                for k in self.metric_defaults.keys():
                    values.append(self._serialize_value(self.metrics[k]))
                conn.execute(f"INSERT INTO metrics ({','.join(col_names)}) VALUES ({placeholders})", values)
                conn.commit()
