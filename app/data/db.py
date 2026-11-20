"""SQLite 存储：清理历史、机器与设置。"""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from typing import Any

from ..core.paths import DB_PATH, ensure_app_dirs

SCHEMA = """
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    item_key TEXT NOT NULL,
    item_label TEXT NOT NULL,
    category TEXT DEFAULT '',
    success INTEGER DEFAULT 0,
    removed_count INTEGER DEFAULT 0,
    freed_bytes INTEGER DEFAULT 0,
    skipped_count INTEGER DEFAULT 0,
    note TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_history_ts ON history(ts);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    total_items INTEGER DEFAULT 0,
    success_items INTEGER DEFAULT 0,
    removed_count INTEGER DEFAULT 0,
    freed_bytes INTEGER DEFAULT 0,
    operator TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS machines (
    hwid TEXT PRIMARY KEY,
    hostname TEXT DEFAULT '',
    username TEXT DEFAULT '',
    first_seen TEXT DEFAULT '',
    last_seen TEXT DEFAULT '',
    note TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT DEFAULT ''
);

-- 在线授权模式下本机缓存的会话（服务端不可用时用于降级放行）
CREATE TABLE IF NOT EXISTS session (
    hwid TEXT PRIMARY KEY,
    code TEXT DEFAULT '',
    plan TEXT DEFAULT '',
    token TEXT DEFAULT '',
    status TEXT DEFAULT 'unused',
    expires_at TEXT DEFAULT '',
    usage_limit INTEGER DEFAULT 0,
    usage_count INTEGER DEFAULT 0,
    bound_machine TEXT DEFAULT '',
    activated_at TEXT DEFAULT '',
    last_verify TEXT DEFAULT ''
);
"""


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Database:
    def __init__(self, path=None) -> None:
        ensure_app_dirs()
        self.path = str(path or DB_PATH)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False, timeout=15)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    # ---------- 基础 ----------
    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur

    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._conn.execute(sql, params).fetchall())

    def close(self) -> None:
        with self._lock:
            try:
                self._conn.close()
            except Exception:
                pass

    # ---------- 历史 ----------
    def add_history(self, item_key, item_label, category, success, removed, freed, skipped, note=""):
        self.execute(
            "INSERT INTO history (ts,item_key,item_label,category,success,removed_count,"
            "freed_bytes,skipped_count,note) VALUES (?,?,?,?,?,?,?,?,?)",
            (now_str(), item_key, item_label, category, 1 if success else 0,
             int(removed), int(freed), int(skipped), note or ""),
        )

    def add_session(self, total, success, removed, freed, operator=""):
        self.execute(
            "INSERT INTO sessions (ts,total_items,success_items,removed_count,freed_bytes,operator)"
            " VALUES (?,?,?,?,?,?)",
            (now_str(), int(total), int(success), int(removed), int(freed), operator or ""),
        )

    def recent_history(self, limit: int = 200) -> list[sqlite3.Row]:
        return self.query("SELECT * FROM history ORDER BY id DESC LIMIT ?", (int(limit),))

    def sessions(self, limit: int = 100) -> list[sqlite3.Row]:
        return self.query("SELECT * FROM sessions ORDER BY id DESC LIMIT ?", (int(limit),))

    def history_stats(self) -> dict:
        row = self.query(
            "SELECT COALESCE(SUM(freed_bytes),0) AS freed, COALESCE(SUM(removed_count),0) AS removed,"
            " COUNT(*) AS runs FROM history"
        )[0]
        return {"freed": row["freed"], "removed": row["removed"], "runs": row["runs"]}

    def clear_history(self) -> None:
        self.execute("DELETE FROM history")
        self.execute("DELETE FROM sessions")

    def trim_history(self, keep: int = 500) -> None:
        self.execute(
            "DELETE FROM history WHERE id NOT IN (SELECT id FROM history ORDER BY id DESC LIMIT ?)",
            (int(keep),),
        )

    # ---------- 设置 ----------
    def get_setting(self, key: str, default: str = "") -> str:
        rows = self.query("SELECT value FROM settings WHERE key=?", (key,))
        return rows[0]["value"] if rows else default

    def set_setting(self, key: str, value: Any) -> None:
        self.execute(
            "INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)", (key, str(value))
        )


_db: Database | None = None
_db_lock = threading.Lock()


def get_db() -> Database:
    global _db
    with _db_lock:
        if _db is None:
            _db = Database()
        return _db
