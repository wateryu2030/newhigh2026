"""Shared helper functions extracted from endpoints.py to break circular imports.

These helpers are used by the 7 sub-module files (endpoints_market.py, endpoints_news.py,
endpoints_strategy.py, endpoints_system.py, endpoints_execution.py, endpoints_frontend.py,
endpoints_skills.py) to avoid circular imports with endpoints.py.

Usage:
    from .endpoints_helpers import <helper_name>
"""

import asyncio
import json
import logging
import os
from typing import Any, List, Optional

from fastapi import APIRouter, Body, HTTPException, Query, Request
from pydantic import BaseModel, Field

from core.ashare_symbol import normalize_ashare_symbol

from .response_utils import json_fail, json_ok

_log = logging.getLogger(__name__)


# --- Supporting classes & constants ---


class NewsManualRefreshBody(BaseModel):
    """手动拉取 RSS 宏观入库并可选推送一条汇总到 NEWS_BREAKING_WEBHOOK_URL（飞书等）。"""
    send_webhook: bool = False


# 首页「新闻手刷」专用：少量源 + 较短超时，避免反代/浏览器在完整默认 RSS 列表上超时或 500
_MANUAL_RSS_FEEDS_DEFAULT = (
    "http://feeds.bbci.co.uk/news/world/rss.xml,"
    "http://feeds.bbci.co.uk/news/business/rss.xml,"
    "http://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml"
)


def _is_ashare_symbol(symbol: str) -> bool:
    code = (symbol or "").strip().split(".", maxsplit=1)[0]
    return len(code) == 6 and code.isdigit()



def _pipeline_code_variants(symbol: str) -> List[str]:
    """a_stock_daily.code 可能是 000001.SZ / 000001 等，生成候选列表去重。"""
    raw = (symbol or "").strip().upper()
    if not raw:
        return []
    seen: set[str] = set()
    out: List[str] = []

    def add(x: str) -> None:
        x = x.strip()
        if x and x not in seen:
            seen.add(x)
            out.append(x)

    add(raw)
    base = raw.split(".", maxsplit=1)[0]
    if len(base) >= 5 and base.isdigit():
        add(base)
        ns = normalize_ashare_symbol(base)
        if ns.endswith(".SH"):
            add(f"{base}.SH")
            add(f"{base}.XSHG")
        elif ns.endswith(".BSE"):
            add(f"{base}.BJ")
            add(f"{base}.BSE")
        else:
            add(f"{base}.SZ")
            add(f"{base}.XSHE")
    return out



def _row_date_to_utc_iso(td: Any) -> str:
    """DuckDB / Python 日期 → ISO8601 UTC（与 daily_bars 路径一致）。"""
    import datetime as dt

    if hasattr(td, "to_pydatetime"):
        ts = td.to_pydatetime()
    elif isinstance(td, str):
        ts = dt.datetime.strptime(td[:10], "%Y-%m-%d")
    elif isinstance(td, dt.datetime):
        ts = td
    elif isinstance(td, dt.date):
        ts = dt.datetime.combine(td, dt.time.min)
    else:
        ts = dt.datetime.now(dt.timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=dt.timezone.utc)
    return ts.isoformat()



def _normalize_sym_show(code_used: str) -> str:
    sym_show = (code_used or "").strip()
    if "." in sym_show:
        return sym_show
    if len(sym_show) >= 8 and sym_show.isdigit():
        return f"{sym_show[:8]}.BJ"
    if len(sym_show) >= 6:
        six = sym_show[:6]
        ns = normalize_ashare_symbol(six)
        if ns.endswith(".BSE"):
            return f"{six}.BJ"
        return ns
    return sym_show



def _fetch_klines_from_a_stock_daily(symbol: str, limit: int = 120) -> Optional[dict]:
    """
    当 astock daily_bars 无数据时，从 a_stock_daily 读最近 N 根日线（纯 SQL + fetchall，不依赖 pandas）。
    """
    try:
        import os

        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path

        path = get_db_path()
        if not path or not os.path.isfile(path):
            return None
        lim = max(10, min(int(limit or 120), 500))
        conn = get_conn(read_only=False)
        try:
            for code_try in _pipeline_code_variants(symbol):
                rows = conn.execute(
                    """
                    SELECT code, date, open, high, low, close, volume
                    FROM (
                        SELECT code, date, open, high, low, close, volume
                        FROM a_stock_daily
                        WHERE code = ?
                        ORDER BY date DESC
                        LIMIT ?
                    ) AS sub
                    ORDER BY date ASC
                    """,
                    [code_try, lim],
                ).fetchall()
                if not rows:
                    continue
                data: List[dict] = []
                code_used = str(rows[-1][0])
                for r in rows:
                    _c, td, o, h, l, c, v = r[0], r[1], r[2], r[3], r[4], r[5], r[6]
                    data.append(
                        {
                            "t": _row_date_to_utc_iso(td),
                            "o": float(o or 0),
                            "h": float(h or 0),
                            "l": float(l or 0),
                            "c": float(c or 0),
                            "close": float(c or 0),
                            "v": float(v or 0),
                        }
                    )
                return {
                    "symbol": _normalize_sym_show(code_used),
                    "interval": "1d",
                    "limit": len(data),
                    "data": data,
                }
        finally:
            try:
                conn.close()
            except Exception:
                _log.error("Failed to close database connection", exc_info=True)
    except Exception:
        _log.exception("a_stock_daily klines fallback failed: %s", symbol)
    return None



def _ashare_suffix_from_code6(code6: str) -> str:
    if code6.startswith("6"):
        return "SH"
    if len(code6) == 8:
        return "BJ"
    if code6.startswith(("0", "3")):
        return "SZ"
    return "SZ"



def _fetch_klines_akshare_daily(symbol: str, limit: int = 160) -> Optional[dict]:
    """
    本地库均无日线时的结构化兜底：akshare 东财历史 K 线（与 mx-data 自然语言 API 不同，可直接映射 OHLCV）。
    默认开启；设置 KLINE_FALLBACK_AKSHARE=0 可关闭。
    """
    import os

    flag = os.environ.get("KLINE_FALLBACK_AKSHARE", "1").strip().lower()
    if flag in ("0", "false", "no", "off"):
        return None
    raw = (symbol or "").strip().split(".", maxsplit=1)[0].strip()
    code6 = raw[:6] if len(raw) >= 6 and raw[:6].isdigit() else ""
    if len(code6) != 6:
        return None
    lim = max(20, min(int(limit or 160), 800))
    try:
        import datetime as dt

        import akshare as ak  # type: ignore
    except ImportError:
        return None
    end = dt.datetime.now().strftime("%Y%m%d")
    start = (dt.datetime.now() - dt.timedelta(days=lim * 3 + 200)).strftime("%Y%m%d")
    try:
        df = ak.stock_zh_a_hist(
            symbol=code6[:6],
            period="daily",
            start_date=start,
            end_date=end,
            adjust="qfq",
        )
    except Exception:
        _log.exception("akshare stock_zh_a_hist failed: %s", code6)
        return None
    if df is None or df.empty:
        return None
    tail = df.tail(lim)
    sym_show = f"{code6}.{_ashare_suffix_from_code6(code6)}"
    data: List[dict] = []
    for _, row in tail.iterrows():
        d_raw = row.get("日期")
        if hasattr(d_raw, "strftime"):
            day = d_raw.strftime("%Y-%m-%d")
        else:
            day = str(d_raw)[:10]
        ts = f"{day}T00:00:00+00:00"
        data.append(
            {
                "t": ts,
                "o": float(row.get("开盘") or 0),
                "h": float(row.get("最高") or 0),
                "l": float(row.get("最低") or 0),
                "c": float(row.get("收盘") or 0),
                "close": float(row.get("收盘") or 0),
                "v": float(row.get("成交量") or 0),
            }
        )
    if not data:
        return None
    return {"symbol": sym_show, "interval": "1d", "limit": len(data), "data": data}



