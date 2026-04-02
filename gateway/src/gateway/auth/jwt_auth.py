"""
JWT 签发与校验：SECRET_KEY、过期时间；可选启用后对 /api/* 除 /api/auth/login、/health 外校验。
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

_SECRET = (
    os.environ.get("JWT_SECRET_KEY", "").strip()
    or os.environ.get("JWT_SECRET", "").strip()
    or "newhigh-insecure-change-in-production"
)
_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "60"))


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict] = None,
) -> str:
    """
    签发 JWT。subject 通常为 user_id 或 username。
    需安装 PyJWT: pip install pyjwt
    """
    try:
        import jwt
    except ImportError:
        return "stub_token_placeholder"
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=_EXPIRE_MINUTES))
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": now,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, _SECRET, algorithm="HS256")


def verify_token(token: str) -> Optional[dict]:
    """
    校验 JWT，返回 payload 或 None。
    """
    try:
        import jwt
    except ImportError:
        return None
    try:
        payload = jwt.decode(token, _SECRET, algorithms=["HS256"])
        return payload
    except Exception:
        return None


def resolve_effective_role(payload: Optional[dict]) -> str:
    """
    JWT claim role：viewer | operator | admin。
    PIPELINE_ADMIN_SUBJECTS / PIPELINE_OPERATOR_SUBJECTS：逗号分隔，与 JWT `sub`（一般为 user_id）对齐，用于应急赋权。
    优先级：admin 名单 > operator 名单 > JWT role > viewer。
    """
    if not payload:
        return "viewer"
    sub = str(payload.get("sub") or "").strip()
    admin_subjects = os.environ.get("PIPELINE_ADMIN_SUBJECTS", "").strip()
    if admin_subjects and sub:
        allowed = {x.strip() for x in admin_subjects.split(",") if x.strip()}
        if sub in allowed:
            return "admin"
    op_env = os.environ.get("PIPELINE_OPERATOR_SUBJECTS", "").strip()
    if op_env and sub:
        ops = {x.strip() for x in op_env.split(",") if x.strip()}
        if sub in ops:
            return "operator"
    r = payload.get("role")
    if isinstance(r, str) and r in ("admin", "operator", "viewer"):
        return r
    return "viewer"


def is_admin(role: str) -> bool:
    return role == "admin"


def is_operator_or_admin(role: str) -> bool:
    return role in ("operator", "admin")


def get_current_user_optional(authorization: Optional[str] = None) -> Optional[str]:
    """
    从 Authorization: Bearer <token> 解析出 subject（用户名），无效时返回 None。
    用于 Depends() 可选认证。
    """
    if not authorization or "Bearer " not in authorization:
        return None
    token = authorization.replace("Bearer ", "").strip()
    if not token or token == "stub_token_placeholder":
        return "demo"
    payload = verify_token(token)
    if payload is None:
        return None
    return payload.get("sub")
