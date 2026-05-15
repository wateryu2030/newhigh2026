"""API endpoints: market, strategy, backtest, portfolio, risk, trade, ai-lab."""

import asyncio
import json
import logging
import os
from typing import Any, List, Optional

from fastapi import APIRouter, Body, HTTPException, Query, Request
from pydantic import BaseModel, Field

from core.ashare_symbol import normalize_ashare_symbol

from .response_utils import json_fail, json_ok

router = APIRouter()
_log = logging.getLogger(__name__)

# 导入系统数据概览端点
try:
    from .endpoints_system_data import get_system_data_overview
    router.get("/system/data-overview")(get_system_data_overview)
except Exception:
    _log.warning("Import failed, using fallback", exc_info=True)

# 导入财报分析端点（endpoints_api 避免与 endpoints.py 命名冲突）
try:
    from .endpoints_api.financial import router as financial_router
    router.include_router(financial_router)
except Exception as e:
    print(f"警告：财报分析端点加载失败：{e}")

from .endpoints_helpers import (  # noqa: E402
    _fetch_news_for_research,
    _llm_news_summary,
    _pipeline_quant_data_status,
)


@router.get("/data/status")
def get_data_status() -> dict:
    """数据状态：合并 astock 表与 pipeline 表口径，供「数据」页与 Dashboard；主数字优先与概览一致。"""
    astock_st: Optional[dict] = None
    try:
        from data_engine import get_astock_duckdb_available, get_duckdb_data_status

        if get_astock_duckdb_available():
            astock_st = get_duckdb_data_status()
    except Exception:
        _log.error("Import failed", exc_info=True)

    pipeline_st = _pipeline_quant_data_status()

    def _has_data(d: Optional[dict]) -> bool:
        if not d:
            return False
        return (d.get("daily_bars") or 0) > 0 or (d.get("stocks") or 0) > 0

    primary: Optional[dict] = None
    source_label: Optional[str] = None
    # 主展示：pipeline 有日线则优先（与 system/data-overview 一致）；否则 astock；再否则谁有标的使用谁
    if _has_data(pipeline_st):
        primary = pipeline_st
        source_label = "duckdb_pipeline"
    elif _has_data(astock_st):
        primary = astock_st
        source_label = "duckdb_astock"
    elif pipeline_st:
        primary = pipeline_st
        source_label = "duckdb_pipeline"
    elif astock_st:
        primary = astock_st
        source_label = "duckdb_astock"

    if primary:
        return {
            "ok": True,
            "source": source_label,
            **primary,
            "breakdown": {
                "astock_schema": astock_st,
                "pipeline_schema": pipeline_st,
            },
        }

    return {
        "ok": False,
        "source": None,
        "stocks": 0,
        "daily_bars": 0,
        "date_min": None,
        "date_max": None,
        "breakdown": {"astock_schema": astock_st, "pipeline_schema": pipeline_st},
    }


@router.get("/data/daily-coverage")
def get_daily_coverage(limit_codes: int = 200) -> dict:
    """
    a_stock_daily 覆盖明细：总行数、有 K 线的标的数、每只有多少根 K 线 TopN。
    用于解释「股票池很大但日线总行数很少」——多为仅部分标的/短区间写入。
    """
    try:
        import os

        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path

        if not os.path.isfile(get_db_path()):
            return {"ok": False, "error": "database_not_found", "top_codes": []}
        conn = get_conn(read_only=True)
        try:
            lim = max(10, min(int(limit_codes or 200), 500))
            agg = conn.execute(
                """
                SELECT COUNT(*), COUNT(DISTINCT code), MIN(date), MAX(date)
                FROM a_stock_daily
                """
            ).fetchone()
            total_rows = int(agg[0] or 0) if agg else 0
            distinct_codes = int(agg[1] or 0) if agg else 0
            date_min = str(agg[2])[:10] if agg and agg[2] is not None else None
            date_max = str(agg[3])[:10] if agg and agg[3] is not None else None
            pool_row = conn.execute("SELECT COUNT(*) FROM a_stock_basic").fetchone()
            stock_pool = int(pool_row[0] or 0) if pool_row else 0
            top_rows = conn.execute(
                """
                SELECT code, COUNT(*) AS n, MIN(date), MAX(date)
                FROM a_stock_daily
                GROUP BY code
                ORDER BY n DESC
                LIMIT ?
                """,
                [lim],
            ).fetchall()
            top_codes = [
                {
                    "code": str(r[0]),
                    "bar_count": int(r[1] or 0),
                    "date_min": str(r[2])[:10] if r[2] is not None else None,
                    "date_max": str(r[3])[:10] if r[3] is not None else None,
                }
                for r in top_rows
            ]
        finally:
            try:
                conn.close()
            except Exception:
                _log.error("Failed to close database connection", exc_info=True)
        avg = (total_rows / distinct_codes) if distinct_codes else 0.0
        return {
            "ok": True,
            "total_rows": total_rows,
            "distinct_codes": distinct_codes,
            "stock_pool_codes": stock_pool,
            "avg_bars_per_code": round(avg, 4),
            "date_min": date_min,
            "date_max": date_max,
            "top_codes": top_codes,
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "top_codes": []}