def _stooq_daily_symbol_map(sym: str) -> Optional[str]:
    """行情页 FALLBACK 标的 → Stooq 日线代码（免费 CSV，无需密钥）。"""
    u = sym.upper().strip()
    return {
        "GOLD": "xauusd",
        "XAUUSD": "xauusd",
        "SP500": "^spx",
        "SPX": "^spx",
        "NASDAQ": "^ndx",
        "NDX": "^ndx",
    }.get(u)



def _fetch_klines_stooq_daily(stooq_symbol: str, limit: int) -> Optional[dict]:
    import csv
    import io
    import urllib.parse
    import urllib.request

    flag = os.environ.get("STOOQ_KLINE_DISABLE", "0").strip().lower()
    if flag in ("1", "true", "yes"):
        return None

    lim = max(10, min(int(limit or 160), 3000))
    qs = urllib.parse.urlencode({"s": stooq_symbol.lower(), "i": "d"})
    url = f"https://stooq.com/q/d/l/?{qs}"
    try:
        with urllib.request.urlopen(url, timeout=28) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except Exception:
        _log.exception("stooq klines request failed: %s", stooq_symbol)
        return None
    if not text or "No data" in text[:300]:
        return None
    reader = csv.DictReader(io.StringIO(text))
    rows: List[dict] = []
    for raw in reader:
        rows.append({(k or "").strip(): v for k, v in raw.items()})
    if len(rows) < 2:
        return None
    tail = rows[-lim:]
    data: List[dict] = []
    for row in tail:
        day = (row.get("Date") or "").strip()
        if not day:
            continue
        try:
            o = float(row.get("Open") or 0)
            h = float(row.get("High") or 0)
            l = float(row.get("Low") or 0)
            c = float(row.get("Close") or 0)
        except (TypeError, ValueError):
            continue
        vol_raw = row.get("Volume")
        try:
            v = float(vol_raw) if vol_raw not in (None, "") else 0.0
        except (TypeError, ValueError):
            v = 0.0
        data.append(
            {
                "t": f"{day}T00:00:00+00:00",
                "o": o,
                "h": h,
                "l": l,
                "c": c,
                "close": c,
                "v": v,
            }
        )
    if not data:
        return None
    return {"symbol": stooq_symbol, "interval": "1d", "limit": len(data), "data": data}



def _fetch_klines_binance_usdt(symbol: str, interval: str, limit: int) -> Optional[dict]:
    """Binance 现货 USDT 公共 K 线（BTCUSDT / ETHUSDT 等）。"""
    import json
    import urllib.parse
    import urllib.request
    from datetime import datetime, timezone

    flag = os.environ.get("BINANCE_KLINE_DISABLE", "0").strip().lower()
    if flag in ("1", "true", "yes"):
        return None

    sym = symbol.upper().strip()
    if not sym.endswith("USDT"):
        return None
    iv_map = {"1h": "1h", "4h": "4h", "1d": "1d", "15m": "15m", "30m": "30m", "1w": "1w", "1m": "1m"}
    iv = iv_map.get((interval or "1h").lower(), "1h")
    lim = max(10, min(int(limit or 100), 1000))
    q = urllib.parse.urlencode({"symbol": sym, "interval": iv, "limit": lim})
    url = f"https://api.binance.com/api/v3/klines?{q}"
    try:
        with urllib.request.urlopen(url, timeout=18) as resp:
            raw = json.loads(resp.read().decode())
    except Exception:
        _log.exception("binance klines failed: %s", sym)
        return None
    if not raw:
        return None
    data: List[dict] = []
    for k in raw:
        ts_ms = int(k[0])
        t_iso = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S+00:00"
        )
        data.append(
            {
                "t": t_iso,
                "o": float(k[1]),
                "h": float(k[2]),
                "l": float(k[3]),
                "c": float(k[4]),
                "close": float(k[4]),
                "v": float(k[5]),
            }
        )
    return {"symbol": sym, "interval": iv, "limit": len(data), "data": data}


def _pipeline_quant_data_status() -> Optional[dict]:
    """
    使用 data_pipeline 表 a_stock_basic / a_stock_daily 统计（与 /api/system/data-overview 同源口径）。
    与 astock 命名表 stocks / daily_bars 可能并存于 quant_system.duckdb，数值常不一致，需并列展示。
    """
    try:
        import os

        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path

        path = get_db_path()
        if not path or not os.path.isfile(path):
            return None
        conn = get_conn(read_only=False)
        try:
            r1 = conn.execute(
                """
                SELECT COUNT(DISTINCT code) FROM a_stock_basic
                WHERE code IS NOT NULL AND TRIM(CAST(code AS VARCHAR)) <> ''
                """
            ).fetchone()
            stocks_n = int(r1[0]) if r1 and r1[0] is not None else 0
            r2 = conn.execute(
                "SELECT COUNT(*) AS n, MIN(date) AS dmin, MAX(date) AS dmax FROM a_stock_daily"
            ).fetchone()
            if not r2:
                return {
                    "stocks": stocks_n,
                    "daily_bars": 0,
                    "date_min": None,
                    "date_max": None,
                }
            return {
                "stocks": stocks_n,
                "daily_bars": int(r2[0]) if r2[0] is not None else 0,
                "date_min": str(r2[1])[:10] if r2[1] is not None else None,
                "date_max": str(r2[2])[:10] if r2[2] is not None else None,
            }
        finally:
            try:
                conn.close()
            except Exception:
                _log.error("Failed to close database connection", exc_info=True)
    except Exception:
        return None



def _ashare_skill():
    from skills.a_share_skill import load_skill

    return load_skill()



