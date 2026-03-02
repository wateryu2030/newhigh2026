# -*- coding: utf-8 -*-
"""
龙虎榜资金胜率统计：知名游资席位净买入后 +1/+3/+5/+10 日收益、胜率、盈亏比、最大回撤。
支持并发抓取、自动缓存、按席位排名，输出 lhb_statistics_report.json。
"""
from __future__ import annotations
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_LHB_CACHE_DIR = os.path.join(_ROOT, "data", "lhb_cache")
DEFAULT_REPORT_PATH = os.path.join(_ROOT, "output", "lhb_statistics_report.json")


def _order_book_id(symbol: str) -> str:
    """6 位代码 -> order_book_id。"""
    s = (symbol or "").strip()
    if len(s) >= 6 and s[:1] == "6":
        return s[:6] + ".XSHG"
    if len(s) >= 6:
        return s[:6] + ".XSHE"
    return s + ".XSHE"


def _fetch_lhb_for_date(date_ymd: str) -> List[Dict[str, Any]]:
    """单日龙虎榜明细，返回 [{symbol, seat, net_buy_wan, date}, ...] 仅游资净买。"""
    from core.lhb_engine import fetch_lhb_detail, _net_buy_value, _row_val, _seat_name
    from analysis.seat_database import is_yz_seat

    df = fetch_lhb_detail(date_ymd)
    if df is None or (hasattr(df, "__len__") and len(df) == 0):
        return []
    try:
        df = df if isinstance(df, pd.DataFrame) else pd.DataFrame(df)
    except Exception:
        return []
    cols = list(df.columns)
    out = []
    for _, row in df.iterrows():
        seat = _seat_name(row, cols)
        if not is_yz_seat(seat):
            continue
        net_buy = _net_buy_value(row, cols)
        if net_buy <= 0:
            continue
        symbol = str(_row_val(row, cols, "代码", "symbol") or "").strip()
        if not symbol or len(symbol) < 5:
            continue
        out.append({
            "symbol": symbol,
            "order_book_id": _order_book_id(symbol),
            "seat": seat,
            "net_buy_wan": net_buy,
            "date": date_ymd,
        })
    return out


def _trading_days(start: datetime, end: datetime) -> List[str]:
    """[start,end] 交易日，返回 YYYYMMDD 列表。"""
    out = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            out.append(d.strftime("%Y%m%d"))
        d += timedelta(days=1)
    return out


def _load_cached_lhb(date_ymd: str, cache_dir: str) -> Optional[List[Dict]]:
    path = os.path.join(cache_dir, f"lhb_{date_ymd}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_cached_lhb(date_ymd: str, records: List[Dict], cache_dir: str) -> None:
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, f"lhb_{date_ymd}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False)


def fetch_lhb_history(
    start_date: str,
    end_date: str,
    cache_dir: str = DEFAULT_LHB_CACHE_DIR,
    max_workers: int = 4,
) -> List[Dict[str, Any]]:
    """
    拉取 [start_date, end_date] 龙虎榜游资净买记录，自动缓存。
    """
    start_d = datetime.strptime(start_date[:10], "%Y-%m-%d")
    end_d = datetime.strptime(end_date[:10], "%Y-%m-%d")
    days = _trading_days(start_d, end_d)
    all_records: List[Dict[str, Any]] = []
    to_fetch = []
    for d in days:
        cached = _load_cached_lhb(d, cache_dir)
        if cached is not None:
            all_records.extend(cached)
        else:
            to_fetch.append(d)

    def do_fetch(date_ymd: str) -> Tuple[str, List[Dict]]:
        rec = _fetch_lhb_for_date(date_ymd)
        return date_ymd, rec

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(do_fetch, d): d for d in to_fetch}
        for fut in as_completed(futures):
            try:
                date_ymd, rec = fut.result()
                all_records.extend(rec)
                _save_cached_lhb(date_ymd, rec, cache_dir)
            except Exception:
                pass
    return all_records


