#!/usr/bin/env python3
"""
政策新闻：读写 quant_system.duckdb 的 ``news_items``（symbol=__POLICY__）
- init：确保主库表存在
- 插入 / 列表 / 统计 / 清理：均走 DuckDB
- 可选 FastAPI（默认端口 8001），供旧版独立前端或调试

不再使用 SQLite；与 Gateway、RSS、东财快讯共用 ``QUANT_SYSTEM_DUCKDB_PATH``。
"""

from __future__ import annotations

import json
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_POLICY_DIR = Path(__file__).resolve().parent
_NEWHIGH_ROOT = _POLICY_DIR.parent.parent.parent
sys.path.insert(0, str(_NEWHIGH_ROOT / "data-pipeline" / "src"))

from data_pipeline.collectors.policy_news_duckdb import POLICY_SYMBOL, sync_policy_news_to_duckdb  # noqa: E402
from data_pipeline.storage.duckdb_manager import ensure_tables, get_conn  # noqa: E402


def _domains_list(keyword: Optional[str]) -> List[str]:
    if not keyword or not str(keyword).strip():
        return ["综合"]
    parts = [p.strip() for p in str(keyword).split(",") if p.strip()]
    return parts or ["综合"]


@contextmanager
def get_db_connection():
    """与历史 API 兼容的上下文管理器；实际为 DuckDB 连接。"""
    conn = get_conn(read_only=False)
    ensure_tables(conn)
    try:
        yield conn
    finally:
        conn.close()


def init_database() -> None:
    """确保主库表存在（政策数据写入 news_items）。"""
    with get_db_connection():
        pass
    print("✓ DuckDB 已就绪（表 news_items，政策行 symbol=%s）" % POLICY_SYMBOL)


def insert_news(items: List[Dict]) -> int:
    """写入政策新闻（去重逻辑见 policy_news_duckdb.sync_policy_news_to_duckdb）。"""
    return sync_policy_news_to_duckdb(items)


def get_news_list(
    category: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict]:
    """政策新闻列表（API 字段与旧版 SQLite 对齐）。"""
    conn = get_conn(read_only=False)
    ensure_tables(conn)
    q = (
        "SELECT rowid, title, source, tag, content, url, publish_time, sentiment_score, keyword, ts "
        "FROM news_items WHERE symbol = ?"
    )
    params: List[Any] = [POLICY_SYMBOL]
    if category:
        q += " AND tag = ?"
        params.append(category)
    if source:
        q += " AND source = ?"
        params.append(source)
    q += " ORDER BY COALESCE(publish_time, '') DESC, ts DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    cur = conn.execute(q, params)
    out: List[Dict] = []
    for row in cur.fetchall():
        rid, title, src, tag, content, url, pub, sent, keyword, ts = row
        domains = _domains_list(keyword)
        out.append(
            {
                "id": int(rid),
                "title": title or "",
                "source": src or "",
                "category": tag or "",
                "content": content or "",
                "url": url or "",
                "publish_date": pub or "",
                "sentiment": float(sent) if sent is not None else 0.0,
                "domains": json.dumps(domains, ensure_ascii=False),
                "created_at": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
            }
        )
    return out


def get_news_by_id(news_id: int) -> Optional[Dict]:
    conn = get_conn(read_only=False)
    ensure_tables(conn)
    row = conn.execute(
        "SELECT rowid, title, source, tag, content, url, publish_time, sentiment_score, keyword, ts "
        "FROM news_items WHERE symbol = ? AND rowid = ?",
        [POLICY_SYMBOL, news_id],
    ).fetchone()
    if not row:
        return None
    rid, title, src, tag, content, url, pub, sent, keyword, ts = row
    domains = _domains_list(keyword)
    return {
        "id": int(rid),
        "title": title or "",
        "source": src or "",
        "category": tag or "",
        "content": content or "",
        "url": url or "",
        "publish_date": pub or "",
        "sentiment": float(sent) if sent is not None else 0.0,
        "domains": json.dumps(domains, ensure_ascii=False),
        "created_at": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
    }


def get_categories() -> List[str]:
    conn = get_conn(read_only=False)
    ensure_tables(conn)
    cur = conn.execute(
        "SELECT DISTINCT tag FROM news_items WHERE symbol = ? AND tag IS NOT NULL AND TRIM(tag) <> '' ORDER BY tag",
        [POLICY_SYMBOL],
    )
    return [str(r[0]) for r in cur.fetchall()]