def _record_skill_call() -> None:
    """Skill 调用时增加 skill_stats 计数，供系统监控展示。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return
        conn = get_conn(read_only=False)
        try:
            n = conn.execute("SELECT COUNT(*) FROM skill_stats").fetchone()[0]
            if n == 0:
                conn.execute(
                    "INSERT INTO skill_stats (call_count, last_call_time) VALUES (0, NULL)"
                )
        except Exception:
            _log.error("File system operation failed", exc_info=True)
        conn.execute(
            "UPDATE skill_stats SET call_count = call_count + 1, last_call_time = CURRENT_TIMESTAMP"
        )
        conn.close()
    except Exception:
        _log.error("Failed to close database connection", exc_info=True)



def _short_ts_for_signal(val: Any) -> str:
    if val is None:
        return "—"
    if hasattr(val, "strftime"):
        try:
            return val.strftime("%m-%d %H:%M")
        except Exception:
            _log.error("Failed to close database connection", exc_info=True)
    s = str(val).replace("T", " ")
    if len(s) >= 16 and s[4] == "-":
        return s[5:16]
    return s[:16] if len(s) > 16 else s



def _optional_price(v: Any) -> Any:
    if v is None:
        return None
    try:
        x = float(v)
        if abs(x) < 1e-9:
            return None
        return round(x, 3)
    except Exception:
        return None



def _optional_pct(v: Any) -> Any:
    if v is None:
        return None
    try:
        return round(float(v), 2)
    except Exception:
        return None



def _market_db_query(table: str, order_by: str, limit: int = 100) -> list:
    """从 data_pipeline 的 quant_system.duckdb 读表，返回 list[dict]。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return []
        conn = get_conn(read_only=False)
        df = conn.execute(f"SELECT * FROM {table} ORDER BY {order_by} LIMIT ?", [limit]).fetchdf()
        conn.close()
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")
    except Exception:
        return []



def _safe_lhb_date_str(val: Any) -> Optional[str]:
    """避免 pandas NaT / 脏数据以 'NaT' 字符串返回前端。"""
    if val is None:
        return None
    try:
        import pandas as pd

        if pd.isna(val):
            return None
    except Exception:
        _log.error("Failed to close database connection", exc_info=True)
    s = str(val).strip()
    if not s or s.lower() in ("nat", "none"):
        return None
    if len(s) >= 10 and s[4] == "-":
        return s[:10]
    return s[:10] if len(s) >= 10 else None



def _safe_net_buy(val: Any) -> Any:
    if val is None:
        return None
    try:
        import pandas as pd

        if pd.isna(val):
            return None
    except Exception:
        _log.error("Failed to close database connection", exc_info=True)
    try:
        x = float(val)
        if x != x:  # NaN
            return None
        return round(x, 4)
    except Exception:
        return None



def _sniper_candidates_minimal(conn: Any, lim: int) -> list:
    """仅读 sniper_candidates（兼容列不全或 JOIN 失败），保证弹层有行。"""
    res = conn.execute(
        """
        WITH ranked AS (
            SELECT s.*,
                ROW_NUMBER() OVER (
                    PARTITION BY s.code
                    ORDER BY s.sniper_score DESC NULLS LAST
                ) AS rn
            FROM sniper_candidates s
        )
        SELECT code, theme, sniper_score, confidence, snapshot_time
        FROM ranked
        WHERE rn = 1
        ORDER BY sniper_score DESC NULLS LAST, code
        LIMIT ?
        """,
        [lim],
    )
    rows = res.fetchall()
    out = []
    for t in rows:
        code, theme, ss, cf, snap = (t + (None,) * 5)[:5]
        out.append(
            {
                "code": str(code or ""),
                "stock_name": "",
                "theme": str(theme or "").strip() or "—",
                "sniper_score": float(ss) if ss is not None else None,
                "confidence": float(cf) if cf is not None else None,
                "last_price": None,
                "change_pct": None,
                "updated_at": _short_ts_for_signal(snap),
            }
        )
    return out



def _status_to_state(s: str) -> str:
    """将 system_status 短串转为 running/error/idle。"""
    if not s or s == "not_run":
        return "idle"
    if s.startswith("error:"):
        return "error"
    return "running"



def _normalize_news_article_url(raw: object) -> str:
    """东方财富等来源可能返回相对路径或 // 协议相对 URL，补全为可点击的 https 链接。"""
    u = (raw or "").strip() if isinstance(raw, str) else str(raw or "").strip()
    if not u or u.lower() in ("nan", "none"):
        return ""
    if u.startswith("http://") or u.startswith("https://"):
        return u
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("/"):
        return "https://finance.eastmoney.com" + u
    return u



def _news_fallback_akshare(symbol: Optional[str] = None, limit: int = 50) -> List[dict]:
    """当 DuckDB 无新闻时，从 akshare 东方财富拉取个股/财经新闻作为补充（需安装 akshare）。"""
    try:
        import akshare as ak  # type: ignore

        code = (symbol or "000001").strip().split(".", maxsplit=1)[0]
        if len(code) < 5:
            code = "000001"
        df = ak.stock_news_em(symbol=code)
        if df is None or df.empty:
            return []
        lim = max(1, min(int(limit or 10), 30))
        out = []
        cols = [str(c) for c in df.columns.tolist()]
        title_col = next((c for c in ["新闻标题", "title"] if c in cols), cols[0] if cols else None)
        content_col = next((c for c in ["新闻内容", "content"] if c in cols), None)
        time_col = next((c for c in ["发布时间", "publish_time"] if c in cols), None)
        url_col = next((c for c in ["新闻链接", "链接", "url", "link"] if c in cols), None)
        source_col = next((c for c in ["文章来源", "source"] if c in cols), None)
        for _, row in df.head(lim).iterrows():
            url_raw = str(row.get(url_col, "")) if url_col else ""
            item = {
                "symbol": code,
                "title": str(row.get(title_col, "")) if title_col else "",
                "content": (str(row.get(content_col, ""))[:500]) if content_col else "",
                "publish_time": str(row.get(time_col, "")) if time_col else "",
                "url": _normalize_news_article_url(url_raw),
                "source": str(row.get(source_col, "东方财富")) if source_col else "东方财富",
                "source_site": "eastmoney",
                "sentiment_score": None,
                "sentiment_label": None,
            }
            out.append(item)
        return out
    except Exception:
        return []



def _news_fallback_akshare_multi_symbol(codes: tuple[str, ...], total_cap: int) -> List[dict]:
    """
    东财 ``stock_news_em`` 单次约 10 条/股；留空个股代码查询时用多股合并凑够列表（去重 title+时间）。
    """
    cap = max(1, min(int(total_cap or 100), 200))
    seen: set[tuple[str, str]] = set()
    out: List[dict] = []
    for code in codes:
        if len(out) >= cap:
            break
        chunk = _news_fallback_akshare(symbol=code, limit=12)
        for it in chunk:
            title = (it.get("title") or "").strip()
            pub = (it.get("publish_time") or "").strip()
            key = (title, pub)
            if not title or key in seen:
                continue
            seen.add(key)
            out.append(it)
            if len(out) >= cap:
                break
    return out



