"""FastAPI 연동용 인증 라우터.

기존 backend/app.py 가 있는 프로젝트에서는 아래처럼 붙이면 됩니다.

    from backend.core.fastapi_auth_routes import router as auth_router
    app.include_router(auth_router)

FastAPI가 설치되지 않은 환경에서도 ZIP 업로드/테스트가 깨지지 않도록 import를 안전하게 처리합니다.
"""
from __future__ import annotations

try:
    from fastapi import APIRouter, Header, HTTPException, Request
    from pydantic import BaseModel
except Exception:  # pragma: no cover
    APIRouter = None  # type: ignore
    BaseModel = object  # type: ignore

from .auth_service import current_admin, login, logout, refresh
from .db import init_db, seed_default_admin
from .settings_service import all_settings, set_setting

if APIRouter:
    router = APIRouter(prefix="/api/auth", tags=["auth"])
else:  # pragma: no cover
    router = None


class LoginBody(BaseModel):
    username: str
    password: str


class RefreshBody(BaseModel):
    refresh_token: str


class SettingBody(BaseModel):
    key: str
    value: object


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    return authorization.split(" ", 1)[1].strip()


if APIRouter:
    @router.on_event("startup")
    def _startup() -> None:
        init_db()
        seed_default_admin()

    @router.post("/login")
    def api_login(body: LoginBody, request: Request):
        try:
            return login(body.username, body.password, request.client.host if request.client else "", request.headers.get("user-agent", ""))
        except PermissionError as exc:
            raise HTTPException(status_code=401, detail=str(exc))

    @router.post("/refresh")
    def api_refresh(body: RefreshBody, request: Request):
        try:
            return refresh(body.refresh_token, request.client.host if request.client else "", request.headers.get("user-agent", ""))
        except PermissionError as exc:
            raise HTTPException(status_code=401, detail=str(exc))

    @router.post("/logout")
    def api_logout(body: RefreshBody, authorization: str | None = Header(default=None)):
        admin_id = None
        try:
            admin_id = current_admin(_bearer(authorization))["id"]
        except Exception:
            pass
        logout(body.refresh_token, admin_id)
        return {"ok": True}

    @router.get("/me")
    def api_me(authorization: str | None = Header(default=None)):
        try:
            return current_admin(_bearer(authorization))
        except PermissionError as exc:
            raise HTTPException(status_code=401, detail=str(exc))

    @router.get("/settings")
    def api_settings(authorization: str | None = Header(default=None)):
        try:
            current_admin(_bearer(authorization))
            return all_settings()
        except PermissionError as exc:
            raise HTTPException(status_code=401, detail=str(exc))

    @router.post("/settings")
    def api_set_setting(body: SettingBody, request: Request, authorization: str | None = Header(default=None)):
        try:
            admin = current_admin(_bearer(authorization))
            set_setting(body.key, body.value, admin["id"], request.client.host if request.client else "")
            return {"ok": True}
        except PermissionError as exc:
            raise HTTPException(status_code=401, detail=str(exc))
