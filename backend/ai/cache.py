from __future__ import annotations

import time
from typing import Any, Callable, Dict, Hashable, Optional, Tuple


class TTLCache:
    """Small in-memory TTL cache for recommendation statistics.

    Render/uvicorn workers are process based, so this intentionally stays in-memory.
    It only speeds up repeated generate requests; PostgreSQL/SQLite remains the source of truth.
    """

    def __init__(self, ttl_seconds: int = 180, max_items: int = 8) -> None:
        self.ttl_seconds = int(ttl_seconds)
        self.max_items = int(max_items)
        self._items: Dict[Hashable, Tuple[float, Any]] = {}

    def get(self, key: Hashable) -> Optional[Any]:
        item = self._items.get(key)
        if not item:
            return None
        created, value = item
        if time.time() - created > self.ttl_seconds:
            self._items.pop(key, None)
            return None
        return value

    def set(self, key: Hashable, value: Any) -> None:
        if len(self._items) >= self.max_items:
            oldest = min(self._items, key=lambda k: self._items[k][0])
            self._items.pop(oldest, None)
        self._items[key] = (time.time(), value)

    def clear(self) -> None:
        self._items.clear()


def draw_signature(con: Callable[[], Any]) -> Tuple[int, int]:
    """Return a cheap DB signature: latest round and row count."""
    try:
        with con() as c:
            row = c.execute("SELECT COALESCE(MAX(round_no),0) AS latest, COUNT(*) AS cnt FROM draws").fetchone()
        if hasattr(row, 'keys'):
            return int(row['latest'] or 0), int(row['cnt'] or 0)
        return int(row[0] or 0), int(row[1] or 0)
    except Exception:
        return 0, 0
