from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from .db import db, init_db
from .security import (
    REFRESH_TOKEN_SECONDS,
    create_access_token,
    create_refresh_token,
    hash_password,
    token_hash,
    verify_access_token,
    verify_password,
)


def _now_sql() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _expires_sql(seconds: int) -> str:
    return (datetime.now() + timedelta(seconds=seconds)).strftime("%Y-%m-%d %H:%M:%S")


def log_system(admin_id: Optional[int], action: str, target_type: str = "system", target_id: str = "", detail: str = "", ip_address: str = "") -> None:
    init_db()
    with db() as con:
        con.execute(
            "INSERT INTO system_logs(admin_id, action, target_type, target_id, detail, ip_address) VALUES (?, ?, ?, ?, ?, ?)",
            (admin_id, action, target_type, target_id, detail, ip_address),
        )


def create_admin(username: str, password: str, display_name: str = "관리자", role: str = "admin", created_by: Optional[int] = None) -> Dict[str, Any]:
    init_db()
    username = username.strip()
    if not username or len(password) < 8:
        raise ValueError("아이디와 8자리 이상 비밀번호가 필요합니다.")
    with db() as con:
        cur = con.execute(
            "INSERT INTO admins(username, password_hash, display_name, role) VALUES (?, ?, ?, ?)",
            (username, hash_password(password), display_name.strip() or username, role),
        )
        admin_id = cur.lastrowid
    log_system(created_by, "admin_create", "admin", str(admin_id), f"username={username}")
    return {"id": admin_id, "username": username, "display_name": display_name, "role": role}


def login(username: str, password: str, ip_address: str = "", user_agent: str = "") -> Dict[str, Any]:
    init_db()
    username = username.strip()
    with db() as con:
        row = con.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
        if not row or not int(row["is_active"]):
            con.execute(
                "INSERT INTO login_logs(username, success, reason, ip_address, user_agent) VALUES (?, 0, ?, ?, ?)",
                (username, "inactive_or_not_found", ip_address, user_agent),
            )
            raise PermissionError("아이디 또는 비밀번호가 올바르지 않습니다.")
        if not verify_password(password, row["password_hash"]):
            con.execute("UPDATE admins SET failed_login_count = failed_login_count + 1, updated_at = ? WHERE id = ?", (_now_sql(), row["id"]))
            con.execute(
                "INSERT INTO login_logs(admin_id, username, success, reason, ip_address, user_agent) VALUES (?, ?, 0, ?, ?, ?)",
                (row["id"], username, "bad_password", ip_address, user_agent),
            )
            raise PermissionError("아이디 또는 비밀번호가 올바르지 않습니다.")

        refresh = create_refresh_token()
        expires_at = _expires_sql(REFRESH_TOKEN_SECONDS)
        con.execute(
            "INSERT INTO refresh_tokens(admin_id, token_hash, user_agent, ip_address, expires_at) VALUES (?, ?, ?, ?, ?)",
            (row["id"], token_hash(refresh), user_agent, ip_address, expires_at),
        )
        con.execute(
            "UPDATE admins SET failed_login_count = 0, last_login_at = ?, last_login_ip = ?, updated_at = ? WHERE id = ?",
            (_now_sql(), ip_address, _now_sql(), row["id"]),
        )
        con.execute(
            "INSERT INTO login_logs(admin_id, username, success, reason, ip_address, user_agent) VALUES (?, ?, 1, 'ok', ?, ?)",
            (row["id"], username, ip_address, user_agent),
        )

    access = create_access_token(row["id"], row["username"], row["role"])
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "admin": {"id": row["id"], "username": row["username"], "display_name": row["display_name"], "role": row["role"]},
    }


def refresh(refresh_token: str, ip_address: str = "", user_agent: str = "") -> Dict[str, Any]:
    init_db()
    hashed = token_hash(refresh_token)
    with db() as con:
        row = con.execute(
            """
            SELECT rt.*, a.username, a.role, a.display_name, a.is_active
            FROM refresh_tokens rt
            JOIN admins a ON a.id = rt.admin_id
            WHERE rt.token_hash = ? AND rt.revoked_at IS NULL AND datetime(rt.expires_at) > datetime('now','localtime')
            """,
            (hashed,),
        ).fetchone()
        if not row or not int(row["is_active"]):
            raise PermissionError("로그인 유지 토큰이 만료되었습니다.")
        access = create_access_token(row["admin_id"], row["username"], row["role"])
    return {
        "access_token": access,
        "token_type": "bearer",
        "admin": {"id": row["admin_id"], "username": row["username"], "display_name": row["display_name"], "role": row["role"]},
    }


def logout(refresh_token: str, admin_id: Optional[int] = None) -> None:
    init_db()
    with db() as con:
        con.execute("UPDATE refresh_tokens SET revoked_at = ? WHERE token_hash = ?", (_now_sql(), token_hash(refresh_token)))
    log_system(admin_id, "logout", "auth", "", "refresh token revoked")


def current_admin(access_token: str) -> Dict[str, Any]:
    payload = verify_access_token(access_token)
    if not payload:
        raise PermissionError("로그인이 만료되었습니다.")
    admin_id = int(payload["sub"])
    with db() as con:
        row = con.execute("SELECT id, username, display_name, role, is_active, last_login_at FROM admins WHERE id = ?", (admin_id,)).fetchone()
        if not row or not int(row["is_active"]):
            raise PermissionError("비활성 관리자입니다.")
    return dict(row)
