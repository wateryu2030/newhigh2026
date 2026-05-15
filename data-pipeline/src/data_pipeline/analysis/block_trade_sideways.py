"""
大宗交易 × 区间震荡筛选。

业务含义：在近期走势呈区间震荡（非单边趋势）的标的中，找出同期出现大宗成交的个案，
用于单独复盘「低位/徘徊 + 大宗」组合（数据仅供参考，不构成投资建议）。

数据来源：
- 大宗：AkShare ``stock_dzjy_mrmx``（东财数据中心）
- 日 K：DuckDB ``a_stock_daily``
"""

from __future__ import annotations

import logging
import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

_log = logging.getLogger(__name__)


def _code6_from_text(x: object) -> str:
    s = str(x or "").strip()
    s = re.sub(r"[^\d]", "", s)
    return s[:6].zfill(6) if len(s) >= 4 else ""


def fetch_block_trade_aggregate(
    start_date: str,
    end_date: str,
) -> Tuple[Dict[str, Dict[str, Any]], Optional[str]]:
    """
    返回 code6 -> { amount_wan, n_rows, name }；失败时第二项为错误说明。
    start_date/end_date: YYYYMMDD
    """
    try:
        import akshare as ak
    except ImportError:
        return {}, "未安装 akshare，请: pip install akshare"

    try:
        df = ak.stock_dzjy_mrmx(symbol="A股", start_date=start_date, end_date=end_date)
    except Exception as e:
        _log.warning("stock_dzjy_mrmx failed: %s", e)
        return {}, f"大宗接口失败: {e!s}"[:200]

    if df is None or getattr(df, "empty", True):
        return {}, None

    # 列名兼容（中/英）
    cols = {str(c).strip(): c for c in df.columns}
    code_col = next(
        (
            cols[k]
            for k in ("证券代码", "代码", "code", "symbol")
            if k in cols
        ),
        None,
    )
    name_col = next((cols[k] for k in ("证券简称", "名称", "name") if k in cols), None)
    amt_candidates = ("成交额", "成交额(万元)", "成交额（万元）", "amount", "成交总额")
    amt_col = next((cols[k] for k in amt_candidates if k in cols), None)

    if code_col is None:
        return {}, "大宗表缺少证券代码列"

    out: Dict[str, Dict[str, Any]] = {}
    for _, row in df.iterrows():
        c6 = _code6_from_text(row[code_col])
        if len(c6) != 6:
            continue
        name = ""
        if name_col is not None:
            name = str(row[name_col] or "").strip()
        amt_wan = 0.0
        if amt_col is not None:
            try:
                amt_wan += float(row[amt_col] or 0)
            except (TypeError, ValueError):
                pass
        if c6 not in out:
            out[c6] = {"amount_wan": 0.0, "n_rows": 0, "name": name}
        out[c6]["amount_wan"] += amt_wan
        out[c6]["n_rows"] += 1
        if name and not out[c6].get("name"):
            out[c6]["name"] = name

    return out, None


def load_daily_ohlc(
    conn: Any,
    code6: str,
    exchange_symbol: str,
    lookback_days: int,
) -> List[Tuple[Any, float, float, float, float]]:
    """返回按日期升序的 (date, o, h, l, c)。"""
    q = """
        SELECT date, open, high, low, close
        FROM a_stock_daily
        WHERE split_part(upper(trim(cast(code as varchar))), '.', 1) = ?
           OR code = ? OR code = ?
        ORDER BY date ASC
    """
    try:
        cur = conn.execute(q, [code6, code6, exchange_symbol])
        rows = cur.fetchall()
    except Exception as e:
        _log.debug("daily read %s: %s", code6, e)
        return []
    if not rows:
        return []
    # 取最近 lookback_days 条（已按日期升序，取尾部）
    tail = rows[-lookback_days:] if len(rows) > lookback_days else rows
    out: List[Tuple[Any, float, float, float, float]] = []
    for row in tail:
        d, o, h, l, c = (row + (None,) * 5)[:5]
        try:
            out.append(
                (
                    d,
                    float(o or 0),
                    float(h or 0),
                    float(l or 0),
                    float(c or 0),
                )
            )
        except (TypeError, ValueError):
            continue
    return out


