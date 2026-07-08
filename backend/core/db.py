from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = BASE_DIR / "data" / "bblotto.db"
DB_PATH = Path(os.getenv("BBLOTTO_DB_PATH", str(DEFAULT_DB_PATH)))


def get_db_path() -> Path:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return DB_PATH


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(get_db_path())
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    con.execute("PRAGMA busy_timeout = 5000")
    return con


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    con = connect()
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_db() -> None:
    with db() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL DEFAULT '관리자',
                role TEXT NOT NULL DEFAULT 'admin',
                is_active INTEGER NOT NULL DEFAULT 1,
                failed_login_count INTEGER NOT NULL DEFAULT 0,
                last_login_at TEXT,
                last_login_ip TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS refresh_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                user_agent TEXT,
                ip_address TEXT,
                expires_at TEXT NOT NULL,
                revoked_at TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                FOREIGN KEY(admin_id) REFERENCES admins(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS login_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                username TEXT NOT NULL,
                success INTEGER NOT NULL,
                reason TEXT,
                ip_address TEXT,
                user_agent TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                FOREIGN KEY(admin_id) REFERENCES admins(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                action TEXT NOT NULL,
                target_type TEXT,
                target_id TEXT,
                detail TEXT,
                ip_address TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                FOREIGN KEY(admin_id) REFERENCES admins(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_by INTEGER,
                updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                FOREIGN KEY(updated_by) REFERENCES admins(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_refresh_admin ON refresh_tokens(admin_id);
            CREATE INDEX IF NOT EXISTS idx_login_logs_created ON login_logs(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_system_logs_created ON system_logs(created_at DESC);
            """
        )


def seed_default_admin(username: str = "admin", password: str = "admin1234", display_name: str = "최고관리자") -> bool:
    from .security import hash_password

    init_db()
    with db() as con:
        exists = con.execute("SELECT id FROM admins WHERE username = ?", (username,)).fetchone()
        if exists:
            return False
        con.execute(
            "INSERT INTO admins(username, password_hash, display_name, role) VALUES (?, ?, ?, 'super_admin')",
            (username, hash_password(password), display_name),
        )
        return True
