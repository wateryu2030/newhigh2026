# Auto-fixed by Cursor on 2026-04-02: Parquet IO + yfinance/akshare download helpers + universe stub.
"""辅助拉取行情与 universe；与 DuckDB 主仓并存，用于冷数据归档。"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

import numpy as np
import pandas as pd

_log = logging.getLogger(__name__)

DEFAULT_PARQUET_ROOT = Path(__file__).resolve().parents[1] / "data" / "parquet"


def save_to_parquet(df: pd.DataFrame, path: Path, **kwargs: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, **kwargs)


def load_from_parquet(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path)


def write_metadata(root: Path, payload: dict) -> None:
    root.mkdir(parents=True, exist_ok=True)
    p = root / "metadata.json"
    payload = {**payload, "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def clean_ohlcv_df(df: pd.DataFrame) -> pd.DataFrame:
    """前向填充收盘价、丢弃全空行；不做复权（由上游决定）。"""
    if df is None or df.empty:
        return df
    out = df.copy()
    for c in ("open", "high", "low", "close", "volume"):
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    if "close" in out.columns:
        out["close"] = out["close"].ffill()
    return out.dropna(how="all")


def download_daily_yfinance(symbol: str, start: str, end: str) -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError as e:
        _log.warning("yfinance not installed: %s", e)
        return pd.DataFrame()
    try:
        d = yf.download(symbol, start=start, end=end, progress=False, auto_adjust=True)
        if d is None or d.empty:
            return pd.DataFrame()
        d = d.rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )
        d = d.reset_index()
        if "Date" in d.columns:
            d = d.rename(columns={"Date": "date"})
        return clean_ohlcv_df(d)
    except Exception as e:
        _log.exception("yfinance download failed %s: %s", symbol, e)
        return pd.DataFrame()


def download_daily_akshare(symbol: str, start: str, end: str) -> pd.DataFrame:
    try:
        import akshare as ak
    except ImportError as e:
        _log.warning("akshare not installed: %s", e)
        return pd.DataFrame()
    try:
        code = symbol.strip().split(".")[0]
        start_s = start.replace("-", "")
        end_s = end.replace("-", "")
        df = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start_s,
            end_date=end_s,
            adjust="qfq",
        )
        if df is None or df.empty:
            return pd.DataFrame()
        colmap = {
            "日期": "date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
        }
        df = df.rename(columns={k: v for k, v in colmap.items() if k in df.columns})
        df["date"] = pd.to_datetime(df["date"])
        return clean_ohlcv_df(df)
    except Exception as e:
        _log.exception("akshare download failed %s: %s", symbol, e)
        return pd.DataFrame()


def download_daily(symbol: str, start: str, end: str, source: str = "auto") -> pd.DataFrame:
    """
    source: auto | yfinance | akshare
    auto: 6 位数字用 akshare，否则 yfinance
    """
    s = symbol.strip()
    if source == "yfinance":
        return download_daily_yfinance(s, start, end)
    if source == "akshare":
        return download_daily_akshare(s, start, end)
    if s[:6].isdigit() and len(s) >= 6:
        return download_daily_akshare(s, start, end)
    return download_daily_yfinance(s, start, end)


def get_universe(asof: Optional[str] = None) -> List[str]:
    """
    返回股票代码列表：优先 Parquet universe；否则 DuckDB a_stock_basic；再否则空。
    asof: YYYY-MM-DD，用于未来接指数成分历史；当前为占位。
    """
    root = Path(os.environ.get("NEWHIGH_PARQUET_ROOT", str(DEFAULT_PARQUET_ROOT)))
    uni = root / "universe" / f"universe_{(asof or 'latest')}.parquet"
    if uni.is_file():
        try:
            df = load_from_parquet(uni)
            if "code" in df.columns:
                return df["code"].astype(str).tolist()
        except Exception as e:
            _log.warning("read universe parquet failed: %s", e)
    try:
        from data_pipeline.storage.duckdb_manager import get_conn

        conn = get_conn(read_only=True)
        try:
            rows = conn.execute(
                "SELECT code FROM a_stock_basic WHERE code IS NOT NULL ORDER BY code LIMIT 8000"
            ).fetchall()
            return [str(r[0]) for r in rows or []]
        finally:
            conn.close()
    except Exception as e:
        _log.warning("get_universe duckdb fallback failed: %s", e)
    return []


def risk_free_series_flat(rate: float = 0.02, index: pd.DatetimeIndex) -> pd.Series:
    """占位：常数无风险日收益近似 rate/252。"""
    daily = (1.0 + float(rate)) ** (1.0 / 252.0) - 1.0
    return pd.Series(np.full(len(index), daily), index=index)
