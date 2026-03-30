"""
认证中间件：对 /api/* 除白名单路径外校验 Authorization: Bearer <token>。
白名单含 /api/auth/login、/api/health、/health、/docs、/openapi、/redoc，
及行情页只读 /api/market/sentiment-7d、/api/market/klines、/api/market/ashare/stocks、/api/market/emotion，
控制台只读 /api/dashboard、/api/system/data-overview、/api/system/status；
OPTIONS 预检直接放行。
通过 JWT_AUTH_REQUIRED=1 启用；未启用时所有请求放行。
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
    "/api/auth/login",
    "/api/auth/register",
    "/api/health",
    "/api/market/sentiment-7d",
    "/api/market/klines",
    "/api/market/ashare/stocks",
    # 新闻 / 数据状态：首页与 /news 页公网可读（JWT_AUTH_REQUIRED=1 时仍需白名单）
    "/api/news",
    "/api/news/coverage",
    "/api/news/hot-ticker",
    "/api/news/collector",
    "/api/data/status",
    # 控制台首页 / 系统卡片只读（生产 JWT 开启时避免整页 401；敏感写操作仍在保护内）
    "/api/dashboard",
    "/api/system/data-overview",
    "/api/system/status",
    "/api/market/emotion",
}


def _should_skip(path: str) -> bool:
    if path in _SKIP_PATHS:
        return True
    if path.startswith(_SKIP_PREFIXES):
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
    if _should_skip(path):
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
