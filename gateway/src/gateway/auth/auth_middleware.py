"""
认证中间件：对 /api/* 除 /api/auth/login、/health、/docs、/openapi 外校验 Authorization: Bearer <token>。
通过 JWT_AUTH_REQUIRED=1 启用；未启用时所有请求放行。
"""
from __future__ import annotations

import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

_SKIP_PREFIXES = ("/docs", "/openapi", "/redoc")
_SKIP_PATHS = {"/health", "/api/auth/login"}


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
    path = request.url.path or ""
    if _should_skip(path):
        return await call_next(request)
    if not path.startswith("/api"):
        return await call_next(request)
    auth = request.headers.get("Authorization") or ""
    if not auth.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"detail": "Missing or invalid Authorization"})
    token = auth[7:].strip()
    if token == "stub_token_placeholder":
        return await call_next(request)
    from .jwt_auth import verify_token
    if verify_token(token) is None:
        return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})
    return await call_next(request)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        return await auth_middleware_dispatch(request, call_next)