def compute_forward_returns(
    order_book_id: str,
    buy_date: str,
    horizons: List[int],
    db_path: Optional[str] = None,
) -> Dict[int, Optional[float]]:
    """计算 buy_date 之后 +1,+3,+5,+10 日收益率（按交易日）。"""
    from database.duckdb_backend import DuckDBBackend
    import os as _os
    _root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    if db_path is None:
        db_path = _os.path.join(_root, "data", "quant.duckdb")
    if not _os.path.exists(db_path):
        return {h: None for h in horizons}
    backend = DuckDBBackend(db_path)
    # buy_date 格式 YYYY-MM-DD 或 YYYYMMDD
    s = buy_date.replace("-", "").replace("/", "")[:8]
    buy_d = datetime.strptime(s, "%Y%m%d")
    end_d = buy_d + timedelta(days=max(horizons) * 2 + 10)
    start_str = (buy_d - timedelta(days=5)).strftime("%Y-%m-%d")
    end_str = end_d.strftime("%Y-%m-%d")
    bars = backend.get_daily_bars(order_book_id, start_date=start_str, end_date=end_str)
    if bars is None or len(bars) < 2:
        return {h: None for h in horizons}
    bars = bars.sort_index()
    dates = bars.index.tolist()
    close = bars["close"]
    buy_ts = pd.Timestamp(buy_d)
    idx0 = next((i for i, d in enumerate(dates) if d >= buy_ts), None)
    if idx0 is None:
        return {h: None for h in horizons}
    out = {}
    for h in horizons:
        if idx0 + h >= len(dates):
            out[h] = None
            continue
        try:
            p0 = float(close.iloc[idx0])
            p1 = float(close.iloc[idx0 + h])
            if p0 and p0 > 0:
                out[h] = (p1 / p0 - 1.0)
            else:
                out[h] = None
        except Exception:
            out[h] = None
    return out


def run_lhb_statistics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    years: int = 2,
    cache_dir: str = DEFAULT_LHB_CACHE_DIR,
    report_path: str = DEFAULT_REPORT_PATH,
    max_workers: int = 4,
) -> Dict[str, Any]:
    """
    主流程：拉取龙虎榜 → 按席位聚合净买 → 计算 +1/+3/+5/+10 收益 → 胜率/盈亏比/最大回撤 → 输出报告。
    """
    from backtest.performance_analyzer import analyze_returns

    if end_date is None:
        end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    if start_date is None:
        end_d = datetime.strptime(end_date[:10], "%Y-%m-%d")
        start_date = (end_d - timedelta(days=years * 365)).strftime("%Y-%m-%d")

    records = fetch_lhb_history(start_date, end_date, cache_dir=cache_dir, max_workers=max_workers)
    horizons = [1, 3, 5, 10]
    # (date, order_book_id) -> [ (seat, net_buy_wan), ... ]
    by_key: Dict[Tuple[str, str], List[Tuple[str, float]]] = {}
    for r in records:
        key = (r["date"], r.get("order_book_id") or _order_book_id(r["symbol"]))
        by_key.setdefault(key, []).append((r["seat"], r.get("net_buy_wan", 0)))
    # 每个 (date, ob_id) 只算一次收益，但归属多个席位
    key_returns: Dict[Tuple[str, str], Dict[int, Optional[float]]] = {}
    for (d, ob_id) in list(by_key.keys()):
        date_str = d[:4] + "-" + d[4:6] + "-" + d[6:8]
        key_returns[(d, ob_id)] = compute_forward_returns(ob_id, date_str, horizons)

    # 按席位聚合收益序列
    by_seat: Dict[str, Dict[int, List[float]]] = {}
    for (d, ob_id), rets in key_returns.items():
        seats = [s for s, _ in by_key[(d, ob_id)]]
        for h in horizons:
            r = rets.get(h)
            if r is not None:
                for seat in seats:
                    by_seat.setdefault(seat, {}).setdefault(h, []).append(r)

    report_seats: Dict[str, Dict[str, Any]] = {}
    for seat, hor_rets in by_seat.items():
        report_seats[seat] = {}
        for h, rets in hor_rets.items():
            report_seats[seat][f"+{h}日"] = analyze_returns(rets)
        # 高胜率标记：+5 日胜率 > 0.55
        wr5 = report_seats[seat].get("+5日", {}).get("win_rate", 0) or 0
        report_seats[seat]["high_win_rate"] = wr5 >= 0.55

    # 排行榜：按 +5 日胜率
    ranking = sorted(
        report_seats.items(),
        key=lambda x: (x[1].get("+5日", {}).get("win_rate", 0) or 0),
        reverse=True,
    )
    report = {
        "start_date": start_date,
        "end_date": end_date,
        "by_seat": report_seats,
        "ranking": [{"seat": s, "win_rate_5d": (d.get("+5日", {}).get("win_rate"))} for s, d in ranking],
        "total_records": len(records),
    }
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report
