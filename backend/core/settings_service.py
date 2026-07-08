from __future__ import annotations

import json
from typing import Any, Dict, Optional

from .auth_service import log_system
from .db import db, init_db


def get_setting(key: str, default: Any = None) -> Any:
    init_db()
    with db() as con:
        row = con.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    if not row:
        return default
    try:
        return json.loads(row["value"])
    except Exception:
        return row["value"]


def set_setting(key: str, value: Any, admin_id: Optional[int] = None, ip_address: str = "") -> None:
    init_db()
    encoded = json.dumps(value, ensure_ascii=False)
    with db() as con:
        con.execute(
            """
            INSERT INTO settings(key, value, updated_by, updated_at)
            VALUES (?, ?, ?, datetime('now','localtime'))
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_by = excluded.updated_by, updated_at = datetime('now','localtime')
            """,
            (key, encoded, admin_id),
        )
    log_system(admin_id, "setting_update", "settings", key, encoded[:500], ip_address)


def all_settings() -> Dict[str, Any]:
    init_db()
    result: Dict[str, Any] = {}
    with db() as con:
        rows = con.execute("SELECT key, value FROM settings ORDER BY key").fetchall()
    for row in rows:
        try:
            result[row["key"]] = json.loads(row["value"])
        except Exception:
            result[row["key"]] = row["value"]
    return result