@router.get("/market/ashare/stocks")
def get_ashare_stocks() -> dict:
    """A 股标的列表（来自 newhigh 本地 DuckDB），供前端 Market 页标的选择与 K 线请求。"""
    try:
        from data_engine import get_astock_duckdb_available, get_stocks_for_api

        if get_astock_duckdb_available():
            stocks = get_stocks_for_api()
            return {"stocks": stocks, "source": "duckdb"}
    except Exception:
        _log.error("Import failed", exc_info=True)
    return {"stocks": [], "source": None}


# --- Data Service 层：DuckDB → API 稳定通道（MVP Data Bridge）---


@router.get("/stocks")
def get_stocks(limit: int = 200) -> list:
    """A 股股票列表，供前端 Stocks 页表格。优先 stocks 表，空时回退 a_stock_basic。"""
    try:
        from core.data_service import get_stock_list

        out = get_stock_list(limit=limit)
        if out:
            return out
    except Exception:
        _log.error("Import failed", exc_info=True)
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if os.path.isfile(get_db_path()):
            conn = get_conn(read_only=False)
            try:
                df = conn.execute(
                    "SELECT code, name FROM a_stock_basic ORDER BY code LIMIT ?",
                    [limit],
                ).fetchdf()
                if df is not None and not df.empty:
                    return [
                        {
                            "ts_code": str(row.get("code", "")),
                            "name": str(row.get("name") or row.get("code") or ""),
                            "industry": "",
                        }
                        for _, row in df.iterrows()
                    ]
            finally:
                conn.close()
    except Exception:
        _log.error("Failed to close database connection", exc_info=True)
    return []


@router.get("/market/summary")
def get_market_summary() -> dict:
    """市场概览：标的数、日线条数、日期范围，供 Dashboard 与前端。"""
    try:
        from core.data_service import get_market_summary as svc_summary

        return svc_summary()
    except Exception:
        return {
            "total_stocks": 0,
            "market": "A-share",
            "daily_bars": 0,
            "date_min": None,
            "date_max": None,
        }


# --- 数据管道 Data Pipeline（quant_system.duckdb：实时/涨停/资金流）---


@router.get("/data/sources")
def get_data_sources() -> dict:
    """已注册数据源 id 列表（支持增量更新的数据源）。"""
    try:
        from data_pipeline import list_sources

        return {"sources": list_sources()}
    except Exception as e:
        return {"sources": [], "error": str(e)}


@router.post("/data/ensure-stocks")
def ensure_stocks() -> dict:
    """拉取 A 股股票池写入 a_stock_basic（akshare），数据不足时由前端或定时任务调用。"""
    try:
        from data_pipeline.collectors.stock_list import update_stock_list

        n = update_stock_list()
        return {"ok": True, "rows": n}
    except Exception as e:
        return {"ok": False, "rows": 0, "error": str(e)}


