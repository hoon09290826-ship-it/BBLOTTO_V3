from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any, Dict, Optional

PASSWORD_ITERATIONS = 180_000
SECRET_KEY = os.getenv("BBLOTTO_SECRET_KEY", "CHANGE_ME_BBLOTTO_RC2_SPRINT2_SECRET")
ACCESS_TOKEN_SECONDS = int(os.getenv("BBLOTTO_ACCESS_TOKEN_SECONDS", "1800"))
REFRESH_TOKEN_SECONDS = int(os.getenv("BBLOTTO_REFRESH_TOKEN_SECONDS", str(60 * 60 * 24 * 14)))


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_b64, digest_b64 = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), _unb64(salt_b64), int(iterations))
        return hmac.compare_digest(_b64(digest), digest_b64)
    except Exception:
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(admin_id: int, username: str, role: str, expires_in: int = ACCESS_TOKEN_SECONDS) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {"sub": str(admin_id), "username": username, "role": role, "iat": now, "exp": now + expires_in}
    signing_input = f"{_b64(json.dumps(header, separators=(',', ':')).encode())}.{_b64(json.dumps(payload, separators=(',', ':')).encode())}"
    signature = hmac.new(SECRET_KEY.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64(signature)}"


def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
        signing_input = f"{header_b64}.{payload_b64}"
        expected = _b64(hmac.new(SECRET_KEY.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest())
        if not hmac.compare_digest(expected, sig_b64):
            return None
        payload = json.loads(_unb64(payload_b64))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except Exception:
        return None


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)
