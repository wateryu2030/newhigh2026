"""
与 Vue 红山客户端 / Next 登录共用的认证路由：用户落在 DuckDB（hongshan_users）。
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from .auth.jwt_auth import create_access_token
from .unified_password import hash_password, verify_password

_log = logging.getLogger(__name__)


class LoginBody(BaseModel):
    username: str = Field(default="", max_length=256)
    password: str = Field(default="", max_length=512)


class RegisterBody(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: str = Field(..., min_length=3, max_length=256)
    password: str = Field(..., min_length=6, max_length=256)
    phone: Optional[str] = None

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, v: str) -> str:
        s = (v or "").strip()
        if "@" not in s or len(s.split("@")) != 2:
            raise ValueError("邮箱格式不正确")
        local, domain = s.split("@", 1)
        if not local or not domain or "." not in domain:
            raise ValueError("邮箱格式不正确")
        return s


def _login_response_dict(
    token: str, user_id: str, username: str, role: str = "viewer"
) -> dict[str, Any]:
    return {
        "token": token,
        "access_token": token,
        "token_type": "bearer",
        "user_id": user_id,
        "username": username,
        "user": username,
        "role": role,
    }


def _open_writable():
    import os

    from data_pipeline.storage.duckdb_manager import ensure_tables, get_conn, get_db_path

    path = get_db_path()
    if not path or not os.path.isfile(path):
        return None
    conn = get_conn(read_only=False)
    ensure_tables(conn)
    return conn


def build_unified_auth_router() -> APIRouter:
    r = APIRouter(prefix="/auth", tags=["auth"])

    @r.post("/login")
    def post_login(body: LoginBody) -> dict:
        username = (body.username or "").strip() or "demo"
        password = body.password or ""
        conn = _open_writable()
        try:
            if conn:
                row = conn.execute(
                    """
                    SELECT user_id, username, password_hash, role
                    FROM hongshan_users
                    WHERE username = ? AND status = 'active'
                    """,
                    [username],
                ).fetchone()
                if row:
                    uid, uname, ph = str(row[0]), str(row[1]), str(row[2] or "")
                    urole = str(row[3]).strip().lower() if len(row) > 3 and row[3] else "viewer"
                    if urole not in ("viewer", "operator", "admin"):
                        urole = "viewer"
                    if not verify_password(password, ph):
                        raise HTTPException(status_code=401, detail="用户名或密码错误")
                    token = create_access_token(subject=uid, extra_claims={"role": urole})
                    return _login_response_dict(token, uid, uname, urole)
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

        if password:
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        try:
            token = create_access_token(subject=username, extra_claims={"role": "viewer"})
        except Exception:
            token = "stub_token_placeholder"
        return _login_response_dict(token, "demo-user", username, "viewer")

    @r.post("/register")
    def post_register(body: RegisterBody) -> dict:
        conn = _open_writable()
        if not conn:
            raise HTTPException(status_code=503, detail="数据库不可用，无法注册")
        try:
            if conn.execute(
                "SELECT 1 FROM hongshan_users WHERE username = ? LIMIT 1",
                [body.username],
            ).fetchone():
                raise HTTPException(status_code=400, detail="用户名已存在")
            if conn.execute(
                "SELECT 1 FROM hongshan_users WHERE email = ? LIMIT 1",
                [str(body.email)],
            ).fetchone():
                raise HTTPException(status_code=400, detail="邮箱已被注册")
            uid = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            conn.execute(
                """
                INSERT INTO hongshan_users (user_id, username, email, phone, password_hash, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'active', ?)
                """,
                [
                    uid,
                    body.username,
                    str(body.email),
                    (body.phone or "").strip() or None,
                    hash_password(body.password),
                    now,
                ],
            )
            conn.execute(
                """
                INSERT INTO hongshan_accounts (user_id, available_cash, frozen_cash, total_assets, updated_at)
                VALUES (?, 500000, 0, 500000, ?)
                """,
                [uid, now],
            )
            return {
                "id": uid,
                "username": body.username,
                "email": str(body.email),
                "phone": body.phone or "",
                "status": "active",
                "created_at": now.isoformat(),
            }
        except HTTPException:
            raise
        except Exception as e:
            _log.exception("register failed")
            raise HTTPException(status_code=500, detail=str(e)[:200]) from e
        finally:
            try:
                conn.close()
            except Exception:
                pass

    return r
