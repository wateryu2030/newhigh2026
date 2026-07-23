"""
飞书（Lark）OAuth：网页授权 code 换用户并签发 JWT，与桌面端 / 小程序统一用户表 hongshan_users。

需配置：
  FEISHU_APP_ID          应用 App ID（cli_ 开头）
  FEISHU_APP_SECRET      应用 Secret
  FEISHU_OAUTH_REDIRECT_URI  与飞书开放平台「重定向 URL」完全一致（HTTPS）
可选：
  OAUTH_LOGIN_REDIRECT_BASE  登录成功后浏览器跳转的前端基址，如 https://htma.newhigh.com.cn
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from .auth.jwt_auth import create_access_token
from .response_utils import json_fail, json_ok
from .unified_password import hash_password

_log = logging.getLogger(__name__)


def _open_writable():
    import os as _os

    from data_pipeline.storage.duckdb_manager import ensure_tables, get_conn, get_db_path

    path = get_db_path()
    if not path or not _os.path.isfile(path):
        return None
    conn = get_conn(read_only=False)
    ensure_tables(conn)
    return conn


def _feishu_exchange_code(code: str) -> tuple[Optional[dict], Optional[str]]:
    """code → user_access_token JSON；失败返回 (None, err_msg)。"""
    app_id = os.environ.get("FEISHU_APP_ID", "").strip()
    app_secret = os.environ.get("FEISHU_APP_SECRET", "").strip()
    redirect_uri = os.environ.get("FEISHU_OAUTH_REDIRECT_URI", "").strip()
    if not app_id or not app_secret:
        return None, "未配置 FEISHU_APP_ID / FEISHU_APP_SECRET"
    body = {
        "grant_type": "authorization_code",
        "code": code,
        "app_id": app_id,
        "app_secret": app_secret,
    }
    if redirect_uri:
        body["redirect_uri"] = redirect_uri
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/authen/v1/access_token",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        try:
            raw = e.read().decode("utf-8", errors="replace")
        except Exception:
            raw = str(e)
        return None, f"飞书 token HTTP {e.code}: {raw[:300]}"
    except Exception as e:
        return None, str(e)[:200]
    try:
        j = json.loads(raw)
    except Exception:
        return None, "飞书返回非 JSON"
    if j.get("code") != 0:
        return None, str(j.get("msg") or j.get("error") or j)[:300]
    d = j.get("data") or {}
    return d, None


def _feishu_user_info(user_access_token: str) -> tuple[Optional[dict], Optional[str]]:
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/authen/v1/user_info",
        headers={"Authorization": f"Bearer {user_access_token}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return None, str(e)[:200]
    try:
        j = json.loads(raw)
    except Exception:
        return None, "user_info 非 JSON"
    if j.get("code") != 0:
        return None, str(j.get("msg") or j)[:200]
    return j.get("data") or {}, None


def build_feishu_auth_router() -> APIRouter:
    r = APIRouter(prefix="/auth", tags=["feishu"])

    @r.get("/feishu/url")
    def feishu_oauth_url() -> dict[str, Any]:
        client_id = os.environ.get("FEISHU_APP_ID", "").strip()
        redirect_uri = os.environ.get("FEISHU_OAUTH_REDIRECT_URI", "").strip()
        if not client_id or not redirect_uri:
            return json_ok(
                {
                    "configured": False,
                    "authorize_url": None,
                    "mock_available": True,
                    "hint": "未配置 FEISHU_APP_ID，可使用模拟扫码登录",
                },
                source="feishu",
            )
        state = uuid.uuid4().hex[:16]
        q = urllib.parse.urlencode(
            {
                "client_id": client_id,
                "response_type": "code",
                "redirect_uri": redirect_uri,
                "state": state,
            }
        )
        url = f"https://passport.feishu.cn/suite/passport/oauth/authorize?{q}"
        return json_ok({"configured": True, "authorize_url": url, "state": state}, source="feishu")

    @r.get("/feishu/callback")
    def feishu_callback(code: str = "", state: str = "", error: str = "") -> Any:
        base = (os.environ.get("OAUTH_LOGIN_REDIRECT_BASE") or "").strip().rstrip("/")
        login_path = "/login"
        if error:
            if base:
                return RedirectResponse(url=f"{base}{login_path}?oauth_error={urllib.parse.quote(error[:200])}")
            return json_fail(f"飞书授权失败: {error}", status_code=400, source="feishu")
        if not code:
            if base:
                return RedirectResponse(url=f"{base}{login_path}?oauth_error=nocode")
            return json_fail("missing code", status_code=400, source="feishu")

        token_data, err = _feishu_exchange_code(code)
        if err or not token_data:
            msg = err or "token 失败"
            if base:
                return RedirectResponse(url=f"{base}{login_path}?oauth_error={urllib.parse.quote(msg)}")
            return json_fail(msg, status_code=502, source="feishu")

        user_access_token = str(token_data.get("access_token") or "").strip()
        if not user_access_token:
            if base:
                return RedirectResponse(url=f"{base}{login_path}?oauth_error=no_access_token")
            return json_fail("未返回 access_token", status_code=502, source="feishu")

        ui, uerr = _feishu_user_info(user_access_token)
        if uerr or not ui:
            msg = uerr or "user_info 失败"
            if base:
                return RedirectResponse(url=f"{base}{login_path}?oauth_error={urllib.parse.quote(msg)}")
            return json_fail(msg, status_code=502, source="feishu")

        open_id = str(ui.get("open_id") or "").strip()
        if not open_id:
            open_id = str(ui.get("user_id") or "").strip()
        if not open_id:
            if base:
                return RedirectResponse(url=f"{base}{login_path}?oauth_error=no_open_id")
            return json_fail("飞书未返回 open_id", status_code=502, source="feishu")

        name = str(ui.get("name") or ui.get("en_name") or "").strip() or None
        avatar = str(ui.get("avatar_url") or ui.get("avatar_big") or "").strip() or None
        email_feishu = str(ui.get("email") or "").strip() or None

        conn = _open_writable()
        if not conn:
            if base:
                return RedirectResponse(url=f"{base}{login_path}?oauth_error=db")
            return json_fail("数据库不可用", status_code=503, source="feishu")

        try:
            row = conn.execute(
                """
                SELECT user_id, username, role, COALESCE(user_level, 'trial')
                FROM hongshan_users WHERE feishu_open_id = ? LIMIT 1
                """,
                [open_id],
            ).fetchone()
            now = datetime.now(timezone.utc)
            if row:
                uid, uname, urole = str(row[0]), str(row[1]), str(row[2] or "viewer")
                ulvl = str(row[3] or "trial").strip() if len(row) > 3 else "trial"
                conn.execute(
                    """
                    UPDATE hongshan_users
                    SET display_name = COALESCE(?, display_name),
                        avatar_url = COALESCE(?, avatar_url),
                        updated_at = ?
                    WHERE user_id = ?
                    """,
                    [name, avatar, now, uid],
                )
            else:
                uid = str(uuid.uuid4())
                uname = f"fs_{open_id[:10]}_{uid[:6]}"
                urole = "viewer"
                ulvl = "trial"
                email = email_feishu or f"{uid[:8]}@feishu.local"
                if conn.execute(
                    "SELECT 1 FROM hongshan_users WHERE email = ? LIMIT 1",
                    [email],
                ).fetchone():
                    email = f"{uid}@feishu.local"
                conn.execute(
                    """
                    INSERT INTO hongshan_users
                    (user_id, username, email, phone, password_hash, status, role, user_level,
                     feishu_open_id, display_name, avatar_url, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        uid,
                        uname,
                        email,
                        None,
                        hash_password(uuid.uuid4().hex),
                        urole,
                        ulvl,
                        open_id,
                        name,
                        avatar,
                        now,
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
        except Exception as e:
            _log.exception("feishu callback persist")
            if base:
                return RedirectResponse(
                    url=f"{base}{login_path}?oauth_error={urllib.parse.quote(str(e)[:120])}"
                )
            return json_fail(str(e)[:200], status_code=500, source="feishu")
        finally:
            try:
                conn.close()
            except Exception:
                _log.error("Database write operation failed", exc_info=True)

        if base:
            return RedirectResponse(
                url=f"{base}{login_path}?oauth=feishu&token={urllib.parse.quote(token)}"
            )
        return json_ok(
            {"token": token, "user_id": uid, "username": uname, "openid_feishu": open_id},
            source="feishu",
        )

    # -- 飞书模拟扫码登录 ----------------------------------------------------
    _FEISHU_MOCK_TICKETS: dict[str, dict] = {}

    @r.get("/feishu/mock-begin")
    def feishu_mock_begin(redirect: str = "/") -> dict[str, Any]:
        tid = uuid.uuid4().hex[:24]
        _FEISHU_MOCK_TICKETS[tid] = {"next": redirect, "created_at": __import__("time").time(), "used": False}
        return json_ok(
            {"ticket": tid, "mock_pick_url": f"/login/feishu-mock?t={tid}", "configured": False},
            source="feishu",
        )

    @r.post("/feishu/mock-complete")
    def feishu_mock_complete(payload: dict) -> Any:
        ticket = (payload.get("ticket") or "").strip()
        role = (payload.get("role") or "").strip().lower()
        if role not in ("viewer", "operator", "admin"):
            role = "viewer"
        entry = _FEISHU_MOCK_TICKETS.get(ticket)
        if not entry:
            return json_fail("ticket 无效或已过期", status_code=400, source="feishu")
        _FEISHU_MOCK_TICKETS.pop(ticket, None)
        conn = _open_writable()
        if not conn:
            return json_fail("数据库不可用", status_code=503, source="feishu")
        try:
            openid = f"fs-mock:{role}:{uuid.uuid4().hex[:12]}"
            display_name = {"admin": "管理员", "operator": "运营", "viewer": "用户"}.get(role, "用户")
            row = conn.execute(
                "SELECT user_id, username, role, COALESCE(user_level, 'trial') FROM hongshan_users WHERE feishu_open_id = ? LIMIT 1",
                [openid],
            ).fetchone()
            if row:
                uid, uname, urole = str(row[0]), str(row[1]), str(row[2] or role)
                ulvl = str(row[3] or "trial").strip() if len(row) > 3 else "trial"
            else:
                uid = str(uuid.uuid4())
                uname = f"fs-mock_{role}_{uuid.uuid4().hex[:6]}"
                urole = role
                ulvl = role
                now = datetime.now(timezone.utc)
                conn.execute(
                    """INSERT INTO hongshan_users
                       (user_id, username, email, phone, password_hash, status, role, feishu_open_id, user_level, created_at)
                       VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)""",
                    [uid, uname, f"{uid[:8]}@fs-mock.local", None,
                     hash_password(uuid.uuid4().hex), role, openid, ulvl, now],
                )
                try:
                    conn.execute(
                        "INSERT INTO hongshan_accounts (user_id, available_cash, frozen_cash, total_assets, updated_at) VALUES (?, 500000, 0, 500000, ?)",
                        [uid, now],
                    )
                except Exception:
                    pass
            token = create_access_token(subject=uid, extra_claims={"role": urole, "user_level": ulvl, "name": display_name})
            return json_ok(
                {"token": token, "access_token": token, "token_type": "bearer",
                 "user_id": uid, "username": display_name, "user": display_name, "role": urole, "user_level": ulvl},
                source="feishu",
            )
        except Exception as e:
            return json_fail(str(e)[:200], status_code=500, source="feishu")
        finally:
            try:
                conn.close()
            except Exception:
                pass

    return r
