"""
微信网页授权 URL（占位）与小程序 code 换 JWT。
需配置：WECHAT_MINIPROGRAM_APPID、WECHAT_MINIPROGRAM_SECRET；
公众号网页授权：WECHAT_MP_APPID、WECHAT_OAUTH_REDIRECT_URI（可选）。
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .auth.jwt_auth import create_access_token
from .response_utils import json_fail, json_ok
from .unified_password import hash_password

_log = logging.getLogger(__name__)


class MiniProgramBody(BaseModel):
    code: str = Field(..., min_length=4, max_length=256)


def _open_writable():
    import os as _os

    from data_pipeline.storage.duckdb_manager import ensure_tables, get_conn, get_db_path

    path = get_db_path()
    if not path or not _os.path.isfile(path):
        return None
    conn = get_conn(read_only=False)
    ensure_tables(conn)
    return conn


def build_wechat_auth_routes() -> APIRouter:
    r = APIRouter(prefix="/auth", tags=["wechat"])

    @r.get("/wechat/url")
    def wechat_oauth_url(redirect: str = "/") -> dict[str, Any]:
        """返回公众号网页授权 URL；未配置 appid 时仅说明字段。"""
        appid = os.environ.get("WECHAT_MP_APPID", "").strip()
        if not appid:
            return json_ok(
                {
                    "configured": False,
                    "authorize_url": None,
                    "hint": "设置环境变量 WECHAT_MP_APPID、WECHAT_MP_SECRET 与合法 redirect_uri 后可用",
                },
                source="wechat",
            )
        redir = os.environ.get("WECHAT_OAUTH_REDIRECT_URI", "").strip() or "https://example.com/api/auth/wechat/callback"
        scope = "snsapi_userinfo"
        state = "newhigh"
        url = (
            f"https://open.weixin.qq.com/connect/oauth2/authorize?appid={appid}"
            f"&redirect_uri={__import__('urllib.parse').quote(redir, safe='')}"
            f"&response_type=code&scope={scope}&state={state}#wechat_redirect"
        )
        return json_ok({"configured": True, "authorize_url": url}, source="wechat")

    @r.get("/wechat/callback")
    def wechat_callback(code: str = "", state: str = "") -> Any:
        """OAuth 回调占位：生产环境应换取 openid 并写库后签发 JWT。"""
        if not code:
            return json_fail("missing code", status_code=400)
        return json_ok(
            {"code_received": True, "state": state, "note": "请接微信开放平台换取 openid 后绑定用户"},
            source="wechat",
        )

    @r.post("/wechat/miniprogram")
    def wechat_miniprogram_login(payload: MiniProgramBody) -> Any:
        """
        小程序 wx.login 的 code 换 session；成功则按 openid 查找或创建用户并返回 JWT。
        """
        appid = os.environ.get("WECHAT_MINIPROGRAM_APPID", "").strip()
        secret = os.environ.get("WECHAT_MINIPROGRAM_SECRET", "").strip()
        if not appid or not secret:
            return json_fail(
                "未配置 WECHAT_MINIPROGRAM_APPID / WECHAT_MINIPROGRAM_SECRET",
                status_code=501,
                source="wechat",
            )
        try:
            import urllib.parse
            import urllib.request

            q = (
                "https://api.weixin.qq.com/sns/jscode2session"
                f"?appid={urllib.parse.quote(appid)}"
                f"&secret={urllib.parse.quote(secret)}"
                f"&js_code={urllib.parse.quote(payload.code)}"
                "&grant_type=authorization_code"
            )
            with urllib.request.urlopen(q, timeout=10) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            import json as _json

            data = _json.loads(raw)
        except Exception as e:
            _log.warning("wechat code2session failed: %s", e)
            return json_fail(f"微信接口失败: {e!s}"[:200], status_code=502, source="wechat")

        if data.get("errcode"):
            return json_fail(
                str(data.get("errmsg") or data.get("errcode")),
                status_code=400,
                source="wechat",
            )
        openid = str(data.get("openid") or "").strip()
        if not openid:
            return json_fail("未返回 openid", status_code=502, source="wechat")

        conn = _open_writable()
        if not conn:
            return json_fail("数据库不可用", status_code=503, source="wechat")
        try:
            row = conn.execute(
                """
                SELECT user_id, username, role, COALESCE(user_level, 'trial')
                FROM hongshan_users WHERE wechat_openid = ? LIMIT 1
                """,
                [openid],
            ).fetchone()
            if row:
                uid, uname, urole = str(row[0]), str(row[1]), str(row[2] or "viewer")
                ulvl = str(row[3] or "trial").strip() if len(row) > 3 else "trial"
            else:
                uid = str(uuid.uuid4())
                uname = f"wx_{openid[:8]}_{uid[:6]}"
                urole = "viewer"
                ulvl = "trial"
                now = datetime.now(timezone.utc)
                conn.execute(
                    """
                    INSERT INTO hongshan_users
                    (user_id, username, email, phone, password_hash, status, role, wechat_openid, user_level, created_at)
                    VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)
                    """,
                    [
                        uid,
                        uname,
                        f"{uid[:8]}@wechat.local",
                        None,
                        hash_password(uuid.uuid4().hex),
                        urole,
                        openid,
                        ulvl,
                        now,
                    ],
                )
                try:
                    conn.execute(
                        """
                        INSERT INTO hongshan_accounts (user_id, available_cash, frozen_cash, total_assets, updated_at)
                        VALUES (?, 500000, 0, 500000, ?)
                        """,
                        [uid, now],
                    )
                except Exception:
                    _log.error("Database write operation failed", exc_info=True)
            token = create_access_token(
                subject=uid, extra_claims={"role": urole, "user_level": ulvl}
            )
            return json_ok(
                {
                    "token": token,
                    "access_token": token,
                    "token_type": "bearer",
                    "user_id": uid,
                    "username": uname,
                    "openid": openid,
                    "user_level": ulvl,
                },
                source="wechat",
            )
        except Exception as e:
            _log.exception("miniprogram login persist failed")
            return json_fail(str(e)[:200], status_code=500, source="wechat")
        finally:
            try:
                conn.close()
            except Exception:
                _log.error("Database write operation failed", exc_info=True)

    return r