def sideways_metrics(ohlc: List[Tuple[Any, float, float, float, float]]) -> Optional[Dict[str, float]]:
    if len(ohlc) < 15:
        return None
    highs = [x[2] for x in ohlc]
    lows = [x[3] for x in ohlc]
    closes = [x[4] for x in ohlc]
    if not closes or min(closes) <= 0:
        return None
    hh, ll = max(highs), min(lows)
    mean_c = sum(closes) / len(closes)
    if mean_c <= 0:
        return None
    range_ratio = (hh - ll) / mean_c
    first_c, last_c = closes[0], closes[-1]
    trend_ret = (last_c / first_c - 1.0) if first_c > 0 else 0.0
    rets = []
    for i in range(1, len(closes)):
        if closes[i - 1] > 0:
            rets.append(closes[i] / closes[i - 1] - 1.0)
    if not rets:
        return None
    import statistics

    ret_std = float(statistics.pstdev(rets)) if len(rets) > 1 else 0.0
    return {
        "range_ratio": float(range_ratio),
        "trend_ret": float(trend_ret),
        "ret_std": float(ret_std),
        "hh": float(hh),
        "ll": float(ll),
        "last_close": float(last_c),
    }


def run_screen(
    conn: Any,
    block_start: str,
    block_end: str,
    lookback_days: int,
    range_ratio_max: float,
    trend_abs_max: float,
    ret_std_max: float,
    min_amount_wan: float,
    max_codes: int,
) -> Dict[str, Any]:
    """
    block_start/block_end: YYYYMMDD（大宗统计区间）
    """
    from core.ashare_symbol import normalize_ashare_symbol_bj_display

    agg, err = fetch_block_trade_aggregate(block_start, block_end)
    if err:
        return {"ok": False, "error": err, "items": []}
    if not agg:
        return {
            "ok": True,
            "items": [],
            "note": "区间内无大宗成交记录（或数据源为空）",
            "block_range": {"start": block_start, "end": block_end},
        }

    # 按成交额排序，优先分析有大宗的标的
    ranked = sorted(
        agg.items(),
        key=lambda kv: kv[1].get("amount_wan", 0),
        reverse=True,
    )[:max_codes]

    items: List[Dict[str, Any]] = []
    for code6, meta in ranked:
        amt = float(meta.get("amount_wan") or 0)
        if min_amount_wan > 0 and amt < min_amount_wan:
            continue
        ex = normalize_ashare_symbol_bj_display(code6)
        ohlc = load_daily_ohlc(conn, code6, ex, lookback_days)
        m = sideways_metrics(ohlc)
        if m is None:
            continue
        if m["range_ratio"] > range_ratio_max:
            continue
        if abs(m["trend_ret"]) > trend_abs_max:
            continue
        if m["ret_std"] > ret_std_max:
            continue
        items.append(
            {
                "code": code6,
                "name": meta.get("name") or "",
                "block_amount_wan": round(amt, 2),
                "block_n": int(meta.get("n_rows") or 0),
                "range_ratio": round(m["range_ratio"], 4),
                "trend_ret": round(m["trend_ret"], 4),
                "ret_std": round(m["ret_std"], 4),
                "hh": m["hh"],
                "ll": m["ll"],
                "last_close": m["last_close"],
                "lookback_days_used": len(ohlc),
            }
        )

    items.sort(key=lambda x: x["block_amount_wan"], reverse=True)
    return {
        "ok": True,
        "items": items,
        "block_range": {"start": block_start, "end": block_end},
        "params": {
            "lookback_days": lookback_days,
            "range_ratio_max": range_ratio_max,
            "trend_abs_max": trend_abs_max,
            "ret_std_max": ret_std_max,
            "min_amount_wan": min_amount_wan,
        },
    }


def default_block_dates(days_back: int = 20) -> Tuple[str, str]:
    """最近自然日区间转 YYYYMMDD（大宗接口按日历）。"""
    ed = date.today()
    sd = ed - timedelta(days=max(30, days_back * 2))
    return sd.strftime("%Y%m%d"), ed.strftime("%Y%m%d")
