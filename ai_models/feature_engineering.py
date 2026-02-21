# -*- coding: utf-8 -*-
"""
因子工程：从股票历史 K 线生成机器学习特征。
输出 DataFrame: date | symbol | feature1 | ... | label
"""
from __future__ import annotations
from typing import Optional
import numpy as np
import pandas as pd


def _ensure_close_series(df: pd.DataFrame) -> pd.Series:
    """统一获取收盘价序列（支持 date 列或 index）。"""
    if "close" in df.columns:
        return df["close"]
    if "收盘" in df.columns:
        return df["收盘"]
    raise ValueError("need close or 收盘 column")


def _ensure_volume(df: pd.DataFrame) -> pd.Series:
    if "volume" in df.columns:
        return df["volume"]
    if "成交量" in df.columns:
        return df["成交量"]
    return pd.Series(np.nan, index=df.index)


def _ensure_date_col(df: pd.DataFrame) -> pd.Series:
    if "date" in df.columns:
        return pd.to_datetime(df["date"])
    if df.index is not None and len(df.index) > 0:
        return pd.to_datetime(df.index)
    raise ValueError("need date column or datetime index")


def compute_ma(close: pd.Series, window: int) -> pd.Series:
    return close.rolling(window=window, min_periods=1).mean()


def compute_returns(close: pd.Series, periods: int) -> pd.Series:
    return close.pct_change(periods)


def compute_volatility(close: pd.Series, window: int = 20) -> pd.Series:
    return close.pct_change().rolling(window=window, min_periods=2).std()


def compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """Average True Range."""
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window=window, min_periods=1).mean()


def compute_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=window, min_periods=1).mean()
    avg_loss = loss.rolling(window=window, min_periods=1).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def compute_max_drawdown(close: pd.Series, window: int = 20) -> pd.Series:
    """滚动窗口内最大回撤（正数表示回撤幅度）。"""
    roll_max = close.rolling(window=window, min_periods=1).max()
    dd = (close - roll_max) / roll_max.replace(0, np.nan)
    return -dd  # 正数表示回撤


def compute_high_distance(close: pd.Series, window: int = 20) -> pd.Series:
    """与 N 日新高的距离（0~1，1 表示创新高）。"""
    roll_high = close.rolling(window=window, min_periods=1).max()
    return close / roll_high.replace(0, np.nan)


def compute_ma_alignment(close: pd.Series) -> pd.Series:
    """均线多头排列：MA5 > MA10 > MA20 > MA60 为 1，否则 0。"""
    ma5 = compute_ma(close, 5)
    ma10 = compute_ma(close, 10)
    ma20 = compute_ma(close, 20)
    ma60 = compute_ma(close, 60)
    return ((ma5 > ma10) & (ma10 > ma20) & (ma20 > ma60)).astype(float)


def build_features_for_symbol(
    df: pd.DataFrame,
    symbol: str,
    label_forward_days: int = 5,
) -> pd.DataFrame:
    """
    单只股票从 K 线构建特征与标签。
    :param df: 列需含 date/close（或 日期/收盘）、high/low、volume（或 成交量）
    :param symbol: 标的代码
    :param label_forward_days: 未来 N 日收益作为 label
    :return: DataFrame 每行 date, symbol, 多列 feature, label
    """
    close = _ensure_close_series(df)
    dates = _ensure_date_col(df)
    high = df["high"] if "high" in df.columns else df["最高"] if "最高" in df.columns else close
    low = df["low"] if "low" in df.columns else df["最低"] if "最低" in df.columns else close
    volume = _ensure_volume(df)

    # 技术因子
    ma5 = compute_ma(close, 5)
    ma10 = compute_ma(close, 10)
    ma20 = compute_ma(close, 20)
    ma60 = compute_ma(close, 60)
    ret_1 = compute_returns(close, 1)
    vol_20 = compute_volatility(close, 20)
    atr = compute_atr(high, low, close, 14)
    rsi = compute_rsi(close, 14)
    macd_line, _, macd_hist = compute_macd(close)
    vol_change = volume.pct_change(5) if volume.notna().any() else pd.Series(0.0, index=close.index)

    # 趋势因子
    high_dist_20 = compute_high_distance(close, 20)
    ma_align = compute_ma_alignment(close)

    # 动量因子
    ret_5 = compute_returns(close, 5)
    ret_20 = compute_returns(close, 20)
    ret_60 = compute_returns(close, 60)

    # 风险因子
    max_dd_20 = compute_max_drawdown(close, 20)

    # 标签：未来 N 日收益
    future_ret = close.shift(-label_forward_days) / close - 1.0

    out = pd.DataFrame({
        "date": dates,
        "symbol": symbol,
        "ma5": ma5,
        "ma10": ma10,
        "ma20": ma20,
        "ma60": ma60,
        "return_1d": ret_1,
        "volatility_20": vol_20,
        "atr_14": atr,
        "rsi_14": rsi,
        "macd_hist": macd_hist,
        "volume_change_5": vol_change,
        "high_dist_20": high_dist_20,
        "ma_alignment": ma_align,
        "return_5d": ret_5,
        "return_20d": ret_20,
        "return_60d": ret_60,
        "max_drawdown_20": max_dd_20,
        "label": future_ret,
    })
    out = out.dropna(subset=["label"])
    return out


def build_features_multi(
    market_data: dict[str, pd.DataFrame],
    label_forward_days: int = 5,
) -> pd.DataFrame:
    """
    多标的合并因子表。
    :param market_data: { order_book_id 或 symbol: DataFrame }
    :param label_forward_days: 未来 N 日收益作为 label
    """
    frames: list[pd.DataFrame] = []
    for sym, df in market_data.items():
        if df is None or len(df) < 80:
            continue
        code = sym.split(".")[0] if "." in sym else sym
        try:
            fe = build_features_for_symbol(df, code, label_forward_days)
            if len(fe) > 0:
                frames.append(fe)
        except Exception:
            continue
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)
