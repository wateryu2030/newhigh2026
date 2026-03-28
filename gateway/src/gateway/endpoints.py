"""API endpoints: market, strategy, backtest, portfolio, risk, trade, ai-lab."""

import json
import logging
import os
from typing import Any, List, Optional

from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import BaseModel, Field

from .response_utils import json_fail, json_ok

router = APIRouter()
_log = logging.getLogger(__name__)

# 导入系统数据概览端点
try:
    from .endpoints_system_data import get_system_data_overview
    router.get("/system/data-overview")(get_system_data_overview)
except Exception:
    pass

# 导入财报分析端点（endpoints_api 避免与 endpoints.py 命名冲突）
try:
    from .endpoints_api.financial import router as financial_router
    router.include_router(financial_router)
except Exception as e:
    print(f"警告：财报分析端点加载失败：{e}")


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
        if base.startswith("6"):
            add(f"{base}.SH")
            add(f"{base}.XSHG")
        elif base.startswith(("4", "8", "9")) or len(base) == 8:
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
        if six.startswith("6"):
            return f"{six}.SH"
        if six.startswith(("4", "8", "9")):
            return f"{six}.BJ"
        return f"{six}.SZ"
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
                pass
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


@router.get("/market/klines")
def get_klines(
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    limit: int = 100,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Any:
    """K 线：daily_bars → a_stock_daily → 可选 akshare；空数据仍 200，避免误报 503。"""
    empty_payload = {"symbol": symbol, "interval": interval, "limit": 0, "data": []}
    if _is_ashare_symbol(symbol):
        rows: List[Any] = []
        try:
            from data_engine import get_astock_duckdb_available, fetch_klines_from_astock_duckdb

            if get_astock_duckdb_available():
                try:
                    rows = fetch_klines_from_astock_duckdb(
                        symbol,
                        start_date=start_date,
                        end_date=end_date,
                        limit=limit,
                        recent_first=True,
                    )
                except Exception:
                    _log.exception("fetch_klines_from_astock_duckdb failed: %s", symbol)
                    rows = []
        except ImportError:
            _log.warning("data_engine not importable; skip daily_bars klines for %s", symbol)

        if rows:
            data = [
                {
                    "t": r.timestamp.isoformat(),
                    "o": r.open,
                    "h": r.high,
                    "l": r.low,
                    "c": r.close,
                    "close": r.close,
                    "v": r.volume,
                }
                for r in rows
            ]
            return json_ok(
                {
                    "symbol": rows[0].symbol,
                    "interval": "1d",
                    "limit": len(data),
                    "data": data,
                },
                source="duckdb",
            )

        try:
            pipe = _fetch_klines_from_a_stock_daily(symbol, limit=limit)
        except Exception:
            _log.exception("pipeline daily klines failed: %s", symbol)
            pipe = None
        if pipe:
            return json_ok(pipe, source="duckdb_pipeline")

        try:
            ak_payload = _fetch_klines_akshare_daily(symbol, limit=limit)
        except Exception:
            _log.exception("akshare klines failed: %s", symbol)
            ak_payload = None
        if ak_payload:
            return json_ok(ak_payload, source="akshare")

        return json_ok({**empty_payload, "limit": limit}, source="none")

    sym_u = (symbol or "").strip().upper()

    if sym_u.endswith("USDT"):
        bn = _fetch_klines_binance_usdt(sym_u, interval, limit)
        if bn:
            return json_ok(bn, source="binance")

    stq = _stooq_daily_symbol_map(sym_u)
    if stq:
        sq = _fetch_klines_stooq_daily(stq, limit)
        if sq:
            return json_ok(sq, source="stooq")

    return json_ok({**empty_payload, "limit": limit}, source="stub")


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
                pass
    except Exception:
        return None


@router.get("/data/status")
def get_data_status() -> dict:
    """数据状态：合并 astock 表与 pipeline 表口径，供「数据」页与 Dashboard；主数字优先与概览一致。"""
    astock_st: Optional[dict] = None
    try:
        from data_engine import get_astock_duckdb_available, get_duckdb_data_status

        if get_astock_duckdb_available():
            astock_st = get_duckdb_data_status()
    except Exception:
        pass

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
        conn = get_conn(read_only=False)
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
                pass
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
        pass
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
        pass
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
        pass
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
            pass
        conn.execute(
            "UPDATE skill_stats SET call_count = call_count + 1, last_call_time = CURRENT_TIMESTAMP"
        )
        conn.close()
    except Exception:
        pass


@router.get("/skill/ashare/stock-basic")
def skill_ashare_stock_basic(ts_code: Optional[str] = None, name: Optional[str] = None) -> Any:
    """A股股票基本信息（代码、名称、行业、上市日期）。需 TUSHARE_TOKEN。"""
    _record_skill_call()
    return _ashare_skill().get_stock_basic(ts_code=ts_code, name=name)


@router.get("/skill/ashare/daily")
def skill_ashare_daily(
    ts_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Any:
    """A股日线行情（开高低收、成交量、涨跌幅）。需 TUSHARE_TOKEN。"""
    _record_skill_call()
    return _ashare_skill().get_daily_price(
        ts_code=ts_code, start_date=start_date, end_date=end_date
    )


@router.get("/skill/ashare/tech-indicator")
def skill_ashare_tech_indicator(
    ts_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Any:
    """A股技术指标（MA5、MA10、MACD）。需 TUSHARE_TOKEN。"""
    _record_skill_call()
    return _ashare_skill().get_tech_indicator(
        ts_code=ts_code, start_date=start_date, end_date=end_date
    )


@router.get("/skill/ashare/finance-indicator")
def skill_ashare_finance_indicator(ts_code: str, year: Optional[int] = None) -> Any:
    """A股财务指标（PE、PB、ROE、毛利率）。需 TUSHARE_TOKEN。"""
    _record_skill_call()
    return _ashare_skill().get_finance_indicator(ts_code=ts_code, year=year)


@router.get("/skill/ashare/limit-up-down")
def skill_ashare_limit_up_down(trade_date: Optional[str] = None) -> Any:
    """A股涨停/跌停股票列表。需 TUSHARE_TOKEN。"""
    _record_skill_call()
    return _ashare_skill().get_limit_up_down(trade_date=trade_date)


@router.get("/skill/ashare/industry-ranking")
def skill_ashare_industry_ranking(trade_date: Optional[str] = None, top_n: int = 10) -> Any:
    """A股行业涨幅排行。需 TUSHARE_TOKEN。"""
    _record_skill_call()
    return _ashare_skill().get_industry_ranking(trade_date=trade_date, top_n=top_n)


@router.get("/skill/ashare/market-overview")
def skill_ashare_market_overview(trade_date: Optional[str] = None) -> Any:
    """A股市场概览数据。需 TUSHARE_TOKEN。"""
    _record_skill_call()
    return _ashare_skill().get_market_overview(trade_date=trade_date)


@router.get("/skill/stats")
def get_skill_stats() -> dict:
    """Skill 调用统计：总次数、最近调用时间，供系统监控页展示。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return {"call_count": 0, "last_call_time": None}
        conn = get_conn(read_only=False)
        row = conn.execute("SELECT call_count, last_call_time FROM skill_stats LIMIT 1").fetchone()
        conn.close()
        if not row:
            return {"call_count": 0, "last_call_time": None}
        last_ts = row[1]
        if hasattr(last_ts, "isoformat"):
            last_call_time = last_ts.isoformat()
        else:
            last_call_time = str(last_ts) if last_ts else None
        return {"call_count": int(row[0] or 0), "last_call_time": last_call_time}
    except Exception:
        return {"call_count": 0, "last_call_time": None}


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


def _short_ts_for_signal(val: Any) -> str:
    if val is None:
        return "—"
    if hasattr(val, "strftime"):
        try:
            return val.strftime("%m-%d %H:%M")
        except Exception:
            pass
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


@router.get("/market/realtime")
def get_market_realtime(limit: int = 100) -> list:
    """实时行情快照（数据管道 a_stock_realtime），按成交额降序。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return []
        conn = get_conn(read_only=False)
        df = conn.execute(
            "SELECT code, name, latest_price, change_pct, volume, amount, snapshot_time FROM a_stock_realtime ORDER BY amount DESC NULLS LAST LIMIT ?",
            [limit],
        ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")
    except Exception:
        return []


@router.get("/market/limitup")
def get_market_limitup(limit: int = 100) -> list:
    """涨停池：按 code 去重、补名称/现价/涨跌、缩略时间（无原始微秒 timestamp）。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return []
        conn = get_conn(read_only=False)
        lim = max(1, min(int(limit or 100), 500))
        df = conn.execute(
            """
            WITH ranked AS (
                SELECT u.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY u.code
                        ORDER BY u.snapshot_time DESC NULLS LAST, u.limit_up_times DESC NULLS LAST
                    ) AS rn
                FROM a_stock_limitup u
            )
            SELECT
                r.code,
                COALESCE(NULLIF(TRIM(CAST(r.name AS VARCHAR)), ''), b.name, '') AS stock_name,
                COALESCE(rt.latest_price, r.price, ld.c) AS last_price,
                COALESCE(rt.change_pct, r.change_pct) AS change_pct,
                r.limit_up_times,
                r.snapshot_time
            FROM ranked r
            LEFT JOIN a_stock_basic b ON b.code = r.code
            LEFT JOIN a_stock_realtime rt ON rt.code = r.code
            LEFT JOIN (
                SELECT code, close AS c,
                    ROW_NUMBER() OVER (PARTITION BY code ORDER BY date DESC) AS rn
                FROM a_stock_daily
            ) ld ON ld.code = r.code AND ld.rn = 1
            WHERE r.rn = 1
            ORDER BY r.limit_up_times DESC NULLS LAST, r.code
            LIMIT ?
            """,
            [lim],
        ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return []
        out = []
        for _, row in df.iterrows():
            out.append(
                {
                    "code": str(row.get("code") or ""),
                    "stock_name": str(row.get("stock_name") or "").strip(),
                    "last_price": _optional_price(row.get("last_price")),
                    "change_pct": _optional_pct(row.get("change_pct")),
                    "limit_up_times": int(row["limit_up_times"])
                    if row.get("limit_up_times") is not None
                    else None,
                    "updated_at": _short_ts_for_signal(row.get("snapshot_time")),
                }
            )
        return out
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
        pass
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
        pass
    try:
        x = float(val)
        if x != x:  # NaN
            return None
        return round(x, 4)
    except Exception:
        return None


@router.get("/market/longhubang")
def get_market_longhubang(limit: int = 100) -> list:
    """
    龙虎榜明细：过滤无交易日、按 (code,lhb_date) 去重，补名称/现价/涨跌。
    历史任务曾写入 lhb_date 为空的重复行，会在 SQL 层剔除，避免「同代码刷屏 + NaT」的演示感。
    """
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return []
        conn = get_conn(read_only=False)
        lim = max(1, min(int(limit or 100), 500))
        df = conn.execute(
            """
            WITH cleaned AS (
                SELECT l.*
                FROM a_stock_longhubang l
                WHERE l.code IS NOT NULL
                  AND LENGTH(TRIM(CAST(l.code AS VARCHAR))) >= 4
                  AND l.lhb_date IS NOT NULL
            ),
            ranked AS (
                SELECT c.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY c.code, c.lhb_date
                        ORDER BY c.snapshot_time DESC NULLS LAST
                    ) AS rn
                FROM cleaned c
            )
            SELECT
                r.code,
                COALESCE(NULLIF(TRIM(CAST(r.name AS VARCHAR)), ''), b.name, '') AS stock_name,
                r.lhb_date,
                r.net_buy,
                COALESCE(rt.latest_price, ld.c) AS last_price,
                rt.change_pct AS change_pct,
                r.snapshot_time
            FROM ranked r
            LEFT JOIN a_stock_basic b ON b.code = r.code
            LEFT JOIN a_stock_realtime rt ON rt.code = r.code
            LEFT JOIN (
                SELECT code, close AS c,
                    ROW_NUMBER() OVER (PARTITION BY code ORDER BY date DESC) AS rn
                FROM a_stock_daily
            ) ld ON ld.code = r.code AND ld.rn = 1
            WHERE r.rn = 1
            ORDER BY r.lhb_date DESC NULLS LAST, r.net_buy DESC NULLS LAST, r.code
            LIMIT ?
            """,
            [lim],
        ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return []
        out = []
        for _, row in df.iterrows():
            lhb = _safe_lhb_date_str(row.get("lhb_date"))
            if not lhb:
                continue
            nb = _safe_net_buy(row.get("net_buy"))
            out.append(
                {
                    "code": str(row.get("code") or ""),
                    "stock_name": str(row.get("stock_name") or "").strip(),
                    "lhb_date": lhb,
                    "net_buy": nb,
                    "last_price": _optional_price(row.get("last_price")),
                    "change_pct": _optional_pct(row.get("change_pct")),
                    "updated_at": _short_ts_for_signal(row.get("snapshot_time")),
                }
            )
        return out
    except Exception:
        return []


@router.get("/market/fundflow")
def get_market_fundflow(limit: int = 100) -> list:
    """资金流：按 code 取最新一条，补名称/现价/涨跌、缩略时间。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return []
        conn = get_conn(read_only=False)
        lim = max(1, min(int(limit or 100), 500))
        df = conn.execute(
            """
            WITH ranked AS (
                SELECT f.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY f.code
                        ORDER BY f.snapshot_time DESC NULLS LAST, f.snapshot_date DESC NULLS LAST
                    ) AS rn
                FROM a_stock_fundflow f
            )
            SELECT
                r.code,
                COALESCE(NULLIF(TRIM(CAST(r.name AS VARCHAR)), ''), b.name, '') AS stock_name,
                r.main_net_inflow,
                r.snapshot_date,
                r.snapshot_time,
                COALESCE(rt.latest_price, ld.c) AS last_price,
                rt.change_pct AS change_pct
            FROM ranked r
            LEFT JOIN a_stock_basic b ON b.code = r.code
            LEFT JOIN a_stock_realtime rt ON rt.code = r.code
            LEFT JOIN (
                SELECT code, close AS c,
                    ROW_NUMBER() OVER (PARTITION BY code ORDER BY date DESC) AS rn
                FROM a_stock_daily
            ) ld ON ld.code = r.code AND ld.rn = 1
            WHERE r.rn = 1
            ORDER BY r.main_net_inflow DESC NULLS LAST
            LIMIT ?
            """,
            [lim],
        ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return []
        out = []
        for _, row in df.iterrows():
            sd = row.get("snapshot_date")
            m = row.get("main_net_inflow")
            out.append(
                {
                    "code": str(row.get("code") or ""),
                    "stock_name": str(row.get("stock_name") or "").strip(),
                    "main_net_inflow": round(float(m), 4) if m is not None else None,
                    "snapshot_date": str(sd)[:10] if sd is not None else None,
                    "last_price": _optional_price(row.get("last_price")),
                    "change_pct": _optional_pct(row.get("change_pct")),
                    "updated_at": _short_ts_for_signal(row.get("snapshot_time")),
                }
            )
        return out
    except Exception:
        return []


@router.get("/market/emotion")
def get_market_emotion() -> dict:
    """情绪周期状态：优先 market_emotion（每日指标+状态），否则 market_emotion_state。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return {
                "state": "unknown",
                "stage": "—",
                "limit_up_count": 0,
                "score": 0,
                "trade_date": None,
                "max_height": 0,
                "market_volume": 0,
            }
        conn = get_conn(read_only=False)
        row = conn.execute(
            "SELECT trade_date, limitup_count, max_height, market_volume, emotion_state FROM market_emotion ORDER BY trade_date DESC LIMIT 1"
        ).fetchone()
        if row:
            conn.close()
            return {
                "state": row[4] or "—",
                "stage": row[4] or "—",
                "limit_up_count": int(row[1] or 0),
                "score": 50.0,
                "trade_date": str(row[0]) if row[0] else None,
                "max_height": int(row[2] or 0),
                "market_volume": float(row[3] or 0),
            }
        row = conn.execute(
            "SELECT state, stage, limit_up_count, score FROM market_emotion_state ORDER BY snapshot_time DESC LIMIT 1"
        ).fetchone()
        conn.close()
        if row:
            return {
                "state": row[0],
                "stage": row[1],
                "limit_up_count": row[2] or 0,
                "score": float(row[3] or 0),
                "trade_date": None,
                "max_height": 0,
                "market_volume": 0,
            }
    except Exception:
        pass
    return {
        "state": "unknown",
        "stage": "—",
        "limit_up_count": 0,
        "score": 0,
        "trade_date": None,
        "max_height": 0,
        "market_volume": 0,
    }


@router.get("/market/sentiment-7d")
def get_market_sentiment_7d() -> dict:
    """
    全市场 7 维情绪评分（对齐 ClawHub A Stock Monitor 思路，本仓库安全实现）。
    数据：优先 a_stock_realtime，否则 akshare 现货。
    """
    try:
        from data_pipeline.sentiment_7d import get_market_sentiment_7d

        return get_market_sentiment_7d(prefer_db=True)
    except Exception as e:
        return {"error": str(e), "score": 0, "level": "未知", "emoji": "❓"}


@router.get("/strategy/signals")
def get_strategy_signals(limit: int = 50) -> list:
    """
    交易信号：联接股票名称、现价/涨跌幅（实时或最近日线），时间缩略到分。
    返回字段供传统行情表展示，不含原始微秒级 snapshot_time。
    """
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return []
        conn = get_conn(read_only=False)
        lim = max(1, min(int(limit or 50), 500))
        df = conn.execute(
            """
            SELECT
                t.code,
                COALESCE(b.name, '') AS stock_name,
                t.signal,
                t.confidence,
                t.target_price,
                t.stop_loss,
                t.strategy_id,
                t.signal_score,
                COALESCE(rt.latest_price, ld.c) AS last_price,
                rt.change_pct AS change_pct,
                t.snapshot_time
            FROM trade_signals t
            LEFT JOIN a_stock_basic b ON b.code = t.code
            LEFT JOIN a_stock_realtime rt ON rt.code = t.code
            LEFT JOIN (
                SELECT code, close AS c,
                    ROW_NUMBER() OVER (PARTITION BY code ORDER BY date DESC) AS rn
                FROM a_stock_daily
            ) ld ON ld.code = t.code AND ld.rn = 1
            ORDER BY t.snapshot_time DESC
            LIMIT ?
            """,
            [lim],
        ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return []
        out = []
        for _, row in df.iterrows():
            out.append(
                {
                    "code": str(row.get("code") or ""),
                    "stock_name": str(row.get("stock_name") or "").strip(),
                    "signal": str(row.get("signal") or ""),
                    "confidence": float(row["confidence"])
                    if row.get("confidence") is not None
                    else None,
                    "signal_score": float(row["signal_score"])
                    if row.get("signal_score") is not None
                    else None,
                    "target_price": _optional_price(row.get("target_price")),
                    "stop_loss": _optional_price(row.get("stop_loss")),
                    "strategy_id": str(row.get("strategy_id") or ""),
                    "last_price": _optional_price(row.get("last_price")),
                    "change_pct": _optional_pct(row.get("change_pct")),
                    "updated_at": _short_ts_for_signal(row.get("snapshot_time")),
                }
            )
        return out
    except Exception:
        return []


@router.get("/market/hotmoney")
def get_market_hotmoney(limit: int = 50) -> list:
    """游资席位胜率：缩略时间，不含原始微秒 timestamp。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return []
        conn = get_conn(read_only=False)
        df = conn.execute(
            "SELECT seat_name, trade_count, win_rate, avg_return, snapshot_time FROM top_hotmoney_seats ORDER BY win_rate DESC NULLS LAST LIMIT ?",
            [limit],
        ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return []
        out = []
        for _, row in df.iterrows():
            out.append(
                {
                    "seat_name": str(row.get("seat_name") or ""),
                    "trade_count": int(row["trade_count"] or 0)
                    if row.get("trade_count") is not None
                    else 0,
                    "win_rate": float(row["win_rate"]) if row.get("win_rate") is not None else 0.0,
                    "avg_return": float(row["avg_return"]) if row.get("avg_return") is not None else 0.0,
                    "updated_at": _short_ts_for_signal(row.get("snapshot_time")),
                }
            )
        return out
    except Exception:
        return []


@router.get("/market/main-themes")
def get_market_main_themes(limit: int = 10) -> list:
    """主线题材：缩略时间。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return []
        conn = get_conn(read_only=False)
        df = conn.execute(
            "SELECT sector, total_volume, rank, snapshot_time FROM main_themes ORDER BY rank LIMIT ?",
            [limit],
        ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return []
        out = []
        for _, row in df.iterrows():
            out.append(
                {
                    "sector": str(row.get("sector") or ""),
                    "total_volume": float(row["total_volume"])
                    if row.get("total_volume") is not None
                    else 0.0,
                    "rank": int(row["rank"] or 0) if row.get("rank") is not None else 0,
                    "updated_at": _short_ts_for_signal(row.get("snapshot_time")),
                }
            )
        return out
    except Exception:
        return []


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


@router.get("/market/sniper-candidates")
def get_sniper_candidates(limit: int = 50) -> list:
    """狙击候选：按 code 去重保留最高分；补名称/现价/涨跌（实时→涨停池→日K两日）；题材用 sector/industry 回填「未分类」。"""
    try:
        from data_pipeline.storage.duckdb_manager import ensure_tables, get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return []
        conn = get_conn(read_only=False)
        try:
            ensure_tables(conn)
        except Exception:
            _log.exception("ensure_tables before sniper_candidates")
        lim = max(1, min(int(limit or 50), 500))
        try:
            res = conn.execute(
                """
                WITH ranked AS (
                    SELECT s.*,
                        ROW_NUMBER() OVER (
                            PARTITION BY s.code
                            ORDER BY s.sniper_score DESC NULLS LAST, s.snapshot_time DESC NULLS LAST
                        ) AS rn
                    FROM sniper_candidates s
                ),
                daily_rn AS (
                    SELECT
                        split_part(CAST(code AS VARCHAR), '.', 1) AS code6,
                        date,
                        CAST(close AS DOUBLE) AS close,
                        ROW_NUMBER() OVER (
                            PARTITION BY split_part(CAST(code AS VARCHAR), '.', 1)
                            ORDER BY date DESC
                        ) AS rn
                    FROM a_stock_daily
                ),
                d1 AS (SELECT code6, close AS c1 FROM daily_rn WHERE rn = 1),
                d2 AS (SELECT code6, close AS c2 FROM daily_rn WHERE rn = 2),
                basic_rn AS (
                    SELECT
                        name,
                        sector,
                        industry,
                        split_part(CAST(code AS VARCHAR), '.', 1) AS code6,
                        ROW_NUMBER() OVER (
                            PARTITION BY split_part(CAST(code AS VARCHAR), '.', 1)
                            ORDER BY CAST(code AS VARCHAR) DESC
                        ) AS rn
                    FROM a_stock_basic
                ),
                limup_rn AS (
                    SELECT
                        split_part(CAST(code AS VARCHAR), '.', 1) AS code6,
                        change_pct,
                        snapshot_time,
                        ROW_NUMBER() OVER (
                            PARTITION BY split_part(CAST(code AS VARCHAR), '.', 1)
                            ORDER BY snapshot_time DESC NULLS LAST
                        ) AS rn
                    FROM a_stock_limitup
                ),
                rt_rn AS (
                    SELECT
                        split_part(CAST(code AS VARCHAR), '.', 1) AS code6,
                        latest_price,
                        change_pct,
                        ROW_NUMBER() OVER (
                            PARTITION BY split_part(CAST(code AS VARCHAR), '.', 1)
                            ORDER BY snapshot_time DESC NULLS LAST
                        ) AS rn
                    FROM a_stock_realtime
                )
                SELECT
                    r.code,
                    COALESCE(b.name, '') AS stock_name,
                    CASE
                        WHEN r.theme IS NULL OR TRIM(CAST(r.theme AS VARCHAR)) = ''
                            OR TRIM(CAST(r.theme AS VARCHAR)) = '未分类'
                        THEN COALESCE(
                            NULLIF(TRIM(CAST(b.sector AS VARCHAR)), ''),
                            NULLIF(TRIM(CAST(b.industry AS VARCHAR)), ''),
                            '—'
                        )
                        ELSE TRIM(CAST(r.theme AS VARCHAR))
                    END AS theme,
                    r.sniper_score,
                    r.confidence,
                    COALESCE(rt.latest_price, d1.c1) AS last_price,
                    COALESCE(
                        rt.change_pct,
                        lu.change_pct,
                        CASE
                            WHEN d2.c2 IS NOT NULL AND d2.c2 > 0
                            THEN (d1.c1 - d2.c2) / d2.c2 * 100.0
                            ELSE NULL
                        END
                    ) AS change_pct,
                    CASE
                        WHEN lu.snapshot_time IS NOT NULL
                            AND (r.snapshot_time IS NULL OR lu.snapshot_time > r.snapshot_time)
                        THEN lu.snapshot_time
                        ELSE r.snapshot_time
                    END AS snapshot_time
                FROM ranked r
                LEFT JOIN basic_rn b
                    ON b.code6 = split_part(CAST(r.code AS VARCHAR), '.', 1) AND b.rn = 1
                LEFT JOIN rt_rn rt
                    ON rt.code6 = split_part(CAST(r.code AS VARCHAR), '.', 1) AND rt.rn = 1
                LEFT JOIN d1 ON d1.code6 = split_part(CAST(r.code AS VARCHAR), '.', 1)
                LEFT JOIN d2 ON d2.code6 = split_part(CAST(r.code AS VARCHAR), '.', 1)
                LEFT JOIN limup_rn lu
                    ON lu.code6 = split_part(CAST(r.code AS VARCHAR), '.', 1) AND lu.rn = 1
                WHERE r.rn = 1
                ORDER BY r.sniper_score DESC NULLS LAST, r.code
                LIMIT ?
                """,
                [lim],
            )
            rows = res.fetchall() or []
            out: list = []
            for row in rows:
                (
                    code,
                    stock_name,
                    theme,
                    ss,
                    cf,
                    last_price,
                    change_pct,
                    snap,
                ) = (row + (None,) * 8)[:8]
                out.append(
                    {
                        "code": str(code or ""),
                        "stock_name": str(stock_name or "").strip(),
                        "theme": str(theme or "").strip() or "—",
                        "sniper_score": float(ss) if ss is not None else None,
                        "confidence": float(cf) if cf is not None else None,
                        "last_price": _optional_price(last_price),
                        "change_pct": _optional_pct(change_pct),
                        "updated_at": _short_ts_for_signal(snap),
                    }
                )
            return out
        except Exception:
            _log.exception("get_sniper_candidates full query failed")
            try:
                return _sniper_candidates_minimal(conn, lim)
            except Exception:
                _log.exception("get_sniper_candidates minimal failed")
                return []
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception:
        return []


def _status_to_state(s: str) -> str:
    """将 system_status 短串转为 running/error/idle。"""
    if not s or s == "not_run":
        return "idle"
    if s.startswith("error:"):
        return "error"
    return "running"


@router.get("/ai/decision")
def get_ai_decision() -> dict:
    """
    AI 决策解释：聚合情绪、交易信号、游资、主线，返回当前信号与理由，供前端「AI 决策解释」区块展示。
    返回：signal (BUY/SELL/HOLD), reason (文案), factors (标签列表)。
    """
    signal = "HOLD"
    reason_parts: List[str] = []
    factors: List[str] = []
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return {"signal": signal, "reason": "暂无数据", "factors": []}
        conn = get_conn(read_only=False)
        try:
            row = conn.execute(
                "SELECT emotion_state, limitup_count FROM market_emotion ORDER BY trade_date DESC LIMIT 1"
            ).fetchone()
            if row:
                stage = str(row[0] or "—")
                limitup = int(row[1] or 0)
                reason_parts.append(f"情绪阶段: {stage}; 涨停数 {limitup}")
                factors.append(f"emotion_{stage[:2]}" if stage != "—" else "emotion")
            df_sig = conn.execute(
                "SELECT signal FROM trade_signals ORDER BY snapshot_time DESC LIMIT 20"
            ).fetchdf()
            if df_sig is not None and not df_sig.empty:
                sig_str = str(df_sig.iloc[0].get("signal", "")).upper()
                if "BUY" in sig_str or "LONG" in sig_str or "买" in sig_str or "多" in sig_str:
                    signal = "BUY"
                elif "SELL" in sig_str or "SHORT" in sig_str or "卖" in sig_str or "空" in sig_str:
                    signal = "SELL"
                n = len(df_sig)
                reason_parts.append(f"交易信号 {n} 条，最新: {sig_str or '—'}")
                factors.append("trade_signals")
            hot = conn.execute("SELECT COUNT(*) FROM top_hotmoney_seats").fetchone()
            hot_n = int(hot[0]) if hot and hot[0] is not None else 0
            if hot_n > 0:
                reason_parts.append(f"游资席位 {hot_n} 个")
                factors.append("hotmoney")
            th = conn.execute("SELECT COUNT(*) FROM main_themes").fetchone()
            th_n = int(th[0]) if th and th[0] is not None else 0
            if th_n > 0:
                reason_parts.append(f"主线题材 {th_n} 个")
                factors.append("themes")
        finally:
            conn.close()
        reason = (
            "；".join(reason_parts)
            if reason_parts
            else "暂无情绪与信号数据，建议先运行 system_core。"
        )
    except Exception as e:
        reason = str(e)
    return {"signal": signal, "reason": reason, "factors": factors}


@router.get("/system/status")
def get_system_status(limit: int = 10):
    """
    统一运行核心状态（system_status 表），由 system_core 写入。
    返回：summary（data_pipeline, scanner, ai_models, strategy_engine, last_update）+ history 列表。
    """
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return {
                "data_pipeline": "idle",
                "scanner": "idle",
                "ai_models": "idle",
                "strategy_engine": "idle",
                "last_update": None,
                "history": [],
            }
        conn = get_conn(read_only=False)
        try:
            df = conn.execute(
                """SELECT data_status, scanner_status, ai_status, strategy_status, snapshot_time,
                          evolution_task_id, evolution_status, evolution_result, skill_call_count, skill_last_call_time
                   FROM system_status ORDER BY snapshot_time DESC LIMIT ?""",
                [limit],
            ).fetchdf()
        except Exception:
            df = conn.execute(
                "SELECT data_status, scanner_status, ai_status, strategy_status, snapshot_time FROM system_status ORDER BY snapshot_time DESC LIMIT ?",
                [limit],
            ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return {
                "data_pipeline": "idle",
                "scanner": "idle",
                "ai_models": "idle",
                "strategy_engine": "idle",
                "last_update": None,
                "history": [],
                "evolution_task_id": None,
                "evolution_status": None,
                "skill_call_count": 0,
                "skill_last_call_time": None,
            }
        row = df.iloc[0]
        last_ts = row.get("snapshot_time")
        if hasattr(last_ts, "isoformat"):
            last_update = last_ts.isoformat()
        else:
            last_update = str(last_ts) if last_ts else None
        summary = {
            "data_pipeline": _status_to_state(str(row.get("data_status", ""))),
            "scanner": _status_to_state(str(row.get("scanner_status", ""))),
            "ai_models": _status_to_state(str(row.get("ai_status", ""))),
            "strategy_engine": _status_to_state(str(row.get("strategy_status", ""))),
            "last_update": last_update,
        }
        if "evolution_task_id" in row:
            summary["evolution_task_id"] = row.get("evolution_task_id")
            summary["evolution_status"] = row.get("evolution_status")
        if "skill_call_count" in row:
            summary["skill_call_count"] = int(row.get("skill_call_count") or 0)
            st = row.get("skill_last_call_time")
            summary["skill_last_call_time"] = (
                st.isoformat() if hasattr(st, "isoformat") else (str(st) if st else None)
            )
        history = df.to_dict(orient="records")
        for h in history:
            if "snapshot_time" in h and hasattr(h["snapshot_time"], "isoformat"):
                h["snapshot_time"] = h["snapshot_time"].isoformat()
        return {**summary, "history": history}
    except Exception:
        return {
            "data_pipeline": "idle",
            "scanner": "idle",
            "ai_models": "idle",
            "strategy_engine": "idle",
            "last_update": None,
            "history": [],
            "evolution_task_id": None,
            "evolution_status": None,
            "skill_call_count": 0,
            "skill_last_call_time": None,
        }


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
        out = []
        cols = [str(c) for c in df.columns.tolist()]
        title_col = next((c for c in ["新闻标题", "title"] if c in cols), cols[0] if cols else None)
        content_col = next((c for c in ["新闻内容", "content"] if c in cols), None)
        time_col = next((c for c in ["发布时间", "publish_time"] if c in cols), None)
        url_col = next((c for c in ["新闻链接", "链接", "url", "link"] if c in cols), None)
        source_col = next((c for c in ["文章来源", "source"] if c in cols), None)
        for _, row in df.head(limit).iterrows():
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


@router.get("/news")
def get_news(symbol: Optional[str] = None, limit: int = 100) -> dict:
    """新闻列表：优先 DuckDB news_items；为空时从 akshare 东方财富补充。"""
    items: List[dict] = []
    source: Optional[str] = None
    try:
        from data_engine import get_astock_duckdb_available, get_news_from_astock_duckdb

        if get_astock_duckdb_available():
            items = get_news_from_astock_duckdb(symbol=symbol, limit=limit)
            if items:
                source = "duckdb"
    except Exception:
        pass
    if not items:
        items = _news_fallback_akshare(symbol=symbol, limit=min(limit, 50))
        if items:
            source = "akshare"
    sentiment = _news_sentiment_summary(items)
    return {"news": items, "source": source, "sentiment": sentiment}


def _repo_root_from_gateway() -> str:
    """gateway/src/gateway/endpoints.py → 仓库根。"""
    return os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
    )


def _policy_news_sqlite_path() -> Optional[str]:
    """policy-news 采集库；可用环境变量 POLICY_NEWS_DB_PATH 覆盖。"""
    custom = (os.environ.get("POLICY_NEWS_DB_PATH") or "").strip()
    if custom:
        return custom if os.path.isfile(custom) else None
    default = os.path.join(
        _repo_root_from_gateway(),
        "integrations",
        "hongshan",
        "policy-news",
        "sqlite",
        "news.db",
    )
    return default if os.path.isfile(default) else None


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


@router.get("/news/collector")
def get_news_collector(
    category: Optional[str] = None,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    """
    政策采集入库（SQLite）：与 OpenClaw/policy-news 脚本同一数据源，供主站 /news「政策采集」Tab。
    不依赖第三方 Awesome Finance Skills；库不存在时返回空列表。
    """
    db_path = _policy_news_sqlite_path()
    if not db_path:
        return {
            "news": [],
            "source": None,
            "sentiment": {"count": 0, "avg_score": None, "positive_ratio": None},
            "detail": "policy_news_db_not_found",
        }
    import sqlite3

    items: List[dict] = []
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            q = (
                "SELECT title, source, category, content, url, publish_date, sentiment, domains "
                "FROM news WHERE (? IS NULL OR category = ?) "
                "ORDER BY COALESCE(publish_date, '') DESC, created_at DESC LIMIT ? OFFSET ?"
            )
            cur = conn.execute(q, (category, category, limit, offset))
            for row in cur.fetchall():
                sc = row["sentiment"]
                items.append(
                    {
                        "title": row["title"] or "",
                        "content": (row["content"] or "")[:2000],
                        "url": row["url"] or None,
                        "source": row["source"] or "",
                        "publish_time": (row["publish_date"] or "")[:19],
                        "tag": row["category"] or "",
                        "keyword": (row["domains"] or "")[:200] if row["domains"] else None,
                        "sentiment_score": float(sc) if sc is not None else None,
                        "sentiment_label": _policy_sentiment_label(sc),
                    }
                )
        finally:
            conn.close()
    except Exception as e:
        _log.warning("policy news sqlite read failed: %s", e)
        return {
            "news": [],
            "source": None,
            "sentiment": None,
            "detail": "policy_news_read_error",
        }
    sentiment = _news_sentiment_summary(items)
    return {"news": items, "source": "policy_sqlite", "sentiment": sentiment}


@router.get("/news/coverage")
def get_news_coverage() -> dict:
    """
    新闻检索能力分层说明（借鉴 AI-Search-Hub 多平台原生搜索理念，见 docs/NEWS_SEARCH_AI_SEARCH_HUB.md）。
    不含外部调用，供前端/Agent 展示扩展路径。
    """
    return {
        "tier1_in_repo": {
            "description": "站内默认：DuckDB news_items + akshare 东方财富",
            "api": "GET /api/news",
            "summary_api": "POST /api/research/news-summary",
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
        pass

    if len(lines) < 6:
        try:
            extra = _news_fallback_akshare(None, 15)
            for n in extra[:10]:
                t = (n.get("title") or "").strip()
                if t and len(t) > 8:
                    lines.append({"type": "news", "text": t[:60], "code": None})
        except Exception:
            pass

    if not lines:
        lines = [
            {"type": "tip", "text": "热点加载中，请稍后刷新；确保本机可访问东财数据", "code": None}
        ]

    parts = [x["text"] for x in lines[:20]]
    banner = prefix + " · ".join(parts)
    return {
        "lines": lines[:20],
        "banner": banner[:1200],
        "updated_at": dt.datetime.now().isoformat(timespec="seconds"),
    }


@router.get("/news/hot-ticker")
def get_news_hot_ticker() -> dict:
    """顶部滚动热点：东方财富热榜 + 财经快讯标题。"""
    return _fetch_hot_ticker_payload()


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


def _fetch_news_for_research(symbol: Optional[str], limit: int) -> tuple[List[dict], Optional[str]]:
    """与 GET /news 一致的新闻拉取，供投研摘要复用。"""
    items: List[dict] = []
    source: Optional[str] = None
    try:
        from data_engine import get_astock_duckdb_available, get_news_from_astock_duckdb

        if get_astock_duckdb_available():
            items = get_news_from_astock_duckdb(symbol=symbol, limit=limit)
            if items:
                source = "duckdb"
    except Exception:
        pass
    if not items:
        items = _news_fallback_akshare(symbol=symbol, limit=min(limit, 50))
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


def _save_backtest_to_strategy_market(strategy_id: str, name: str, result: dict) -> bool:
    """将回测结果写入 strategy_market 表。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, ensure_tables

        conn = get_conn(read_only=False)
        ensure_tables(conn)
        tr = result.get("total_return")
        return_pct = float(tr * 100) if tr is not None else None
        sharpe = result.get("sharpe_ratio")
        max_dd = result.get("max_drawdown")
        conn.execute(
            """
            INSERT INTO strategy_market (strategy_id, name, return_pct, sharpe_ratio, max_drawdown, status, updated_at)
            VALUES (?, ?, ?, ?, ?, 'active', CURRENT_TIMESTAMP)
            ON CONFLICT (strategy_id) DO UPDATE SET
            name=EXCLUDED.name, return_pct=EXCLUDED.return_pct, sharpe_ratio=EXCLUDED.sharpe_ratio,
            max_drawdown=EXCLUDED.max_drawdown, status=EXCLUDED.status, updated_at=CURRENT_TIMESTAMP
        """,
            [
                strategy_id,
                name or strategy_id.replace("_", " ").title(),
                return_pct,
                sharpe,
                max_dd,
            ],
        )
        conn.close()
        return True
    except Exception:
        return False


@router.get("/strategies/market")
def get_strategies_market(limit: int = 50) -> dict:
    """
    策略市场列表：id、名称、收益、Sharpe、回撤、状态。
    优先从 strategy_market 表读（回测结果写入）；再补 trade_signals 中 distinct strategy_id；最后补 stub。
    """
    items: List[dict] = []
    seen: set = set()
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if os.path.isfile(get_db_path()):
            conn = get_conn(read_only=False)
            try:
                df = conn.execute(
                    """SELECT strategy_id, name, return_pct, sharpe_ratio, max_drawdown, status
                       FROM strategy_market ORDER BY updated_at DESC LIMIT ?""",
                    [limit],
                ).fetchdf()
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        sid = str(row.get("strategy_id") or "")
                        if not sid:
                            continue
                        seen.add(sid)
                        items.append(
                            {
                                "id": sid,
                                "name": str(row.get("name") or sid.replace("_", " ").title()),
                                "return_pct": (
                                    float(row["return_pct"])
                                    if row.get("return_pct") is not None
                                    else None
                                ),
                                "sharpe_ratio": (
                                    float(row["sharpe_ratio"])
                                    if row.get("sharpe_ratio") is not None
                                    else None
                                ),
                                "max_drawdown": (
                                    float(row["max_drawdown"])
                                    if row.get("max_drawdown") is not None
                                    else None
                                ),
                                "status": str(row.get("status") or "active"),
                            }
                        )
                df2 = conn.execute(
                    """SELECT DISTINCT COALESCE(strategy_id, 'ai_fusion') AS strategy_id
                       FROM trade_signals ORDER BY strategy_id LIMIT ?""",
                    [limit],
                ).fetchdf()
                if df2 is not None and not df2.empty:
                    for sid in df2["strategy_id"].astype(str).tolist():
                        if not sid or sid == "None":
                            sid = "ai_fusion"
                        if sid in seen:
                            continue
                        seen.add(sid)
                        items.append(
                            {
                                "id": sid,
                                "name": sid.replace("_", " ").title(),
                                "return_pct": None,
                                "sharpe_ratio": None,
                                "max_drawdown": None,
                                "status": "active",
                            }
                        )
            finally:
                conn.close()
    except Exception:
        pass
    stub = [
        {
            "id": "trend_following",
            "name": "Trend Following",
            "return_pct": 12.5,
            "sharpe_ratio": 2.1,
            "max_drawdown": 5.0,
            "status": "live",
        },
        {
            "id": "mean_reversion",
            "name": "Mean Reversion",
            "return_pct": 8.2,
            "sharpe_ratio": 1.8,
            "max_drawdown": 6.0,
            "status": "test",
        },
        {
            "id": "breakout",
            "name": "Breakout",
            "return_pct": 15.0,
            "sharpe_ratio": 1.9,
            "max_drawdown": 5.5,
            "status": "live",
        },
    ]
    for s in stub:
        if s["id"] not in seen:
            items.append(s)
    return {"items": items}


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


@router.post("/backtest/run")
def run_backtest_api(
    symbol: str = "000001.SZ",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    signal_source: str = "trade_signals",
    init_cash: float = 10000.0,
    fees: float = 0.001,
    slippage: float = 0.0,
    symbols: Optional[str] = None,
    strategy_id: Optional[str] = None,
    strategy_name: Optional[str] = None,
) -> dict:
    """
    回测：从 quant_system.duckdb 读日 K 与信号，返回资金曲线与风险指标。
    若提供 strategy_id（及可选 strategy_name），回测成功后写入 strategy_market 表，供策略市场页展示。
    """
    try:
        out = _run_backtest_internal(
            symbol,
            start_date,
            end_date,
            signal_source=signal_source,
            init_cash=init_cash,
            fees=fees,
            slippage=slippage,
            symbols=symbols,
        )
        if strategy_id and not out.get("error"):
            _save_backtest_to_strategy_market(strategy_id, strategy_name or strategy_id, out)
        return out
    except Exception as e:
        return {
            "symbol": symbol,
            "equity_curve": [],
            "sharpe_ratio": None,
            "max_drawdown": None,
            "total_return": None,
            "win_rate_pct": None,
            "profit_factor": None,
            "total_profit": None,
            "trade_count": None,
            "error": str(e),
        }


@router.post("/backtest/portfolio")
def run_backtest_portfolio_api(
    strategy_ids: List[str] = Body(
        ..., description="Strategy IDs from strategy_market / trade_signals"
    ),
    weights: Optional[List[float]] = Body(None),
    start_date: Optional[str] = Body(None),
    end_date: Optional[str] = Body(None),
    init_cash: float = Body(10000.0),
    fees: float = Body(0.001),
    slippage: float = Body(0.0),
) -> dict:
    """
    多策略组合回测：按 strategy_ids 与可选 weights 分配资金，各策略独立回测后按权重合并资金曲线与指标。
    """
    from datetime import datetime, timedelta
    import os
    import sys

    _root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    for _d in ["backtest-engine/src", "data-pipeline/src", "core/src"]:
        _p = os.path.join(_root, _d)
        if os.path.isdir(_p) and _p not in sys.path:
            sys.path.insert(0, _p)
    try:
        from backtest_engine.portfolio_backtest import run_portfolio_backtest

        end = end_date or datetime.now().strftime("%Y-%m-%d")
        start = start_date or (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        out = run_portfolio_backtest(
            strategy_ids=strategy_ids,
            start_date=start,
            end_date=end,
            weights=weights,
            init_cash=init_cash,
            fees=fees,
            slippage=slippage,
        )
        return out
    except Exception as e:
        return {
            "equity_curve": [],
            "sharpe_ratio": None,
            "max_drawdown": None,
            "total_return": None,
            "per_strategy": [],
            "error": str(e),
        }


@router.get("/backtest/result")
def get_backtest_result(
    symbol: str = "000001.SZ",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    signal_source: str = "trade_signals",
    fees: float = 0.001,
    slippage: float = 0.0,
    symbols: Optional[str] = None,
) -> dict:
    """GET 回测结果：便于前端直接拉取资金曲线与指标，参数同 POST /backtest/run。"""
    try:
        return _run_backtest_internal(
            symbol,
            start_date,
            end_date,
            signal_source=signal_source,
            fees=fees,
            slippage=slippage,
            symbols=symbols,
        )
    except Exception as e:
        return {
            "symbol": symbol,
            "equity_curve": [],
            "sharpe_ratio": None,
            "max_drawdown": None,
            "total_return": None,
            "win_rate_pct": None,
            "profit_factor": None,
            "total_profit": None,
            "trade_count": None,
            "error": str(e),
        }


@router.get("/portfolio/weights")
def get_portfolio_weights() -> dict:
    """Current portfolio weights (stub)."""
    return {"weights": {}, "capital": 0}


@router.get("/risk/status")
def risk_status() -> dict:
    """Risk checks status (stub)."""
    return {
        "drawdown_ok": True,
        "exposure_ok": True,
        "volatility_ok": True,
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


@router.get("/risk/rules")
def get_risk_rules() -> dict:
    """风控规则列表（从 risk_rules 表读取）。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return {"rules": []}
        conn = get_conn(read_only=False)
        load_rules, _, _ = _risk_engine_module()
        rules = load_rules(conn)
        conn.close()
        return {"rules": rules}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/risk/rules")
def post_risk_rule(
    rule_type: str,
    value: float,
    enabled: bool = True,
    id: Optional[int] = None,
) -> dict:
    """新增或更新一条风控规则。rule_type: single_position_pct_max | max_drawdown_pct | max_exposure_pct。"""
    try:
        _, _, save_rule = _risk_engine_module()
        ok = save_rule(rule_type=rule_type, value=value, enabled=enabled, rule_id=id)
        return {"ok": ok}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/risk/check")
def post_risk_check(body: dict = Body(default={})) -> dict:
    """风控检查：body 含 positions（列表）、total_assets（float）、可选 equity_curve（列表），返回 pass 与 violations。"""
    try:
        _, evaluate, _ = _risk_engine_module()
        body = body or {}
        positions = body.get("positions") or []
        total_assets = float(body.get("total_assets") or 0)
        equity_curve = body.get("equity_curve")
        out = evaluate(positions=positions, total_assets=total_assets, equity_curve=equity_curve)
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 审计 ---


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
                pass
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
        _log.exception("get_data_quality failed")
        return json_fail(str(e)[:200], status_code=503, source="error")


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


@router.get("/execution/mode")
def get_execution_mode() -> dict:
    """当前执行模式：simulated（模拟盘）或 live（实盘）。"""
    try:
        execution_mode, _, _ = _execution_broker_module()
        return {"mode": execution_mode()}
    except Exception as e:
        return {"mode": "simulated", "error": str(e)}


@router.post("/execution/mode")
def post_execution_mode(mode: str = "simulated") -> dict:
    """设置执行模式（仅当前进程/请求生效；持久化需配置 EXECUTION_MODE 环境变量）。"""
    try:
        _, set_execution_mode, _ = _execution_broker_module()
        set_execution_mode(mode)
        return {"ok": True, "mode": mode}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 模拟盘 Simulated Execution (execution-engine) ---


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


@router.post("/simulated/step")
def post_simulated_step(
    buy_threshold: float = 0.7,
    sell_threshold: float = 0.3,
    lot_size: int = 100,
    max_buys: int = 10,
    max_sells: int = 10,
) -> dict:
    """
    执行一步模拟盘：根据 trade_signals 生成模拟订单，更新持仓与资金快照。
    返回本步 orders_created、cash、equity、total_assets。
    """
    try:
        step_simulated, _, _, _ = _simulated_module()
        return step_simulated(
            buy_threshold=buy_threshold,
            sell_threshold=sell_threshold,
            lot_size=lot_size,
            max_buys=max_buys,
            max_sells=max_sells,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/simulated/positions")
def get_simulated_positions(limit: int = 100) -> dict:
    """模拟盘当前持仓列表。"""
    try:
        _, sim_get_positions, _, _ = _simulated_module()
        positions = sim_get_positions(limit=limit)
        return {"positions": positions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/simulated/orders")
def get_simulated_orders(limit: int = 100, status: Optional[str] = None) -> dict:
    """模拟盘订单列表；status 可选 pending/filled。"""
    try:
        _, _, sim_get_orders, _ = _simulated_module()
        orders = sim_get_orders(limit=limit, status=status)
        return {"orders": orders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/simulated/account_snapshots")
def get_simulated_account_snapshots(limit: int = 100) -> dict:
    """模拟盘资金快照历史。"""
    try:
        _, _, _, sim_get_account_snapshots = _simulated_module()
        snapshots = sim_get_account_snapshots(limit=limit)
        return {"snapshots": snapshots}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/execution/equity_curve")
def get_execution_equity_curve(limit: int = 200) -> dict:
    """执行层资金曲线：从 sim_account_snapshots 聚合，供前端资金曲线图。"""
    try:
        _, _, _, sim_get_account_snapshots = _simulated_module()
        snapshots = sim_get_account_snapshots(limit=limit)
        # 按时间正序返回 [{ date, value }, ...]
        curve = []
        for s in reversed(snapshots):
            ts = s.get("snapshot_time")
            v = s.get("total_assets")
            if ts is not None and v is not None:
                dt = ts.strftime("%Y-%m-%d %H:%M") if hasattr(ts, "strftime") else str(ts)[:16]
                curve.append({"date": dt, "value": float(v)})
        return {"equity_curve": curve}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions")
def get_positions() -> dict:
    """Current positions (stub)."""
    return {"positions": []}


@router.post("/ai/generate-strategies")
def generate_strategies(count: int = 5) -> dict:
    """Generate strategies via AI (stub)."""
    return {"generated": [], "count": count}


# --- Frontend API (Dashboard, Evolution, Trades) ---


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
        conn = get_conn(read_only=False)
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
            conn.close()
    except Exception:
        pass
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
        # 选一只有日线数据的标的（首只可能无 bar，如 60081.SH）
        rows = []
        sym = None
        for s in stocks[:50]:
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


@router.get("/dashboard")
def get_dashboard() -> dict:
    """Dashboard：有 DuckDB 时用日线推导权益曲线与日涨跌；夏普/回撤由曲线估算；策略榜仅 DB 真实记录。"""
    out = _dashboard_from_duckdb()
    if out is not None:
        return out
    stub_equity = [10e6, 10.2e6, 10.5e6, 11e6, 11.8e6, 12.34e6]
    sh, md = _metrics_from_equity_curve(stub_equity)
    return {
        "total_equity": 12_340_000,
        "daily_return_pct": 2.34,
        "sharpe_ratio": sh if sh is not None else None,
        "max_drawdown_pct": md if md is not None else None,
        "equity_curve": stub_equity,
        "top_strategies": [],
        "ai_generated_today": None,
        "strategies_alive": None,
        "strategies_live": None,
        "equity_proxy_symbol": None,
        "dashboard_notes": ["no_duckdb_or_no_bars_using_static_demo_equity_curve"],
    }


@router.get("/evolution")
def get_evolution() -> dict:
    """Evolution: generation, best strategy, tree (stub)."""
    return {
        "current_generation": 3,
        "best_strategy": {"id": "STR_0034", "sharpe": 2.6, "return_pct": 41},
        "generations": [{"gen": 1}, {"gen": 2}, {"gen": 3}],
    }


@router.post("/evolution/run")
def post_evolution_run(
    population_limit: int = 10,
    symbol: str = "000001.SZ",
) -> dict:
    """执行一轮 OpenClaw 进化：从策略市场加载种群，遗传+回测评估，优秀个体写回 strategy_market。"""
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

        return run_evolution_cycle(population_limit=population_limit, symbol=symbol)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        pass


@router.post("/evolution/trigger")
def post_evolution_trigger(
    task_type: str = "strategy_generation",
    population_limit: int = 10,
    symbol: str = "000001.SZ",
) -> dict:
    """触发 OpenClaw 进化任务（异步），返回 task_id；前端可轮询 GET /api/evolution/status/{task_id}。"""
    import uuid
    import threading

    task_id = str(uuid.uuid4())
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if os.path.isfile(get_db_path()):
            conn = get_conn(read_only=False)
            conn.execute(
                "INSERT INTO evolution_tasks (task_id, status, result) VALUES (?, ?, ?)",
                [task_id, "pending", None],
            )
            conn.close()
    except Exception:
        pass
    t = threading.Thread(
        target=_run_evolution_background,
        args=(task_id, population_limit, symbol),
        daemon=True,
    )
    t.start()
    return {"task_id": task_id, "status": "pending"}


@router.get("/evolution/status/{task_id}")
def get_evolution_status(task_id: str) -> dict:
    """查询 OpenClaw 进化任务状态与结果。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os
        import json

        if not os.path.isfile(get_db_path()):
            return {"task_id": task_id, "status": "PENDING", "result": None}
        conn = get_conn(read_only=False)
        row = conn.execute(
            "SELECT status, result FROM evolution_tasks WHERE task_id = ?",
            [task_id],
        ).fetchone()
        conn.close()
        if not row:
            return {"task_id": task_id, "status": "PENDING", "result": None}
        status, res_str = row[0], row[1]
        result = None
        if res_str:
            try:
                result = json.loads(res_str)
            except Exception:
                result = res_str
        return {"task_id": task_id, "status": status.upper(), "result": result}
    except Exception:
        return {"task_id": task_id, "status": "PENDING", "result": None}


@router.get("/evolution/tasks")
def get_evolution_tasks(limit: int = 5) -> dict:
    """最近若干次进化任务列表，供系统监控页展示。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return {"tasks": []}
        conn = get_conn(read_only=False)
        df = conn.execute(
            "SELECT task_id, status, result, created_at FROM evolution_tasks ORDER BY created_at DESC LIMIT ?",
            [limit],
        ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return {"tasks": []}
        tasks = []
        for _, row in df.iterrows():
            tasks.append(
                {
                    "id": str(row.get("task_id", "")),
                    "status": str(row.get("status", "pending")),
                    "result": row.get("result"),
                    "created_at": (
                        row.get("created_at").isoformat()
                        if hasattr(row.get("created_at"), "isoformat")
                        else str(row.get("created_at")) if row.get("created_at") else None
                    ),
                }
            )
        return {"tasks": tasks}
    except Exception:
        return {"tasks": []}


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


@router.get("/alpha-lab/drill")
def get_alpha_lab_drill(stage: str = "generated", limit: int = 100) -> dict:
    """Alpha 工坊下钻：按阶段返回标的列表（与 /alpha-lab 同一 DuckDB 口径）。"""
    try:
        from data_pipeline.storage.duckdb_manager import ensure_tables, get_conn, get_db_path
        import os

        note = _alpha_lab_binding_note()
        if not os.path.isfile(get_db_path()):
            return {"stage": stage, "items": [], "total": 0, "source": "stub_no_db", "binding_note": note}
        conn = get_conn(read_only=False)
        try:
            ensure_tables(conn)
            items = _alpha_lab_drill_rows(conn, stage, limit)
            return {
                "stage": stage,
                "items": items,
                "total": len(items),
                "source": "duckdb",
                "binding_note": note,
            }
        finally:
            conn.close()
    except Exception:
        _log.exception("get_alpha_lab_drill")
        return {
            "stage": stage,
            "items": [],
            "total": 0,
            "source": "error",
            "binding_note": _alpha_lab_binding_note(),
        }


@router.get("/alpha-lab")
def get_alpha_lab() -> dict:
    """Alpha 工坊漏斗：优先 DuckDB 代理指标；无库或失败时返回 0。"""
    note = _alpha_lab_binding_note()
    try:
        from data_pipeline.storage.duckdb_manager import ensure_tables, get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return {
                "generated_today": 0,
                "passed_backtest": 0,
                "passed_risk": 0,
                "deployed": 0,
                "source": "stub_no_db",
                "binding_note": note,
            }
        conn = get_conn(read_only=False)
        try:
            ensure_tables(conn)
            out = _alpha_lab_compute_counts(conn)
            out["source"] = "duckdb"
            out["binding_note"] = note
            return out
        finally:
            conn.close()
    except Exception:
        _log.exception("get_alpha_lab")
        return {
            "generated_today": 0,
            "passed_backtest": 0,
            "passed_risk": 0,
            "deployed": 0,
            "source": "error",
            "binding_note": note,
        }


# Hongshan / Next 共用：认证、行情、委托、持仓（DuckDB 单栈）
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