# ---------- OpenClaw A股 Skill（Tushare：行情、基本面、技术指标）----------
@router.post("/data/incremental")
def run_data_incremental(
    source_id: str = Query(
        "ashare_daily_kline",
        description="数据源 ID：ashare_daily_kline（东财/akshare）或 tushare_daily（需 TUSHARE_TOKEN）；见 GET /api/data/sources",
    ),
    force_full: bool = Query(False, description="为 True 时对 ashare_daily_kline 全员重拉约一年"),
    codes_limit: Optional[int] = Query(
        None,
        ge=1,
        le=8000,
        description="仅 ashare_daily_kline：最多处理 a_stock_basic 前 N 只，分批防超时；不传则最多 8000",
    ),
    verbose: bool = Query(
        False,
        description="为 True 时 ashare_daily_kline 将分批进度打到服务 stderr",
    ),
    no_proxy: bool = Query(
        False,
        description="为 True 时 ashare_daily_kline 临时清除环境变量中所有 *proxy* 项再请求（修坏代理）",
    ),
) -> dict:
    """执行指定数据源增量更新。ashare_daily_kline 已从 a_stock_basic 扩量，并区分「无 K 线」回填与增量。"""
    try:
        from data_pipeline import run_incremental, list_sources

        if source_id not in list_sources():
            raise HTTPException(status_code=400, detail=f"unknown source_id: {source_id}")
        kw = {}
        if codes_limit is not None:
            kw["codes_limit"] = codes_limit
        if verbose and source_id in ("ashare_daily_kline", "tushare_daily"):
            kw["verbose"] = True
        if no_proxy and source_id in ("ashare_daily_kline", "tushare_daily"):
            kw["strip_proxy_env"] = True
        n = run_incremental(source_id, force_full=force_full, **kw)
        return {"ok": True, "source_id": source_id, "rows_written": n, "codes_limit": codes_limit}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/health-detail")
def get_system_health_detail() -> dict:
    """健康检查扩展：Celery worker 探测、pipeline_meta 最近项、Prometheus 路径（供运维 / OpenClaw）。"""
    try:
        from .endpoints_health import build_health_detail_payload

        return json_ok(build_health_detail_payload(), source="gateway")
    except Exception as e:
        return json_fail(str(e)[:200], status_code=503)


@router.get("/health/detailed")
def get_health_detailed_alias() -> dict:
    """与 /system/health-detail 等价，便于监控与小程序统一路径。"""
    try:
        from .endpoints_health import build_health_detail_payload

        return json_ok(build_health_detail_payload(), source="health")
    except Exception as e:
        return json_fail(str(e)[:200], status_code=503)


