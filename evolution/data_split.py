# -*- coding: utf-8 -*-
"""
数据划分：训练集 / 验证集 / 测试集（按时间切分，严禁未来数据泄露）。
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional, Tuple
import pandas as pd


def split_train_val_test(
    df: pd.DataFrame,
    train_ratio: float = 0.6,
    val_ratio: float = 0.2,
    test_ratio: float = 0.2,
    date_col: str = "date",
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    按时间顺序划分 train / val / test，避免未来信息泄露。
    :param df: 含 date 列或 datetime index 的 DataFrame
    :param train_ratio: 训练集比例
    :param val_ratio: 验证集比例
    :param test_ratio: 测试集比例（必须留作最终评估）
    :return: (train_df, val_df, test_df)
    """
    if df is None or len(df) < 10:
        return df, pd.DataFrame(), pd.DataFrame()
    out = df.copy()
    if date_col not in out.columns and hasattr(out.index, "str"):
        out[date_col] = out.index.astype(str).str[:10]
    out = out.sort_values(date_col).reset_index(drop=True)
    n = len(out)
    t1 = int(n * train_ratio)
    t2 = int(n * (train_ratio + val_ratio))
    train_df = out.iloc[:t1]
    val_df = out.iloc[t1:t2]
    test_df = out.iloc[t2:]
    return train_df, val_df, test_df


def ensure_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """确保存在 open/high/low/close/volume 列，缺失则用 close 或 0 填充。"""
    if df is None or len(df) == 0:
        return df
    out = df.copy()
    for col in ("open", "high", "low", "close", "volume"):
        if col not in out.columns:
            if col == "volume":
                out[col] = 0
            else:
                out[col] = out.get("close", pd.Series(1.0, index=out.index))
    if "close" not in out.columns and "open" in out.columns:
        out["close"] = out["open"]
    return out
