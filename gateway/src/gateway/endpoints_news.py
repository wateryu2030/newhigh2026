"""News API endpoints."""

from __future__ import annotations

import logging
import os
from typing import Any, List, Optional

from fastapi import APIRouter, Body, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .response_utils import json_fail, json_ok

router = APIRouter()
_log = logging.getLogger(__name__)

# --- shared helpers imported from endpoints.py ---

from .endpoints_helpers import (  # noqa: E402
    _news_fallback_akshare,
    _news_fallback_akshare_multi_symbol,
    _news_sentiment_summary,
    _normalize_news_article_url,
    _policy_news_from_duckdb,
    _policy_sentiment_label,
    _duckdb_global_macro_news_summary,
    _run_manual_news_refresh,
    _fetch_news_for_research,
    _llm_news_summary,
    _fetch_hot_ticker_payload,
)


# --- News Routes ---


@router.get("/news")
def get_news(
    symbol: Optional[str] = None,
    limit: int = Query(100, ge=1, le=200),
) -> dict:
    """新闻列表：优先 DuckDB news_items；为空时从 akshare 东方财富补充（单股接口约 10 条，无代码时合并多只旗舰股）。"""
    items: List[dict] = []
    source: Optional[str] = None
    lim = max(1, min(int(limit or 100), 200))
    try:
        from data_engine import get_astock_duckdb_available, get_news_from_astock_duckdb

        if get_astock_duckdb_available():
            items = get_news_from_astock_duckdb(symbol=symbol, limit=lim)
            if items:
                source = "duckdb"
    except Exception:
        _log.error("Import failed", exc_info=True)
    if not items:
        sym = (symbol or "").strip()
        if sym:
            items = _news_fallback_akshare(symbol=sym, limit=lim)
        else:
            items = _news_fallback_akshare_multi_symbol(
                ("000001", "600519", "300750", "601318", "600036", "688981"),
                total_cap=lim,
            )
        if items:
            source = "akshare"
    sentiment = _news_sentiment_summary(items)
    news_items_total: Optional[int] = None
    try:
        from data_pipeline.storage.duckdb_manager import ensure_tables, get_conn

        _c = get_conn(read_only=False)
        ensure_tables(_c)
        news_items_total = int(_c.execute("SELECT COUNT(*) FROM news_items").fetchone()[0])
    except Exception:
        _log.error("Import failed", exc_info=True)
    out: dict = {"news": items, "source": source, "sentiment": sentiment}
    if news_items_total is not None:
        out["news_items_total"] = news_items_total
    return out


@router.get("/news/collector")
def get_news_collector(
    category: Optional[str] = None,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    """
    政策采集：读主库 DuckDB ``news_items``（symbol=__POLICY__，与 RSS/东财同库）。
    供 /news「政策采集」Tab。
    """
    duck_items, duck_ok = _policy_news_from_duckdb(category, limit, offset)
    if duck_items:
        sentiment = _news_sentiment_summary(duck_items)
        return {"news": duck_items, "source": "duckdb_policy", "sentiment": sentiment}

    empty_detail = "policy_news_empty" if duck_ok else "policy_news_read_error"
    return {
        "news": [],
        "source": None,
        "sentiment": {"count": 0, "avg_score": None, "positive_ratio": None},
        "detail": empty_detail,
    }


@router.get("/news/coverage")
def get_news_coverage() -> dict:
    """
    新闻检索能力分层说明（借鉴 AI-Search-Hub 多平台原生搜索理念，见 docs/NEWS_SEARCH_AI_SEARCH_HUB.md）。
    不含外部调用，供前端/Agent 展示扩展路径。
    """
    return {
        "tier1_in_repo": {
            "description": "站内默认：DuckDB news_items（含 RSS 宏观、东财个股、政策采集 __POLICY__）+ akshare 东方财富",
            "api": "GET /api/news",
            "summary_api": "POST /api/research/news-summary",
            "policy_collector_api": "GET /api/news/collector",
        },
        "tier2_extended_philosophy": {
            "description": "社媒/公众号/X/全球网页等多源舆情，借力各平台原生搜索",
            "reference": "https://github.com/minsight-ai-info/AI-Search-Hub",
            "routing_idea": "抖音热点→豆包系；公众号→元宝系；X→Grok；网页发现→Gemini 等",
            "integration": "本仓库不内置浏览器自动化；可本机跑 AI-Search-Hub 将结果贴回投研，或后续接官方联网 API",
        },
        "doc": "docs/NEWS_SEARCH_AI_SEARCH_HUB.md",
        "web_insight_api": "POST /api/news/web-insight（豆包/通义 + 现有 Key；抖音类热点需在火山控制台开联网插件）",
        "channels_doc": "docs/NEWS_CHANNELS_WITH_EXISTING_KEYS.md",
    }


class NewsManualRefreshBody(BaseModel):
    """手动拉取 RSS 宏观入库并可选推送一条汇总到 NEWS_BREAKING_WEBHOOK_URL（飞书等）。"""

    send_webhook: bool = False


@router.post("/news/manual-refresh")
def post_news_manual_refresh(
    body: NewsManualRefreshBody = Body(default_factory=NewsManualRefreshBody),
) -> Any:
    """
    手动触发 RSS 宏观入库，并返回最近条目摘要；可选 POST 一条汇总到 NEWS_BREAKING_WEBHOOK_URL。
    需登录：JWT_AUTH_REQUIRED=1 时由中间件校验 Bearer（本路由不在白名单）。
    失败时仍返回 200 + data.error，避免前端仅见 HTTP 500。
    """
    try:
        payload = _run_manual_news_refresh(bool(body.send_webhook))
        return json_ok(payload, source="news_manual_refresh")
    except Exception as e:
        _log.exception("news manual-refresh failed")
        return json_ok(
            {
                "rss_inserted": 0,
                "summary": "",
                "summary_lines": 0,
                "webhook_sent": False,
                "webhook_skipped_reason": "fatal",
                "error": str(e)[:500],
                "rss_fetch_ok": False,
            },
            source="news_manual_refresh_degraded",
        )


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


@router.get("/news/hot-ticker")
def get_news_hot_ticker() -> dict:
    """顶部滚动热点：东方财富热榜 + 财经快讯标题。"""
    return _fetch_hot_ticker_payload()