def get_sources() -> List[str]:
    conn = get_conn(read_only=False)
    ensure_tables(conn)
    cur = conn.execute(
        "SELECT DISTINCT source FROM news_items WHERE symbol = ? AND source IS NOT NULL AND TRIM(source) <> '' ORDER BY source",
        [POLICY_SYMBOL],
    )
    return [str(r[0]) for r in cur.fetchall()]


def get_stats() -> Dict:
    conn = get_conn(read_only=False)
    ensure_tables(conn)
    total = conn.execute(
        "SELECT COUNT(*) FROM news_items WHERE symbol = ?", [POLICY_SYMBOL]
    ).fetchone()[0]
    by_category: Dict[str, int] = {}
    for r in conn.execute(
        "SELECT tag, COUNT(*) AS c FROM news_items WHERE symbol = ? GROUP BY tag ORDER BY c DESC",
        [POLICY_SYMBOL],
    ).fetchall():
        k = r[0] or "(未分类)"
        by_category[str(k)] = int(r[1])
    by_source: Dict[str, int] = {}
    for r in conn.execute(
        "SELECT source, COUNT(*) AS c FROM news_items WHERE symbol = ? GROUP BY source ORDER BY c DESC",
        [POLICY_SYMBOL],
    ).fetchall():
        k = r[0] or "(未知来源)"
        by_source[str(k)] = int(r[1])
    today = datetime.now(timezone.utc).date().isoformat()
    today_count = conn.execute(
        "SELECT COUNT(*) FROM news_items WHERE symbol = ? AND CAST(ts AS DATE) = CAST(? AS DATE)",
        [POLICY_SYMBOL, today],
    ).fetchone()[0]
    return {
        "total": int(total),
        "by_category": by_category,
        "by_source": by_source,
        "today_count": int(today_count),
    }


def clear_old_news(days: int = 90) -> int:
    """删除 policy 行中 ts 早于 cutoff 的记录。"""
    conn = get_conn(read_only=False)
    ensure_tables(conn)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    n = conn.execute(
        "SELECT COUNT(*) FROM news_items WHERE symbol = ? AND ts < ?",
        [POLICY_SYMBOL, cutoff],
    ).fetchone()[0]
    if n:
        conn.execute(
            "DELETE FROM news_items WHERE symbol = ? AND ts < ?",
            [POLICY_SYMBOL, cutoff],
        )
    return int(n)


def create_api_app():
    try:
        from fastapi import Body, FastAPI, HTTPException, Query
        from fastapi.middleware.cors import CORSMiddleware
    except ImportError:
        print("错误：需要安装 fastapi 和 uvicorn")
        print("安装：pip install fastapi uvicorn --break-system-packages")
        return None

    app = FastAPI(title="红山量化 - 政策新闻 API（DuckDB）", version="2.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    def root():
        return {"message": "红山量化政策新闻 API（news_items / DuckDB）", "version": "2.0.0"}

    @app.get("/news/stats")
    def get_statistics():
        return {"data": get_stats()}

    @app.get("/news/categories")
    def list_categories():
        return {"data": get_categories()}

    @app.get("/news/sources")
    def list_sources():
        return {"data": get_sources()}

    @app.get("/news")
    def list_news(
        category: Optional[str] = Query(None, description="分类"),
        source: Optional[str] = Query(None, description="来源"),
        limit: int = Query(50, ge=1, le=200, description="每页数量"),
        offset: int = Query(0, ge=0, description="偏移量"),
    ):
        news_list = get_news_list(category, source, limit, offset)
        return {"data": news_list, "total": len(news_list)}

    @app.get("/news/{news_id}")
    def get_news(news_id: int):
        news = get_news_by_id(news_id)
        if not news:
            raise HTTPException(status_code=404, detail="新闻不存在")
        return {"data": news}

    @app.post("/news/ingest")
    def ingest_news(items: List[Dict[str, Any]] = Body(...)):
        count = insert_news(items)
        return {"message": f"成功导入 {count} 条新闻"}

    return app


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "init":
            init_database()
        elif command == "stats":
            print(json.dumps(get_stats(), indent=2, ensure_ascii=False))
        elif command == "api":
            app = create_api_app()
            if app:
                import uvicorn

                uvicorn.run(app, host="0.0.0.0", port=8001)
        else:
            print(f"未知命令：{command}")
            print("可用命令：init, stats, api")
    else:
        init_database()
        print(json.dumps(get_stats(), indent=2, ensure_ascii=False))