def _policy_sentiment_label(score: Any) -> Optional[str]:
    try:
        s = float(score)
    except (TypeError, ValueError):
        return None
    if s > 0.1:
        return "利好"
    if s < -0.1:
        return "利空"
    return "中性"



def _policy_news_from_duckdb(
    category: Optional[str], limit: int, offset: int
) -> tuple[List[dict], bool]:
    """从主库 ``news_items`` 读政策采集（symbol=__POLICY__）。返回 (items, ok)；ok=False 表示读库失败。"""
    from data_pipeline.collectors.policy_news_duckdb import POLICY_SYMBOL
    from data_pipeline.storage.duckdb_manager import ensure_tables, get_conn

    items: List[dict] = []
    try:
        conn = get_conn(read_only=False)
        ensure_tables(conn)
        q = (
            "SELECT title, source, tag, content, url, keyword, publish_time, "
            "sentiment_score, sentiment_label "
            "FROM news_items WHERE symbol = ? AND (? IS NULL OR tag = ?) "
            "ORDER BY COALESCE(publish_time, '') DESC, ts DESC LIMIT ? OFFSET ?"
        )
        cur = conn.execute(q, [POLICY_SYMBOL, category, category, limit, offset])
        for row in cur.fetchall():
            title = row[0] or ""
            source = row[1] or ""
            tag = row[2] or ""
            content = (row[3] or "")[:2000]
            url = row[4] or None
            keyword = (row[5] or "")[:200] if row[5] else None
            pub = (row[6] or "")[:19] if row[6] else ""
            sc = row[7]
            lbl = row[8]
            items.append(
                {
                    "title": title,
                    "content": content,
                    "url": url,
                    "source": source,
                    "publish_time": pub,
                    "tag": tag,
                    "keyword": keyword,
                    "sentiment_score": float(sc) if sc is not None else None,
                    "sentiment_label": lbl or _policy_sentiment_label(sc),
                }
            )
        return items, True
    except Exception as e:
        _log.warning("policy news duckdb read failed: %s", e)
        return [], False



def _hot_ticker_from_duckdb_news(limit: int = 16) -> List[dict]:
    """热榜、东财实时均失败时，用 DuckDB news_items 近期标题兜底（日内任务写入后可滚动展示）。"""
    out: List[dict] = []
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path

        if not os.path.isfile(get_db_path()):
            return out
        conn = get_conn(read_only=True)
        rows = conn.execute(
            """
            SELECT title, symbol FROM news_items
            WHERE title IS NOT NULL AND LENGTH(TRIM(CAST(title AS VARCHAR))) > 6
            ORDER BY ts DESC NULLS LAST
            LIMIT ?
            """,
            [max(4, int(limit))],
        ).fetchall()
        conn.close()
        for title, sym in rows or []:
            t = str(title or "").strip()[:72]
            if not t:
                continue
            code = str(sym or "").strip()
            code6 = code[-6:] if len(code) >= 6 and code[-6:].isdigit() else None
            out.append({"type": "news_db", "text": t, "code": code6})
    except Exception:
        _log.error("Failed to close database connection", exc_info=True)
    return out



def _fetch_hot_ticker_payload() -> dict:
    """东财热榜 + 快讯标题，供顶部滚动条。"""
    import datetime as dt

    lines: List[dict] = []
    prefix = "🔥 "
    try:
        import akshare as ak

        df = ak.stock_hot_rank_em()
        if df is not None and not df.empty:
            for _, row in df.head(12).iterrows():
                name = str(row.get("股票名称") or "").strip()
                pct = row.get("涨跌幅")
                code = str(row.get("代码") or "").replace("SH", "").replace("SZ", "").replace("BJ", "")
                if not name:
                    continue
                try:
                    p = float(pct)
                    ps = f"{p:+.2f}%"
                except (TypeError, ValueError):
                    ps = str(pct or "")
                lines.append(
                    {
                        "type": "hot_rank",
                        "text": f"{name} {ps}",
                        "code": code[-6:] if len(code) >= 6 else code,
                    }
                )
    except Exception:
        _log.error("Failed to close database connection", exc_info=True)

    if len(lines) < 6:
        try:
            extra = _news_fallback_akshare(None, 15)
            for n in extra[:10]:
                t = (n.get("title") or "").strip()
                if t and len(t) > 8:
                    lines.append({"type": "news", "text": t[:60], "code": None})
        except Exception:
            _log.error("Failed to close database connection", exc_info=True)

    if len(lines) < 6:
        for x in _hot_ticker_from_duckdb_news(18):
            lines.append(x)
            if len(lines) >= 14:
                break

    if not lines:
        lines = [
            {
                "type": "tip",
                "text": "热点加载中：本机无法实时访问东财时可依赖 Tushare/日内同步的站内新闻；检查代理或运行 scripts/start_schedulers.py intraday-now",
                "code": None,
            }
        ]

    parts = [x["text"] for x in lines[:20]]
    banner = prefix + " · ".join(parts)
    return {
        "lines": lines[:20],
        "banner": banner[:1200],
        "updated_at": dt.datetime.now().isoformat(timespec="seconds"),
    }



