"""
用户资料、改密、配额（依赖 JWT Bearer 与 DuckDB hongshan_users）。
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from .auth.jwt_auth import verify_token
from .quota_limits import default_quota_payload
from .response_utils import json_fail, json_ok
from .unified_password import hash_password, verify_password

_log = logging.getLogger(__name__)


def _open_writable():
    import os

    from data_pipeline.storage.duckdb_manager import ensure_tables, get_conn, get_db_path

    path = get_db_path()
    if not path or not os.path.isfile(path):
        return None
    conn = get_conn(read_only=False)
    ensure_tables(conn)
    return conn


def _subject_from_bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:].strip()
    payload = verify_token(token)
    if not payload:
        return None
    return str(payload.get("sub") or "").strip() or None


def build_user_router() -> APIRouter:
    r = APIRouter(prefix="/user", tags=["user"])

    @r.get("/profile")
    def get_profile(
        authorization: Optional[str] = Header(None, alias="Authorization"),
    ) -> Any:
        sub = _subject_from_bearer(authorization)
        if not sub:
            raise HTTPException(status_code=401, detail="需要登录")
        conn = _open_writable()
        if not conn:
            raise HTTPException(status_code=503, detail="数据库不可用")
        try:
            row = conn.execute(
                """
                SELECT user_id, username, email, phone, role, status, created_at,
                       display_name, avatar_url,
                       CASE WHEN wechat_openid IS NOT NULL AND LENGTH(TRIM(CAST(wechat_openid AS VARCHAR))) > 0 THEN 1 ELSE 0 END,
                       CASE WHEN feishu_open_id IS NOT NULL AND LENGTH(TRIM(CAST(feishu_open_id AS VARCHAR))) > 0 THEN 1 ELSE 0 END,
                       COALESCE(user_level, 'trial')
                FROM hongshan_users
                WHERE user_id = ? AND status = 'active'
                """,
                [sub],
            ).fetchone()
        finally:
            try:
                conn.close()
            except Exception:
                _log.error("Failed to close database connection", exc_info=True)
        if not row:
            raise HTTPException(status_code=404, detail="用户不存在")
        return json_ok(
            {
                "user_id": str(row[0]),
                "username": str(row[1] or ""),
                "email": str(row[2] or ""),
                "phone": str(row[3] or "") if row[3] else "",
                "role": str(row[4] or "viewer"),
                "status": str(row[5] or ""),
                "created_at": str(row[6]) if row[6] else None,
                "display_name": str(row[7] or "") if len(row) > 7 and row[7] else "",
                "avatar_url": str(row[8] or "") if len(row) > 8 and row[8] else "",
                "wechat_bound": bool(row[9]) if len(row) > 9 else False,
                "feishu_bound": bool(row[10]) if len(row) > 10 else False,
                "user_level": str(row[11] or "trial") if len(row) > 11 else "trial",
            },
            source="user",
        )

    class PatchProfileBody(BaseModel):
        display_name: Optional[str] = Field(None, max_length=128)
        phone: Optional[str] = Field(None, max_length=32)
        avatar_url: Optional[str] = Field(None, max_length=512)

    @r.patch("/profile")
    def patch_profile(
        body: PatchProfileBody,
        authorization: Optional[str] = Header(None, alias="Authorization"),
    ) -> Any:
        sub = _subject_from_bearer(authorization)
        if not sub:
            raise HTTPException(status_code=401, detail="需要登录")
        conn = _open_writable()
        if not conn:
            raise HTTPException(status_code=503, detail="数据库不可用")
        try:
            row = conn.execute(
                "SELECT 1 FROM hongshan_users WHERE user_id = ? AND status = 'active'",
                [sub],
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="用户不存在")
            sets: list[str] = []
            params: list[Any] = []
            if body.display_name is not None:
                sets.append("display_name = ?")
                params.append(body.display_name.strip()[:128] or None)
            if body.phone is not None:
                sets.append("phone = ?")
                params.append(body.phone.strip()[:32] or None)
            if body.avatar_url is not None:
                sets.append("avatar_url = ?")
                params.append(body.avatar_url.strip()[:512] or None)
            if not sets:
                return json_ok({"updated": False}, source="user")
            from datetime import datetime, timezone

            sets.append("updated_at = ?")
            params.append(datetime.now(timezone.utc))
            params.append(sub)
            conn.execute(
                f"UPDATE hongshan_users SET {', '.join(sets)} WHERE user_id = ?",
                params,
            )
        finally:
            try:
                conn.close()
            except Exception:
                _log.error("Failed to close database connection", exc_info=True)
        return json_ok({"updated": True}, source="user")

    class ChangePasswordBody(BaseModel):
        old_password: str = Field(..., min_length=1, max_length=512)
        new_password: str = Field(..., min_length=6, max_length=512)

    @r.post("/change-password")
    def post_change_password(
        body: ChangePasswordBody,
        authorization: Optional[str] = Header(None, alias="Authorization"),
    ) -> Any:
        sub = _subject_from_bearer(authorization)
        if not sub:
            raise HTTPException(status_code=401, detail="需要登录")
        conn = _open_writable()
        if not conn:
            raise HTTPException(status_code=503, detail="数据库不可用")
        try:
            row = conn.execute(
                "SELECT password_hash FROM hongshan_users WHERE user_id = ? AND status = 'active'",
                [sub],
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="用户不存在")
            if not verify_password(body.old_password, str(row[0] or "")):
                raise HTTPException(status_code=400, detail="原密码错误")
            conn.execute(
                "UPDATE hongshan_users SET password_hash = ? WHERE user_id = ?",
                [hash_password(body.new_password), sub],
            )
        finally:
            try:
                conn.close()
            except Exception:
                _log.error("Failed to close database connection", exc_info=True)
        return json_ok({"updated": True}, source="user")

    @r.get("/quota")
    def get_quota(
        request: Request,
        authorization: Optional[str] = Header(None, alias="Authorization"),
    ) -> Any:
        sub = _subject_from_bearer(authorization)
        user_key = sub or (request.client.host if request.client else "anonymous")
        user_level: Optional[str] = None
        if sub:
            conn = _open_writable()
            if conn:
                try:
                    rlv = conn.execute(
                        """
                        SELECT COALESCE(user_level, 'trial') FROM hongshan_users
                        WHERE user_id = ? AND status = 'active'
                        """,
                        [sub],
                    ).fetchone()
                    if rlv:
                        user_level = str(rlv[0] or "trial").strip()
                finally:
                    try:
                        conn.close()
                    except Exception:
                        _log.error("Failed to close database connection", exc_info=True)
        return json_ok(default_quota_payload(user_key, user_level), source="quota")

    return r
