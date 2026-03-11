"""从 quant_system.duckdb 加载日 K 与信号，供回测使用。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional, Tuple

import pandas as pd


def _norm_code(symbol: str) -> str:
    """6 位代码或 600519.SH -> 统一为带后缀的 code（与 a_stock_daily 一致）。"""
    s = (symbol or "").strip()
    if not s:
        return ""
    code = s.split(".")[0]
    if len(code) == 6 and code.isdigit():
        if code.startswith("6"):
            return f"{code}.SH"
        if code.startswith(("0", "3")):
            return f"{code}.SZ"
        return f"{code}.SH"
    return s if "." in s else f"{code}.SH"


def _to_ts(d) -> datetime:
    if hasattr(d, "to_pydatetime"):
        t = d.to_pydatetime()
    elif isinstance(d, str):
        t = datetime.strptime(d[:10], "%Y-%m-%d")
    else:
        t = datetime.now(timezone.utc)
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t


def load_ohlcv_from_db(
    symbol: str,
    start_date: str,
    end_date: str,
    conn: Any = None,
) -> Tuple[pd.DataFrame, List[Any]]:
    """
    从 quant_system.duckdb 的 a_stock_daily 加载日 K。
    返回 (DataFrame with columns date, open, high, low, close, volume), list[OHLCV]。
    若 a_stock_daily 无数据则尝试 daily_bars（需 order_book_id）。
    """
    code = _norm_code(symbol)
    close_conn = False
    if conn is None:
        try:
            from data_pipeline.storage.duckdb_manager import get_conn
            conn = get_conn(read_only=True)
            close_conn = True
        except Exception:
            return pd.DataFrame(), []

    start = start_date.replace("-", "")[:8]
    end = end_date.replace("-", "")[:8]
    out_df = pd.DataFrame()
    ohlcv_list: List[Any] = []

    try:
        df = conn.execute(
            """SELECT code, date, open, high, low, close, volume, amount
               FROM a_stock_daily
               WHERE code = ? AND date >= ? AND date <= ?
               ORDER BY date""",
            [code, start, end],
        ).fetchdf()
        if df is not None and not df.empty:
            df = df.rename(columns={"date": "date"})
            df["date"] = pd.to_datetime(df["date"])
            out_df = df[["date", "open", "high", "low", "close", "volume"]].copy()
            try:
                from core import OHLCV
                for _, row in df.iterrows():
                    ohlcv_list.append(
                        OHLCV(
                            symbol=symbol or code,
                            timestamp=_to_ts(row["date"]),
                            open=float(row["open"] or 0),
                            high=float(row["high"] or 0),
                            low=float(row["low"] or 0),
                            close=float(row["close"] or 0),
                            volume=float(row["volume"] or 0),
                            interval="1d",
                        )
                    )
            except ImportError:
                pass
    except Exception:
        pass
    if close_conn and conn is not None:
        try:
            conn.close()
        except Exception:
            pass
    return out_df, ohlcv_list


def load_signals_from_db(
    symbol: str,
    start_date: str,
    end_date: str,
    signal_source: str = "trade_signals",
    strategy_id: Optional[str] = None,
    conn: Any = None,
) -> Tuple[dict, dict]:
    """
    从 trade_signals 或 market_signals 加载该标的在区间内的信号。
    signal_source: 'trade_signals' | 'market_signals'
    strategy_id: 仅当 signal_source='trade_signals' 时过滤策略。
    约定：signal 含 'buy'/'long'/'买入' -> entry=True；'sell'/'short'/'卖出' -> exit=True。
    返回 (entries_by_date, exits_by_date) 为 date_str -> True 的 dict。
    """
    code = _norm_code(symbol)
    close_conn = False
    if conn is None:
        try:
            from data_pipeline.storage.duckdb_manager import get_conn
            conn = get_conn(read_only=True)
            close_conn = True
        except Exception:
            return {}, {}

    start = start_date.replace("-", "")[:8]
    end = end_date.replace("-", "")[:8]
    entries: dict = {}
    exits: dict = {}

    try:
        if signal_source == "trade_signals":
            if strategy_id and str(strategy_id).strip():
                df = conn.execute(
                    """SELECT code, signal, snapshot_time
                       FROM trade_signals
                       WHERE code = ? AND strategy_id = ? AND DATE(snapshot_time) >= ? AND DATE(snapshot_time) <= ?
                       ORDER BY snapshot_time""",
                    [code, str(strategy_id).strip(), start, end],
                ).fetchdf()
            else:
                df = conn.execute(
                    """SELECT code, signal, snapshot_time
                       FROM trade_signals
                       WHERE code = ? AND DATE(snapshot_time) >= ? AND DATE(snapshot_time) <= ?
                       ORDER BY snapshot_time""",
                    [code, start, end],
                ).fetchdf()
        else:
            df = conn.execute(
                """SELECT code, signal_type, score, snapshot_time
                   FROM market_signals
                   WHERE code = ? AND DATE(snapshot_time) >= ? AND DATE(snapshot_time) <= ?
                   ORDER BY snapshot_time""",
                [code, start, end],
            ).fetchdf()
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                ts = row.get("snapshot_time")
                if ts is None:
                    continue
                d = ts if hasattr(ts, "strftime") else str(ts)[:10]
                if hasattr(d, "strftime"):
                    date_key = d.strftime("%Y-%m-%d")
                else:
                    date_key = str(d)[:10]
                sig = str(row.get("signal") or row.get("signal_type") or "").lower()
                if any(x in sig for x in ("buy", "long", "买入", "多")):
                    entries[date_key] = True
                if any(x in sig for x in ("sell", "short", "卖出", "空")):
                    exits[date_key] = True
    except Exception:
        pass
    if close_conn and conn is not None:
        try:
            conn.close()
        except Exception:
            pass

    return entries, exits
