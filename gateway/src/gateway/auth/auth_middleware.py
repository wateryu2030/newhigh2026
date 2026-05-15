"""
认证中间件：对 /api/* 除白名单路径外校验 Authorization: Bearer <token>。

JWT_AUTH_REQUIRED=1 时：未登录允许健康检查、认证、新闻类只读、以及部分 **GET** 公开行情/总览（见 ``_SKIP_PATHS``、``_PUBLIC_GET_*``）；
其余 ``/api/*`` 需有效 JWT。
未设置该变量时全部放行（本地开发）。
OPTIONS 预检不校验。/docs、/openapi、/redoc 前缀跳过。
"""

from __future__ import annotations

import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

_SKIP_PREFIXES = ("/docs", "/openapi", "/redoc")
# 行情页公开读数（与 Next 同源 /api 反代）；若需全部强制登录可删下列路径
_SKIP_PATHS = {
    "/health",
    "/api/health",
    "/api/health/detailed",
    "/api/auth/login",
    "/api/auth/register",
    # 微信 / 飞书 OAuth 与小程序 code 换票（未登录必须可访问）
    "/api/auth/wechat/url",
    "/api/auth/wechat/callback",
    "/api/auth/wechat/miniprogram",
    "/api/auth/feishu/url",
    "/api/auth/feishu/callback",
    # 未登录仅开放：新闻类只读 GET（POST manual-refresh / web-insight 等不在此列，需登录）
    "/api/news",
    "/api/news/coverage",
    "/api/news/hot-ticker",
    "/api/news/collector",
}

# JWT_AUTH_REQUIRED=1 时：下列 GET 仍匿名可访问（小程序「开放浏览」与 Web 公开行情同源）
_PUBLIC_GET_EXACT = frozenset(
    {
        "/api/dashboard",
        "/api/market/emotion",
        "/api/strategy/signals",
    }
)
_PUBLIC_GET_PREFIXES = (
    "/api/stocks/",  # 统一行情 GET：search / quotes / quote/{sym} / …
    "/api/market/",  # 行情只读：klines、sentiment-7d、hotmoney 等（当前均为 GET）
    "/api/screen/",  # 截面筛选只读 GET：大宗 × 区间震荡等
)


def _should_skip(request: Request) -> bool:
    path = request.url.path or ""
    if path in _SKIP_PATHS:
        return True
    if path.startswith(_SKIP_PREFIXES):
        return True
    method = (request.method or "").upper()
    if method != "GET":
        return False
    if path in _PUBLIC_GET_EXACT:
        return True
    for prefix in _PUBLIC_GET_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


async def auth_middleware_dispatch(request: Request, call_next):
    """若启用 JWT 校验且路径需校验，则检查 Authorization。"""
    if os.environ.get("JWT_AUTH_REQUIRED", "").strip().lower() not in ("1", "true", "yes"):
        return await call_next(request)
    # 预检请求不校验 JWT，避免浏览器跨域 OPTIONS 被拦
    if (request.method or "").upper() == "OPTIONS":
        return await call_next(request)
    path = request.url.path or ""
    if _should_skip(request):
        return await call_next(request)
    if not path.startswith("/api"):
        return await call_next(request)
    auth = request.headers.get("Authorization") or ""
    if not auth.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"detail": "Missing or invalid Authorization"})
    token = auth[7:].strip()
    from .jwt_auth import verify_token

    if verify_token(token) is None:
        return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})
    return await call_next(request)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        return await auth_middleware_dispatch(request, call_next)