def _duckdb_global_macro_news_summary(limit: int = 20) -> tuple[str, int]:
    """自 DuckDB 取最近国际宏观 / __GLOBAL__ 标题列表，用于汇总正文。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path

        if not os.path.isfile(get_db_path()):
            return "", 0
        lim = max(1, min(50, int(limit)))
        conn = get_conn(read_only=True)
        if conn is None:
            return "", 0
        try:
            rows = conn.execute(
                """
                SELECT title, url, source_site
                FROM news_items
                WHERE symbol = '__GLOBAL__' OR TRIM(COALESCE(tag, '')) = '国际宏观'
                ORDER BY ts DESC NULLS LAST
                LIMIT ?
                """,
                [lim],
            ).fetchall()
        finally:
            try:
                conn.close()
            except Exception:
                _log.error("Failed to close database connection", exc_info=True)
    except Exception:
        return "", 0
    lines: List[str] = []
    for title, url, site in rows or []:
        ti = str(title or "").strip()[:180]
        if not ti:
            continue
        u = str(url or "").strip()[:120]
        meta = str(site or "").strip()
        extra = f" | {u}" if u else ""
        src = f" ({meta})" if meta else ""
        lines.append(f"· {ti}{extra}{src}")
    return "\n".join(lines), len(lines)



def _run_manual_news_refresh(send_webhook: bool) -> dict:
    """RSS 拉取（关闭逐条突发推送）→ 汇总文案 → 可选一条 Webhook。"""
    from data_pipeline.collectors.rss_macro_news import _send_feishu_text, update_rss_macro_news

    feeds_manual = (os.environ.get("NEWS_RSS_FEEDS_MANUAL") or "").strip() or _MANUAL_RSS_FEEDS_DEFAULT
    n_inserted = 0
    rss_fetch_error: Optional[str] = None
    try:
        _to = float(str(os.environ.get("NEWS_RSS_MANUAL_TIMEOUT_SEC", "12")).strip() or "12")
    except (TypeError, ValueError):
        _to = 12.0
    try:
        _mf = int(str(os.environ.get("NEWS_RSS_MANUAL_MAX_FEEDS", "4")).strip() or "4")
    except (TypeError, ValueError):
        _mf = 4
    try:
        n_inserted = int(
            update_rss_macro_news(
                feeds_csv=feeds_manual,
                send_breaking_alerts=False,
                max_per_feed=25,
                feed_timeout=max(5.0, min(45.0, _to)),
                max_feed_urls=max(1, min(12, _mf)),
            )
        )
    except Exception as e:
        rss_fetch_error = str(e)[:500]
        _log.warning("manual RSS refresh insert failed: %s", rss_fetch_error)

    summary, n_lines = _duckdb_global_macro_news_summary(20)
    front = (os.environ.get("FRONTEND_BASE_URL") or "https://htma.newhigh.com.cn").rstrip("/")
    head = f"【新闻汇总｜手动刷新】RSS 新写入 {n_inserted} 条。全文: {front}/news\n\n"
    body_text = summary or "（暂无国际宏观 RSS 条目，请确认采集与 DuckDB。）"
    full_text = (head + body_text)[:3900]

    webhook_sent = False
    webhook_skipped_reason: Optional[str] = None
    if send_webhook:
        wh = (os.environ.get("NEWS_BREAKING_WEBHOOK_URL") or "").strip()
        if wh:
            webhook_sent = bool(_send_feishu_text(wh, full_text))
            if not webhook_sent:
                webhook_skipped_reason = "webhook_failed"
        else:
            webhook_skipped_reason = "no_webhook_url"
    else:
        webhook_skipped_reason = "send_webhook_false"

    out = {
        "rss_inserted": n_inserted,
        "summary": summary,
        "summary_lines": n_lines,
        "webhook_sent": webhook_sent,
        "webhook_skipped_reason": webhook_skipped_reason,
    }
    if rss_fetch_error:
        out["error"] = rss_fetch_error
        out["rss_fetch_ok"] = False
    else:
        out["rss_fetch_ok"] = True
    return out



def _fetch_news_for_research(symbol: Optional[str], limit: int) -> tuple[List[dict], Optional[str]]:
    """与 GET /news 一致的新闻拉取，供投研摘要复用。"""
    lim = max(1, min(int(limit or 100), 200))
    items: List[dict] = []
    source: Optional[str] = None
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
    return items, source



def _llm_news_summary(blob: str, symbol_label: str, focus: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    调用大模型生成投研向新闻摘要。返回 (summary_text, model_used, error)。
    优先 DashScope（BAILIAN/DASHSCOPE_API_KEY），其次 OPENAI_API_KEY。
    """
    import os

    sys_prompt = (
        "你是 A 股投研助手。根据用户提供的新闻列表，用中文输出：\n"
        "1) 【核心摘要】300 字以内；\n"
        "2) 【利好要点】条列；\n"
        "3) 【风险要点】条列；\n"
        "4) 文末必须写「不构成投资建议」。\n"
        "仅基于给定新闻，勿编造未出现的事实。"
    )
    user_prompt = f"标的/范围：{symbol_label}\n"
    if focus:
        user_prompt += f"用户关注点：{focus}\n"
    user_prompt += "新闻列表：\n" + blob[:12000]

    key = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("BAILIAN_API_KEY")
    model_ds = os.environ.get("RESEARCH_LLM_MODEL", "qwen-turbo")
    if key:
        try:
            import requests

            r = requests.post(
                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                timeout=90,
                json={
                    "model": model_ds,
                    "messages": [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": 2000,
                },
            )
            data = r.json()
            if r.status_code != 200:
                err = data.get("message") or data.get("error", {}).get("message") or r.text[:200]
                return None, None, f"dashscope_http_{r.status_code}: {err}"
            choices = data.get("choices") or []
            if not choices:
                return None, None, "dashscope_empty_choices"
            text = (choices[0].get("message") or {}).get("content") or ""
            return text.strip() or None, model_ds, None
        except Exception as e:
            return None, None, f"dashscope:{e!s}"[:300]

    key_oai = os.environ.get("OPENAI_API_KEY")
    model_oai = os.environ.get("RESEARCH_OPENAI_MODEL", "gpt-4o-mini")
    if key_oai:
        try:
            import requests

            r = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key_oai}", "Content-Type": "application/json"},
                timeout=90,
                json={
                    "model": model_oai,
                    "messages": [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": 2000,
                },
            )
            data = r.json()
            if r.status_code != 200:
                return None, None, f"openai_{r.status_code}:{str(data)[:200]}"
            text = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
            return text.strip() or None, model_oai, None
        except Exception as e:
            return None, None, f"openai:{e!s}"[:300]

    return None, None, "no_llm_key"



def _news_sentiment_summary(items: List[dict]) -> Optional[dict]:
    """从新闻列表计算情感汇总：条数、均值、正面占比。"""
    if not items:
        return None
    scores = [float(x["sentiment_score"]) for x in items if x.get("sentiment_score") is not None]
    if not scores:
        return {"count": len(items), "avg_score": None, "positive_ratio": None}
    import statistics

    avg = statistics.mean(scores)
    positive = sum(1 for s in scores if s > 0) / len(scores)
    return {"count": len(items), "avg_score": round(avg, 2), "positive_ratio": round(positive, 2)}



def _save_backtest_to_strategy_market(strategy_id: str, name: str, result: dict) -> bool:
    """将回测结果写入 strategy_market 表。"""
    try:
        from data_pipeline.strategy_market_writer import upsert_strategy_market_from_backtest

        return upsert_strategy_market_from_backtest(strategy_id, name, result)
    except Exception:
        return False



