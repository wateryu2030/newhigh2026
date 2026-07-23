"""
微信网页授权 URL（占位）、小程序 code 换 JWT、模拟扫码登录。
需配置：WECHAT_MINIPROGRAM_APPID、WECHAT_MINIPROGRAM_SECRET；
公众号网页授权：WECHAT_MP_APPID、WECHAT_OAUTH_REDIRECT_URI（可选）。
"""

from __future__ import annotations

import logging
import os
import time
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


class MockCompleteBody(BaseModel):
    ticket: str = Field(..., min_length=1, max_length=128)
    role: str = Field(..., min_length=1, max_length=32)


# -- 内存 ticket 存储 -----------------------------------------------------
_MOCK_TICKETS: dict[str, dict] = {}
_MOCK_TICKET_TTL = 300  # 5 分钟


def _mock_new_ticket(next_path: str = "/") -> str:
    tid = uuid.uuid4().hex[:24]
    _MOCK_TICKETS[tid] = {
        "next": next_path,
        "created_at": time.time(),
        "used": False,
    }
    return tid


def _mock_consume_ticket(ticket: str) -> Optional[dict]:
    entry = _MOCK_TICKETS.get(ticket)
    if not entry:
        return None
    if time.time() - entry["created_at"] > _MOCK_TICKET_TTL:
        _MOCK_TICKETS.pop(ticket, None)
        return None
    return entry


def _open_writable():
    import os as _os

    from data_pipeline.storage.duckdb_manager import ensure_tables, get_conn, get_db_path

    path = get_db_path()
    if not path or not _os.path.isfile(path):
        return None
    conn = get_conn(read_only=False)
    ensure_tables(conn)
    return conn


def _find_or_create_mock_user(
    conn, openid: str, username: str, role: str
) -> tuple[str, str, str, str]:
    """按 openid 查找或创建 mock 用户，返回 (user_id, username, role, user_level)。"""
    row = conn.execute(
        "SELECT user_id, username, role, COALESCE(user_level, 'trial') FROM hongshan_users WHERE wechat_openid = ? LIMIT 1",
        [openid],
    ).fetchone()
    if row:
        uid, uname, urole = str(row[0]), str(row[1]), str(row[2] or role)
        ulvl = str(row[3] or "trial").strip() if len(row) > 3 else "trial"
        return uid, uname, urole, ulvl

    uid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    conn.execute(
        """INSERT INTO hongshan_users
           (user_id, username, email, phone, password_hash, status, role, wechat_openid, user_level, created_at)
           VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)""",
        [
            uid,
            username,
            f"{uid[:8]}@wechat-mock.local",
            None,
            hash_password(uuid.uuid4().hex),
            role,
            openid,
            role,
            now,
        ],
    )
    try:
        conn.execute(
            "INSERT INTO hongshan_accounts (user_id, available_cash, frozen_cash, total_assets, updated_at) VALUES (?, 500000, 0, 500000, ?)",
            [uid, now],
        )
    except Exception:
        _log.warning("mock user account insert skipped (table may not exist)")
    return uid, username, role, role


def build_wechat_auth_routes() -> APIRouter:
    r = APIRouter(prefix="/auth", tags=["wechat"])

    @r.get("/wechat/url")
    def wechat_oauth_url(redirect: str = "/") -> dict[str, Any]:
        """返回公众号网页授权 URL；未配置 appid 时返回 mock 模式指引。"""
        appid = os.environ.get("WECHAT_MP_APPID", "").strip()
        if not appid:
            return json_ok(
                {
                    "configured": False,
                    "authorize_url": None,
                    "mock_available": True,
                    "hint": "未配置 WECHAT_MP_APPID，可使用模拟扫码登录",
                },
                source="wechat",
            )
        redir = (
            os.environ.get("WECHAT_OAUTH_REDIRECT_URI", "").strip()
            or "https://example.com/api/auth/wechat/callback"
        )
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
            {
                "code_received": True,
                "state": state,
                "note": "请接微信开放平台换取 openid 后绑定用户",
            },
            source="wechat",
        )

    # -- 模拟扫码登录 -------------------------------------------------------
    @r.get("/wechat/mock-begin")
    def wechat_mock_begin(redirect: str = "/") -> dict[str, Any]:
        """生成模拟扫码 ticket，返回 ticket 和前端选角页面 URL。"""
        ticket = _mock_new_ticket(redirect)
        return json_ok(
            {
                "ticket": ticket,
                "mock_pick_url": f"/login/wechat-mock?t={ticket}",
                "configured": False,
                "hint": "模拟扫码模式：跳转到 mock_pick_url 选择角色登录",
            },
            source="wechat",
        )

    @r.post("/wechat/mock-complete")
    def wechat_mock_complete(payload: MockCompleteBody) -> Any:
        """模拟扫码完成：选择角色后创建/查找用户，签发 JWT 并返回。"""
        ticket = payload.ticket.strip()
        role = payload.role.strip().lower()
        if role not in ("viewer", "operator", "admin"):
            role = "viewer"

        _mock_consume_ticket(ticket)  # 校验 ticket 有效性（仅用于验证）

        conn = _open_writable()
        if not conn:
            return json_fail("数据库不可用", status_code=503, source="wechat")
        try:
            openid = f"mock:{role}:{uuid.uuid4().hex[:12]}"
            display_name = {"admin": "管理员", "operator": "运营", "viewer": "用户"}.get(
                role, "用户"
            )
            short_uid = uuid.uuid4().hex[:6]
            uid, uname, urole, ulvl = _find_or_create_mock_user(
                conn, openid, f"mock_{role}_{short_uid}", role
            )
            token = create_access_token(
                subject=uid,
                extra_claims={
                    "role": urole,
                    "user_level": ulvl,
                    "name": display_name,
                },
            )
            return json_ok(
                {
                    "token": token,
                    "access_token": token,
                    "token_type": "bearer",
                    "user_id": uid,
                    "username": display_name,
                    "user": display_name,
                    "role": urole,
                    "user_level": ulvl,
                },
                source="wechat",
            )
        except Exception as e:
            _log.exception("mock-complete failed")
            return json_fail(str(e)[:200], status_code=500, source="wechat")
        finally:
            try:
                conn.close()
            except Exception:
                pass

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