@router.get("/system/backtest-errors")
def get_system_backtest_errors(limit: int = 20) -> dict:
    """Celery / 回测任务最近错误（backtest_task_errors），供排障。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, ensure_tables, get_db_path

        lim = max(1, min(limit, 200))
        if not os.path.isfile(get_db_path()):
            return json_ok({"items": []}, source="none")
        conn = get_conn(read_only=False)
        ensure_tables(conn)
        try:
            df = conn.execute(
                """
                SELECT id, task_name, strategy_id,
                       SUBSTRING(payload_json, 1, 400) AS payload_preview,
                       SUBSTRING(error_message, 1, 500) AS error_message,
                       created_at
                FROM backtest_task_errors
                ORDER BY id DESC LIMIT ?
                """,
                [lim],
            ).fetchdf()
        except Exception:
            df = None
        conn.close()
        if df is None or df.empty:
            return json_ok({"items": []}, source="duckdb")
        return json_ok({"items": df.to_dict(orient="records")}, source="duckdb")
    except Exception as e:
        return json_fail(str(e)[:200], status_code=503)


@router.post("/news/web-insight")
def post_news_web_insight(payload: dict = Body(default_factory=dict)) -> dict:
    """
    用现有 DOUBAO 或 DASHSCOPE Key 做「联网向」舆情问答（抖音/中文热点依赖方舟是否开启联网内容插件）。
    Body: { "query": "...", "provider": "doubao" | "dashscope" }
    """
    import os

    import requests

    query = (payload.get("query") or "").strip()
    if not query or len(query) > 2000:
        raise HTTPException(status_code=400, detail="query 必填，最长 2000 字")
    provider = (payload.get("provider") or "doubao").lower().strip()
    sys_msg = (
        "你是中文互联网舆情与热点分析助手。若具备联网检索能力，请结合最新公开信息回答；"
        "若无，须首句说明无法实时检索。涉及抖音/短视频/微博等仅基于你能访问的公开信息归纳。"
        "文末写：不构成投资建议。"
    )
    user_msg = f"用户问题：\n{query}"

    if provider == "doubao":
        key = os.environ.get("DOUBAO_API_KEY") or os.environ.get("VOLCANO_ENGINE_API_KEY")
        model = (os.environ.get("DOUBAO_MODEL") or "").strip()
        if not key or not model:
            return {
                "ok": False,
                "error": "missing_doubao_config",
                "hint": "配置 DOUBAO_API_KEY 与 DOUBAO_MODEL（推理接入点 ID）。抖音类时效需在火山方舟为该接入点开启联网内容插件，见 docs/NEWS_CHANNELS_WITH_EXISTING_KEYS.md",
            }
        base = os.environ.get("ARK_API_BASE", "https://ark.cn-beijing.volces.com/api/v3")
        try:
            r = requests.post(
                f"{base.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                timeout=120,
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": sys_msg},
                        {"role": "user", "content": user_msg},
                    ],
                    "max_tokens": 4096,
                },
            )
            data = r.json()
            if r.status_code != 200:
                return {
                    "ok": False,
                    "error": f"ark_http_{r.status_code}",
                    "detail": str(data)[:500],
                }
            text = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
            return {
                "ok": True,
                "provider": "doubao",
                "text": text.strip(),
                "note": "是否含实时检索取决于方舟接入点是否启用联网内容插件",
            }
        except Exception as e:
            return {"ok": False, "error": str(e)[:300]}

    if provider == "dashscope":
        key = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("BAILIAN_API_KEY")
        model = os.environ.get("NEWS_WEB_INSIGHT_MODEL", "qwen-turbo")
        if not key:
            return {"ok": False, "error": "missing_DASHSCOPE_API_KEY"}
        try:
            r = requests.post(
                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                timeout=120,
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": sys_msg},
                        {"role": "user", "content": user_msg},
                    ],
                    "max_tokens": 4096,
                },
            )
            data = r.json()
            if r.status_code != 200:
                return {
                    "ok": False,
                    "error": f"dashscope_{r.status_code}",
                    "detail": str(data)[:500],
                }
            text = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
            return {
                "ok": True,
                "provider": "dashscope",
                "model": model,
                "text": text.strip(),
                "note": "通义侧若应用开启联网/搜索能力则时效更强，见百炼控制台",
            }
        except Exception as e:
            return {"ok": False, "error": str(e)[:300]}

    raise HTTPException(status_code=400, detail='provider 仅支持 "doubao" 或 "dashscope"')


@router.post("/research/news-summary")
def post_research_news_summary(payload: dict = Body(default_factory=dict)) -> dict:
    """
    投研：拉取个股/市场新闻后由大模型生成摘要（需配置 DASHSCOPE 或 OPENAI）。
    Body: { "symbol": "000001" 可选, "limit": 25, "focus": "用户关注点" 可选 }
    """
    sym_raw = (payload.get("symbol") or "").strip()
    symbol = sym_raw.split(".", maxsplit=1)[0] if sym_raw else None
    if symbol and (len(symbol) < 5 or not symbol.isdigit()):
        symbol = None
    limit = int(payload.get("limit") or 25)
    limit = min(max(limit, 5), 40)
    focus = str(payload.get("focus") or "")[:500]

    items, source = _fetch_news_for_research(symbol, limit)
    if not items:
        return {
            "ok": False,
            "error": "no_news",
            "summary": "",
            "news_count": 0,
            "source": source,
        }

    label = symbol or "全市场（数据库/默认源）"
    lines = []
    for it in items[:limit]:
        t = str(it.get("title") or "")[:200]
        c = str(it.get("content") or "")[:180]
        pt = str(it.get("publish_time") or "")
        lines.append(f"- [{pt}] {t} | {c}")
    blob = "\n".join(lines)

    summary, model_used, err = _llm_news_summary(blob, label, focus)
    if err and not summary:
        return {
            "ok": False,
            "error": err,
            "summary": "",
            "news_count": len(items),
            "source": source,
        }

    return {
        "ok": True,
        "summary": summary or "",
        "model": model_used,
        "news_count": len(items),
        "source": source,
        "symbol": symbol,
    }


@router.get("/strategies")
def list_strategies() -> dict:
    """List strategy types (stub)."""
    return {
        "strategies": [
            {"id": "trend_following", "name": "Trend Following"},
            {"id": "mean_reversion", "name": "Mean Reversion"},
            {"id": "breakout", "name": "Breakout"},
        ]
    }


@router.get("/data/quality")
def get_data_quality() -> Any:
    """最近一条数据质量巡检报告（DuckDB data_quality_reports）。"""
    try:
        from .endpoints_health import _ensure_repo_paths_for_health

        _ensure_repo_paths_for_health()
        import os

        from data_pipeline.storage.duckdb_manager import ensure_tables, get_conn, get_db_path

        path = get_db_path()
        if not path or not os.path.isfile(path):
            return json_ok(None, source="none")
        # ensure_tables 含 DDL，需可写连接（仅服务端执行）
        conn = get_conn(read_only=False)
        try:
            ensure_tables(conn)
            row = conn.execute(
                """
                SELECT id, report_json, run_at
                FROM data_quality_reports
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
        finally:
            try:
                conn.close()
            except Exception:
                _log.error("Failed to close database connection", exc_info=True)
        if not row:
            return json_ok(None, source="duckdb")
        raw = row[1]
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            parsed = {"raw": raw}
        return json_ok(
            {"id": row[0], "run_at": str(row[2]) if row[2] is not None else None, "report": parsed},
            source="duckdb",
        )
    except Exception as e:
        # 返回 200 + data:null，避免浏览器控制台对「只读巡检」刷 503；运维仍可从日志看到异常
        _log.exception("get_data_quality failed")
        return json_ok(None, source="unavailable")


