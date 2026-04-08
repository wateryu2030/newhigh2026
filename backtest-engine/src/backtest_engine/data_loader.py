# Auto-fixed by Cursor on 2026-04-02: 信号执行滞后默认 T+1、logging、异常记录。
"""从 quant_system.duckdb 加载日 K 与信号，供回测使用。"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, List, Optional, Tuple

import pandas as pd

_log = logging.getLogger(__name__)


def _norm_code(symbol: str) -> str:
    """6 位代码或 600519.SH -> 统一为带后缀的 code（与 a_stock_daily 一致）。"""
    s = (symbol or "").strip()
    if not s:
        return ""
    code = s.split(".", maxsplit=1)[0]
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


def _build_ohlcv_list(df: pd.DataFrame, symbol: str, code: str) -> List[Any]:
    """从 DataFrame 构建 OHLCV 对象列表。"""
    ohlcv_list: List[Any] = []
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
    return ohlcv_list


def _try_close_conn(conn: Any) -> None:
    """尝试关闭数据库连接。"""
    if conn is not None:
        try:
            conn.close()
        except Exception as e:
            _log.debug("duckdb close: %s", e)


def _execution_lag_bdays() -> int:
    raw = os.environ.get("BACKTEST_SIGNAL_EXECUTION_LAG_BDAYS", "1").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 1


def _shift_signal_date_key(date_key: str, lag_bdays: int) -> str:
    """将信号生效日顺延 N 个交易日，减轻收盘后信息当日成交的前视偏差。"""
    if lag_bdays <= 0:
        return date_key
    try:
        ts = pd.Timestamp(date_key)
        shifted = ts + pd.tseries.offsets.BDay(lag_bdays)
        return shifted.strftime("%Y-%m-%d")
    except Exception as e:
        _log.warning("shift_signal_date_key failed %s: %s", date_key, e)
        return date_key


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
            conn = get_conn(read_only=False)
            close_conn = True
        except Exception as e:
            _log.warning("load_ohlcv_from_db: no db: %s", e)
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

        if df is None or df.empty:
            return out_df, ohlcv_list

        df = df.rename(columns={"date": "date"})
        df["date"] = pd.to_datetime(df["date"])
        out_df = df[["date", "open", "high", "low", "close", "volume"]].copy()
        ohlcv_list = _build_ohlcv_list(df, symbol, code)

    except Exception as e:
        _log.exception("load_ohlcv_from_db failed: %s", symbol)
    finally:
        if close_conn:
            _try_close_conn(conn)

    return out_df, ohlcv_list


def _is_entry_signal(sig: str) -> bool:
    """判断是否为买入信号。"""
    return any(x in sig for x in ("buy", "long", "买入", "多"))


def _is_exit_signal(sig: str) -> bool:
    """判断是否为卖出信号。"""
    return any(x in sig for x in ("sell", "short", "卖出", "空"))


def _format_date_key(ts) -> str:
    """将时间戳格式化为日期字符串 YYYY-MM-DD。"""
    if hasattr(ts, "strftime"):
        return ts.strftime("%Y-%m-%d")
    return str(ts)[:10]


def _query_signals(conn, code: str, start: str, end: str, signal_source: str, strategy_id: Optional[str]) -> pd.DataFrame:
    """根据信号源查询信号数据。"""
    if signal_source == "trade_signals":
        if strategy_id and str(strategy_id).strip():
            return conn.execute(
                """SELECT code, signal, snapshot_time
                   FROM trade_signals
                   WHERE code = ? AND strategy_id = ? AND DATE(snapshot_time) >= ? AND DATE(snapshot_time) <= ?
                   ORDER BY snapshot_time""",
                [code, str(strategy_id).strip(), start, end],
            ).fetchdf()
        return conn.execute(
            """SELECT code, signal, snapshot_time
               FROM trade_signals
               WHERE code = ? AND DATE(snapshot_time) >= ? AND DATE(snapshot_time) <= ?
               ORDER BY snapshot_time""",
            [code, start, end],
        ).fetchdf()
    return conn.execute(
        """SELECT code, signal_type, score, snapshot_time
           FROM market_signals
           WHERE code = ? AND DATE(snapshot_time) >= ? AND DATE(snapshot_time) <= ?
           ORDER BY snapshot_time""",
        [code, start, end],
    ).fetchdf()


def load_signals_from_db(
    symbol: str,
    start_date: str,
    end_date: str,
    signal_source: str = "trade_signals",
    strategy_id: Optional[str] = None,
    conn: Any = None,
    execution_lag_bdays: Optional[int] = None,
) -> Tuple[dict, dict]:
    """
    从 trade_signals 或 market_signals 加载该标的在区间内的信号。
    signal_source: 'trade_signals' | 'market_signals'
    strategy_id: 仅当 signal_source='trade_signals' 时过滤策略。
    约定：signal 含 'buy'/'long'/'买入' -> entry=True；'sell'/'short'/'卖出' -> exit=True。
    返回 (entries_by_date, exits_by_date) 为 date_str -> True 的 dict。
    execution_lag_bdays: 默认读环境变量 BACKTEST_SIGNAL_EXECUTION_LAG_BDAYS（默认 1），
    将信号映射到之后第 N 个交易日，降低「收盘后信号当日成交」类前视偏差。
    """
    code = _norm_code(symbol)
    close_conn = False

    if conn is None:
        try:
            from data_pipeline.storage.duckdb_manager import get_conn
            conn = get_conn(read_only=False)
            close_conn = True
        except Exception as e:
            _log.warning("load_signals_from_db: no db: %s", e)
            return {}, {}

    start = start_date.replace("-", "")[:8]
    end = end_date.replace("-", "")[:8]
    entries: dict = {}
    exits: dict = {}
    lag = int(execution_lag_bdays) if execution_lag_bdays is not None else _execution_lag_bdays()

    try:
        df = _query_signals(conn, code, start, end, signal_source, strategy_id)
        if df is None or df.empty:
            return entries, exits

        for _, row in df.iterrows():
            ts = row.get("snapshot_time")
            if ts is None:
                continue
            date_key = _shift_signal_date_key(_format_date_key(ts), lag)
            sig = str(row.get("signal") or row.get("signal_type") or "").lower()
            if _is_entry_signal(sig):
                entries[date_key] = True
            if _is_exit_signal(sig):
                exits[date_key] = True

    except Exception as e:
        _log.exception("load_signals_from_db failed: %s", symbol)
    finally:
        if close_conn:
            _try_close_conn(conn)

    return entries, exits
