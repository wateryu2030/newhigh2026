"""FastAPI gateway application."""

from __future__ import annotations

try:
    import sys
    import os

    _root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    if _root not in sys.path:
        sys.path.insert(0, _root)
    # 加载 .env（TUSHARE_TOKEN、JWT_SECRET 等）
    _env_file = os.path.join(_root, ".env")
    if os.path.isfile(_env_file):
        try:
            from dotenv import load_dotenv

            load_dotenv(_env_file)
        except ImportError:
            pass
    from config.config_loader import init_app_env

    init_app_env()
except Exception:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response

from .endpoints import router
from .ws import router as ws_router

app = FastAPI(
    title="newhigh Gateway",
    description="AI Hedge Fund API",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# JWT 认证中间件（JWT_AUTH_REQUIRED=1 时启用）
try:
    from .auth.auth_middleware import JWTAuthMiddleware

    app.add_middleware(JWTAuthMiddleware)
except Exception:
    pass

app.include_router(router, prefix="/api", tags=["api"])
app.include_router(ws_router, prefix="/ws", tags=["websocket"])


@app.middleware("http")
async def audit_log_middleware(request, call_next):
    """审计：记录请求 method、path、client_host 到 audit_log 表；记录耗时到 Prometheus。"""
    import time

    start = time.perf_counter()
    response = await call_next(request)
    try:
        from .metrics import record_request

        record_request(time.perf_counter() - start, request.url.path or "", request.method or "GET")
    except Exception:
        pass
    try:
        _ensure_repo_paths()
        from data_pipeline.storage.duckdb_manager import get_conn, ensure_tables, get_db_path
        import os

        if os.path.isfile(get_db_path()):
            conn = get_conn(read_only=False)
            ensure_tables(conn)
            r = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 AS n FROM audit_log").fetchone()
            nid = int(r[0]) if r else 1
            host = request.client.host if request.client else ""
            conn.execute(
                "INSERT INTO audit_log (id, method, path, client_host) VALUES (?, ?, ?, ?)",
                [nid, request.method, request.url.path or "", host],
            )
            conn.close()
    except Exception:
        pass
    return response


@app.get("/")
def root():
    """Redirect to API docs."""
    return RedirectResponse(url="/docs", status_code=302)


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Avoid 404 when browser requests favicon."""
    return Response(status_code=204)


def _ensure_repo_paths():
    """Ensure data-pipeline, core, execution-engine are on sys.path for imports."""
    import os
    import sys

    _root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    for _d in ["data-pipeline/src", "core/src", "execution-engine/src"]:
        _p = os.path.join(_root, _d)
        if os.path.isdir(_p) and _p not in sys.path:
            sys.path.insert(0, _p)


@app.get("/health")
def health():
    """健康检查：status=ok 表示可用，degraded 表示部分依赖不可用。"""
    checks = {}
    db_ok = False
    try:
        _ensure_repo_paths()
        import os
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path

        path = get_db_path()
        if path and os.path.isfile(path):
            conn = get_conn(read_only=True)
            if conn:
                try:
                    conn.execute("SELECT 1").fetchone()
                    db_ok = True
                except Exception:
                    pass
                try:
                    conn.close()
                except Exception:
                    pass
        checks["db"] = "available" if db_ok else "unavailable"
    except Exception as e:
        checks["db"] = "error"
        checks["db_error"] = str(e)[:200]
    status = "ok" if db_ok else "degraded"
    return {"status": status, "checks": checks}


@app.get("/metrics", include_in_schema=False)
def metrics():
    """Prometheus 指标端点（需安装 prometheus_client）。"""
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
    except ImportError:
        return Response(content="# prometheus_client not installed\n", media_type="text/plain")