@router.get("/audit/logs")
def get_audit_logs(limit: int = 100) -> dict:
    """审计日志：最近请求记录。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return {"logs": []}
        conn = get_conn(read_only=False)
        df = conn.execute(
            "SELECT id, method, path, client_host, created_at FROM audit_log ORDER BY id DESC LIMIT ?",
            [limit],
        ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return {"logs": []}
        return {"logs": df.to_dict("records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 执行模式与统一经纪接口 (execution-engine brokers) ---


@router.get("/positions")
def get_positions() -> dict:
    """Current positions (stub)."""
    return {"positions": []}


@router.post("/ai/generate-strategies")
def generate_strategies(count: int = 5) -> dict:
    """Generate strategies via AI (stub)."""
    return {"generated": [], "count": count}


# --- Frontend API (Dashboard, Evolution, Trades) ---


@router.get("/trades")
def get_trades(limit: int = 50) -> dict:
    """Recent trades (stub)."""
    return {
        "trades": [
            {
                "time": "2025-03-07T10:00:00Z",
                "strategy": "STR_001",
                "symbol": "BTCUSDT",
                "side": "BUY",
                "qty": 0.1,
                "price": 95000,
            },
            {
                "time": "2025-03-07T09:30:00Z",
                "strategy": "STR_002",
                "symbol": "ETHUSDT",
                "side": "SELL",
                "qty": 1.0,
                "price": 3500,
            },
        ][:limit],
    }


# P1-2: 领域拆分子文件 — 7 个领域路由
try:
    from .endpoints_market import router as _market_router
    from .endpoints_news import router as _news_router
    from .endpoints_strategy import router as _strategy_router
    from .endpoints_system import router as _system_router
    from .endpoints_execution import router as _execution_router
    from .endpoints_frontend import router as _frontend_router
    from .endpoints_skills import router as _skills_router

    router.include_router(_market_router)
    router.include_router(_news_router)
    router.include_router(_strategy_router)
    router.include_router(_system_router)
    router.include_router(_execution_router)
    router.include_router(_frontend_router)
    router.include_router(_skills_router)
except Exception as e:
    _log.warning("domain routers not mounted: %s", e)

try:
    from .endpoints_pipeline import build_pipeline_router

    router.include_router(build_pipeline_router())
except Exception as e:
    _log.warning("strategy pipeline router not mounted: %s", e)
try:
    from .unified_auth_routes import build_unified_auth_router
    from .unified_orders_routes import build_unified_orders_routes_router
    from .unified_positions_routes import build_unified_positions_router
    from .unified_stocks_routes import build_unified_stocks_router

    router.include_router(build_unified_auth_router())
    router.include_router(build_unified_stocks_router())
    router.include_router(build_unified_orders_routes_router())
    router.include_router(build_unified_positions_router())
except Exception as e:
    _log.warning("unified Hongshan routers not mounted: %s", e)

try:
    from .endpoints_stock_qa import build_stock_qa_router

    router.include_router(build_stock_qa_router())
except Exception as e:
    _log.warning("stock_qa router not mounted: %s", e)

try:
    from .endpoints_user import build_user_router
    from .feishu_auth_routes import build_feishu_auth_router
    from .wechat_auth_routes import build_wechat_auth_routes

    router.include_router(build_user_router())
    router.include_router(build_wechat_auth_routes())
    router.include_router(build_feishu_auth_router())
except Exception as e:
    _log.warning("user/wechat/feishu routers not mounted: %s", e)

# 导入新数据端点（endpoints_api/new_data.py）
try:
    from .endpoints_api.new_data import router as new_data_router

    router.include_router(new_data_router)
except Exception as e:
    _log.warning("new_data router not mounted: %s", e)

try:
    from .endpoints_screening import build_screening_router

    router.include_router(build_screening_router())
except Exception as e:
    _log.warning("screening router not mounted: %s", e)