def _run_backtest_internal(
    symbol: str,
    start_date: Optional[str],
    end_date: Optional[str],
    signal_source: str = "trade_signals",
    init_cash: float = 10000.0,
    fees: float = 0.001,
    slippage: float = 0.0,
    symbols: Optional[str] = None,
) -> dict:
    """Shared logic for POST and GET backtest. symbols 为逗号分隔多标的时走组合回测。"""
    import os
    import sys
    from datetime import datetime, timedelta

    _root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    for _d in ["backtest-engine/src", "data-pipeline/src", "core/src"]:
        _p = os.path.join(_root, _d)
        if os.path.isdir(_p) and _p not in sys.path:
            sys.path.insert(0, _p)
    from backtest_engine import run_backtest_from_db, run_backtest_multi_from_db

    end = end_date or datetime.now().strftime("%Y-%m-%d")
    start = start_date or (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    sym_list = [s.strip() for s in (symbols or symbol).split(",") if s.strip()]
    if len(sym_list) > 1:
        out = run_backtest_multi_from_db(
            symbols=sym_list,
            start_date=start,
            end_date=end,
            signal_source=signal_source,
            init_cash=init_cash,
            fees=fees,
            slippage=slippage,
        )
        base = {
            "symbols": sym_list,
            "start_date": start,
            "end_date": end,
            "signal_source": signal_source,
        }
    else:
        sym = sym_list[0] if sym_list else symbol
        out = run_backtest_from_db(
            symbol=sym,
            start_date=start,
            end_date=end,
            signal_source=signal_source,
            init_cash=init_cash,
            fees=fees,
            slippage=slippage,
        )
        base = {"symbol": sym, "start_date": start, "end_date": end, "signal_source": signal_source}
    return {
        **base,
        "equity_curve": out.get("equity_curve") or [],
        "sharpe_ratio": out.get("sharpe_ratio"),
        "max_drawdown": out.get("max_drawdown"),
        "total_return": out.get("total_return"),
        "win_rate_pct": out.get("win_rate_pct"),
        "profit_factor": out.get("profit_factor"),
        "total_profit": out.get("total_profit"),
        "trade_count": out.get("trade_count"),
        "error": out.get("error"),
    }



def _risk_engine_module():
    """Lazy import risk_engine (requires risk-engine/src + data-pipeline on path)."""
    import os
    import sys

    _root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    for _d in ["risk-engine/src", "data-pipeline/src"]:
        _p = os.path.join(_root, _d)
        if os.path.isdir(_p) and _p not in sys.path:
            sys.path.insert(0, _p)
    from risk_engine import load_rules, evaluate, save_rule

    return load_rules, evaluate, save_rule



def _execution_broker_module():
    import os
    import sys

    _root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    _p = os.path.join(_root, "execution-engine/src")
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
    from execution_engine.brokers import execution_mode, set_execution_mode, get_broker

    return execution_mode, set_execution_mode, get_broker



def _simulated_module():
    """Lazy import execution_engine.simulated (requires execution-engine/src on path)."""
    import os
    import sys

    _root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    _p = os.path.join(_root, "execution-engine/src")
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
    from execution_engine.simulated import (
        step_simulated,
        get_positions as sim_get_positions,
        get_orders as sim_get_orders,
        get_account_snapshots as sim_get_account_snapshots,
    )

    return step_simulated, sim_get_positions, sim_get_orders, sim_get_account_snapshots



def _metrics_from_equity_curve(equity: List[float]) -> tuple[Optional[float], Optional[float]]:
    """由权益曲线估算夏普（假设步长为交易日）与最大回撤百分比。"""
    if len(equity) < 3:
        return None, None
    rets: List[float] = []
    for i in range(1, len(equity)):
        p, c = equity[i - 1], equity[i]
        if p <= 0:
            continue
        rets.append((c - p) / p)
    if len(rets) < 2:
        return None, None
    peak = float(equity[0])
    mdd = 0.0
    for x in equity:
        xf = float(x)
        peak = max(peak, xf)
        if peak > 0:
            mdd = max(mdd, (peak - xf) / peak)
    try:
        import statistics

        mu = statistics.mean(rets)
        sd = statistics.pstdev(rets)
    except Exception:
        return None, round(mdd * 100, 2)
    sharpe = (mu / sd * (252**0.5)) if sd > 1e-12 else None
    return (
        round(float(sharpe), 2) if sharpe is not None else None,
        round(mdd * 100, 2),
    )



def _dashboard_top_strategies_from_db(limit: int = 3) -> List[dict]:
    """策略榜：仅展示 strategy_market 中真实回测写入的记录，无则空列表。"""
    out: List[dict] = []
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return out
        conn = get_conn(read_only=True)
        if not conn:
            return out
        try:
            df = conn.execute(
                """SELECT strategy_id, name, return_pct FROM strategy_market
                   ORDER BY updated_at DESC LIMIT ?""",
                [limit],
            ).fetchdf()
            if df is None or df.empty:
                return out
            for _, row in df.iterrows():
                sid = str(row.get("strategy_id") or "").strip()
                if not sid:
                    continue
                rpc = row.get("return_pct")
                out.append(
                    {
                        "id": sid,
                        "name": str(row.get("name") or sid.replace("_", " ").title()),
                        "return_pct": float(rpc) if rpc is not None else None,
                    }
                )
        finally:
            try:
                conn.close()
            except Exception:
                _log.error("Failed to close database connection", exc_info=True)
    except Exception:
        _log.error("Failed to close database connection", exc_info=True)
    return out



def _dashboard_from_duckdb() -> Optional[dict]:
    """当 newhigh 本地 DuckDB 可用时，用 A 股日线聚合出真实收益曲线与今日收益。"""
    try:
        from data_engine import (
            get_astock_duckdb_available,
            get_stocks_for_api,
            fetch_klines_from_astock_duckdb,
        )

        if not get_astock_duckdb_available():
            return None
        stocks = get_stocks_for_api()
        if not stocks:
            return None
        # 选一只有日线数据的标的（首只可能无 bar）；限制探测只数，避免 /dashboard 过慢触发反代 502
        rows = []
        sym = None
        for s in stocks[:20]:
            sym = s["symbol"]
            rows = fetch_klines_from_astock_duckdb(sym, limit=60)
            if len(rows) >= 2:
                break
        if len(rows) < 2:
            return None
        closes = [r.close for r in rows]
        # 收益曲线：归一化到 10M 起，按收益率缩放
        base = closes[0]
        if base <= 0:
            return None
        equity_curve = [10e6 * (c / base) for c in closes]
        last_close, prev_close = closes[-1], closes[-2]
        daily_return_pct = ((last_close - prev_close) / prev_close * 100) if prev_close else 0.0
        total_equity = equity_curve[-1] if equity_curve else 10e6
        sharpe, mdd = _metrics_from_equity_curve(equity_curve)
        top_strategies = _dashboard_top_strategies_from_db(3)
        return {
            "total_equity": total_equity,
            "daily_return_pct": round(daily_return_pct, 2),
            "sharpe_ratio": sharpe,
            "max_drawdown_pct": mdd,
            "equity_curve": equity_curve,
            "top_strategies": top_strategies,
            "ai_generated_today": None,
            "strategies_alive": None,
            "strategies_live": None,
            "equity_proxy_symbol": sym,
            "dashboard_notes": [
                "equity_curve_is_normalized_to_10M_from_first_symbol_with_bars_not_portfolio",
            ],
        }
    except Exception:
        return None



def _run_evolution_background(task_id: str, population_limit: int, symbol: str) -> None:
    """后台执行进化并更新 evolution_tasks 表。"""
    import json

    try:
        import os
        import sys

        _root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        for _d in ["openclaw_engine", "backtest-engine/src", "data-pipeline/src", "core/src"]:
            _p = os.path.join(_root, _d)
            if os.path.isdir(_p) and _p not in sys.path:
                sys.path.insert(0, _p)
        from openclaw_engine import run_evolution_cycle

        result = run_evolution_cycle(population_limit=population_limit, symbol=symbol)
        status, res_str = "success", json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        status, res_str = "failed", json.dumps({"error": str(e)}, ensure_ascii=False)
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path

        if __import__("os").path.isfile(get_db_path()):
            conn = get_conn(read_only=False)
            conn.execute(
                "UPDATE evolution_tasks SET status = ?, result = ? WHERE task_id = ?",
                [status, res_str, task_id],
            )
            conn.close()
    except Exception:
        _log.error("Failed to close database connection", exc_info=True)



def _alpha_lab_code6(expr: str) -> str:
    """SQL：将 code 列规范为 6 位主干（大写、去后缀）。"""
    return f"split_part(UPPER(TRIM(CAST({expr} AS VARCHAR))), '.', 1)"



def _alpha_lab_binding_note() -> str:
    return (
        "漏斗由统一 DuckDB 内 market_signals / trade_signals / "
        "sniper_candidates / sim_positions 等汇总，作为 Alpha 管线代理指标；"
        "非 OpenClaw 逐笔血缘，待进化引擎写入专用阶段表后可切换。"
    )



def _alpha_lab_compute_counts(conn: Any) -> dict:
    """Alpha 工坊漏斗数字：近窗内去重标的（与下钻同一口径）。"""
    c6_ms = _alpha_lab_code6("ms.code")
    c6_sn = _alpha_lab_code6("sn.code")
    c6_hm = _alpha_lab_code6("hm.code")
    c6_ts = _alpha_lab_code6("ts.code")
    c6_sp = _alpha_lab_code6("sp.code")
    win = "CURRENT_TIMESTAMP - INTERVAL 30 DAY"
    # 生成池：扫描/游资/狙击/信号的并集
    gen_sql = f"""
        SELECT COUNT(*) FROM (
            SELECT DISTINCT {c6_ms}
            FROM market_signals ms
            WHERE ms.code IS NOT NULL AND TRIM(CAST(ms.code AS VARCHAR)) <> ''
              AND ms.snapshot_time >= {win}
            UNION
            SELECT DISTINCT {c6_sn}
            FROM sniper_candidates sn
            WHERE sn.code IS NOT NULL AND TRIM(CAST(sn.code AS VARCHAR)) <> ''
              AND (sn.snapshot_time IS NULL OR sn.snapshot_time >= {win})
            UNION
            SELECT DISTINCT {c6_hm}
            FROM hotmoney_signals hm
            WHERE hm.code IS NOT NULL AND TRIM(CAST(hm.code AS VARCHAR)) <> ''
              AND hm.snapshot_time >= {win}
            UNION
            SELECT DISTINCT {c6_ts}
            FROM trade_signals ts
            WHERE ts.code IS NOT NULL AND TRIM(CAST(ts.code AS VARCHAR)) <> ''
              AND ts.snapshot_time >= {win}
        ) g
    """
    # 回测代理：策略侧交易信号
    bt_sql = f"""
        SELECT COUNT(*) FROM (
            SELECT DISTINCT {c6_ts}
            FROM trade_signals ts
            WHERE ts.code IS NOT NULL AND TRIM(CAST(ts.code AS VARCHAR)) <> ''
              AND ts.snapshot_time >= {win}
        ) b
    """
    # 风控代理：置信度阈上
    risk_sql = f"""
        SELECT COUNT(*) FROM (
            SELECT DISTINCT {c6_ts}
            FROM trade_signals ts
            WHERE ts.code IS NOT NULL AND TRIM(CAST(ts.code AS VARCHAR)) <> ''
              AND ts.snapshot_time >= {win}
              AND ts.confidence IS NOT NULL AND ts.confidence >= 0.5
        ) r
    """
    dep_sql = f"""
        SELECT COUNT(*) FROM (
            SELECT DISTINCT {c6_sp}
            FROM sim_positions sp
            WHERE sp.code IS NOT NULL AND TRIM(CAST(sp.code AS VARCHAR)) <> ''
              AND sp.qty IS NOT NULL AND ABS(sp.qty) > 1e-9
        ) d
    """
    g = int(conn.execute(gen_sql).fetchone()[0] or 0)
    b = int(conn.execute(bt_sql).fetchone()[0] or 0)
    r = int(conn.execute(risk_sql).fetchone()[0] or 0)
    d = int(conn.execute(dep_sql).fetchone()[0] or 0)
    return {
        "generated_today": g,
        "passed_backtest": b,
        "passed_risk": r,
        "deployed": d,
    }



def _alpha_lab_drill_rows(conn: Any, stage: str, limit: int) -> list:
    c6_ms = _alpha_lab_code6("ms.code")
    c6_sn = _alpha_lab_code6("sn.code")
    c6_hm = _alpha_lab_code6("hm.code")
    c6_ts = _alpha_lab_code6("ts.code")
    c6_sp = _alpha_lab_code6("sp.code")
    win = "CURRENT_TIMESTAMP - INTERVAL 30 DAY"
    lim = max(1, min(int(limit or 100), 500))
    st = (stage or "").strip().lower()

    def _row(code6: str, name: Any, subtitle: str, score: Any, conf: Any, sid: Any, snap: Any) -> dict:
        bc = str(code6 or "").strip()
        return {
            "code": bc,
            "stock_name": str(name or "").strip(),
            "subtitle": subtitle or None,
            "score": float(score) if score is not None else None,
            "confidence": float(conf) if conf is not None else None,
            "strategy_id": str(sid).strip() if sid else None,
            "snapshot_time": str(snap) if snap is not None else None,
        }

    if st == "generated":
        sql = f"""
            WITH all_gen AS (
                SELECT {c6_ms} AS code6, ms.snapshot_time AS ts,
                    CAST(ms.signal_type AS VARCHAR) AS stype,
                    CAST(ms.score AS DOUBLE) AS sc
                FROM market_signals ms
                WHERE ms.code IS NOT NULL AND TRIM(CAST(ms.code AS VARCHAR)) <> ''
                  AND ms.snapshot_time >= {win}
                UNION ALL
                SELECT {c6_sn}, sn.snapshot_time,
                    'sniper', sn.sniper_score
                FROM sniper_candidates sn
                WHERE sn.code IS NOT NULL AND TRIM(CAST(sn.code AS VARCHAR)) <> ''
                  AND (sn.snapshot_time IS NULL OR sn.snapshot_time >= {win})
                UNION ALL
                SELECT {c6_hm}, hm.snapshot_time,
                    'hotmoney', hm.win_rate
                FROM hotmoney_signals hm
                WHERE hm.code IS NOT NULL AND TRIM(CAST(hm.code AS VARCHAR)) <> ''
                  AND hm.snapshot_time >= {win}
                UNION ALL
                SELECT {c6_ts}, ts.snapshot_time,
                    CAST(ts.signal AS VARCHAR), ts.signal_score
                FROM trade_signals ts
                WHERE ts.code IS NOT NULL AND TRIM(CAST(ts.code AS VARCHAR)) <> ''
                  AND ts.snapshot_time >= {win}
            ),
            agg AS (
                SELECT code6,
                    MAX(ts) AS last_ts,
                    arg_max(stype, ts) AS last_type,
                    arg_max(sc, ts) AS last_score
                FROM all_gen
                GROUP BY 1
            ),
            basic_rn AS (
                SELECT name,
                    split_part(CAST(code AS VARCHAR), '.', 1) AS code6,
                    ROW_NUMBER() OVER (
                        PARTITION BY split_part(CAST(code AS VARCHAR), '.', 1)
                        ORDER BY CAST(code AS VARCHAR) DESC
                    ) AS rn
                FROM a_stock_basic
            )
            SELECT a.code6, br.name, a.last_type, a.last_score, a.last_ts
            FROM agg a
            LEFT JOIN basic_rn br ON br.code6 = a.code6 AND br.rn = 1
            ORDER BY a.last_ts DESC NULLS LAST, a.code6
            LIMIT ?
        """
        rows = conn.execute(sql, [lim]).fetchall() or []
        out = []
        for t in rows:
            code6, name, ltype, lsc, ts = (t + (None,) * 5)[:5]
            lt = str(ltype or "").strip() or "signal"
            sub = lt + (f" · {lsc:.4g}" if lsc is not None else "")
            out.append(_row(code6, name, sub, lsc, None, None, ts))
        return out

    if st in ("backtest", "passed_backtest"):
        sql = f"""
            WITH ts_rn AS (
                SELECT ts.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY {c6_ts}
                        ORDER BY ts.snapshot_time DESC NULLS LAST
                    ) AS rn
                FROM trade_signals ts
                WHERE ts.code IS NOT NULL AND TRIM(CAST(ts.code AS VARCHAR)) <> ''
                  AND ts.snapshot_time >= {win}
            ),
            basic_rn AS (
                SELECT name,
                    split_part(CAST(code AS VARCHAR), '.', 1) AS code6,
                    ROW_NUMBER() OVER (
                        PARTITION BY split_part(CAST(code AS VARCHAR), '.', 1)
                        ORDER BY CAST(code AS VARCHAR) DESC
                    ) AS rn
                FROM a_stock_basic
            )
            SELECT
                split_part(UPPER(TRIM(CAST(t.code AS VARCHAR))), '.', 1),
                br.name,
                CAST(t.signal AS VARCHAR),
                t.signal_score,
                t.confidence,
                t.strategy_id,
                t.snapshot_time
            FROM ts_rn t
            LEFT JOIN basic_rn br
                ON br.code6 = split_part(UPPER(TRIM(CAST(t.code AS VARCHAR))), '.', 1) AND br.rn = 1
            WHERE t.rn = 1
            ORDER BY t.snapshot_time DESC NULLS LAST, t.code
            LIMIT ?
        """
        rows = conn.execute(sql, [lim]).fetchall() or []
        out = []
        for t in rows:
            c6, name, sig, ss, cf, sid, ts = (t + (None,) * 7)[:7]
            out.append(_row(c6, name, str(sig or "signal"), ss, cf, sid, ts))
        return out

    if st in ("risk", "passed_risk"):
        sql = f"""
            WITH ts_rn AS (
                SELECT ts.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY {c6_ts}
                        ORDER BY ts.snapshot_time DESC NULLS LAST
                    ) AS rn
                FROM trade_signals ts
                WHERE ts.code IS NOT NULL AND TRIM(CAST(ts.code AS VARCHAR)) <> ''
                  AND ts.snapshot_time >= {win}
                  AND ts.confidence IS NOT NULL AND ts.confidence >= 0.5
            ),
            basic_rn AS (
                SELECT name,
                    split_part(CAST(code AS VARCHAR), '.', 1) AS code6,
                    ROW_NUMBER() OVER (
                        PARTITION BY split_part(CAST(code AS VARCHAR), '.', 1)
                        ORDER BY CAST(code AS VARCHAR) DESC
                    ) AS rn
                FROM a_stock_basic
            )
            SELECT
                split_part(UPPER(TRIM(CAST(t.code AS VARCHAR))), '.', 1),
                br.name,
                CAST(t.signal AS VARCHAR),
                t.signal_score,
                t.confidence,
                t.strategy_id,
                t.snapshot_time
            FROM ts_rn t
            LEFT JOIN basic_rn br
                ON br.code6 = split_part(UPPER(TRIM(CAST(t.code AS VARCHAR))), '.', 1) AND br.rn = 1
            WHERE t.rn = 1
            ORDER BY t.confidence DESC NULLS LAST, t.snapshot_time DESC NULLS LAST
            LIMIT ?
        """
        rows = conn.execute(sql, [lim]).fetchall() or []
        out = []
        for t in rows:
            c6, name, sig, ss, cf, sid, ts = (t + (None,) * 7)[:7]
            out.append(_row(c6, name, str(sig or "signal"), ss, cf, sid, ts))
        return out

    if st in ("deployed", "production"):
        sql = f"""
            WITH basic_rn AS (
                SELECT name,
                    split_part(CAST(code AS VARCHAR), '.', 1) AS code6,
                    ROW_NUMBER() OVER (
                        PARTITION BY split_part(CAST(code AS VARCHAR), '.', 1)
                        ORDER BY CAST(code AS VARCHAR) DESC
                    ) AS rn
                FROM a_stock_basic
            )
            SELECT
                {c6_sp},
                br.name,
                sp.side,
                sp.qty,
                sp.avg_price,
                sp.updated_at
            FROM sim_positions sp
            LEFT JOIN basic_rn br
                ON br.code6 = {c6_sp} AND br.rn = 1
            WHERE sp.qty IS NOT NULL AND ABS(sp.qty) > 1e-9
            ORDER BY sp.updated_at DESC NULLS LAST
            LIMIT ?
        """
        rows = conn.execute(sql, [lim]).fetchall() or []
        out = []
        for t in rows:
            c6, name, side, qty, ap, ts = (t + (None,) * 6)[:6]
            sub = f"{side or ''} · 数量 {qty}" + (f" · 成本 {ap:.4g}" if ap is not None else "")
            out.append(_row(c6, name, sub, qty, None, None, ts))
        return out

    return []

