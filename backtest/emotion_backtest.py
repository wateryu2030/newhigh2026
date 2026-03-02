# -*- coding: utf-8 -*-
"""
情绪周期回测验证：将策略/指数收益按情绪阶段分组，统计各阶段平均收益、胜率、盈亏比、最大回撤、夏普。
支持多策略、批量回测，输出 emotion_performance_report.json 与可选可视化。
"""
from __future__ import annotations
import json
import os
from typing import Any, Dict, List, Optional

import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_EMOTION_CACHE = os.path.join(_ROOT, "data", "emotion_history.csv")
DEFAULT_REPORT_PATH = os.path.join(_ROOT, "output", "emotion_performance_report.json")


def _ensure_emotion_history(
    start_date: str,
    end_date: str,
    cache_path: str = DEFAULT_EMOTION_CACHE,
) -> pd.DataFrame:
    """确保 emotion_history 存在并加载为 DataFrame。"""
    from backtest.emotion_labeler import generate_emotion_history, load_cached_emotion, save_emotion_cache

    generate_emotion_history(start_date=start_date, end_date=end_date, cache_path=cache_path)
    cached = load_cached_emotion(cache_path)
    need_dates = pd.date_range(start=start_date, end=end_date, freq="B")
    missing = [d.strftime("%Y-%m-%d") for d in need_dates if d.strftime("%Y-%m-%d") not in cached]
    if missing:
        from core.sentiment_engine import get_emotion_state
        for d in missing:
            ymd = d.replace("-", "")
            state = get_emotion_state(date_ymd=ymd)
            cached[d] = state.get("emotion_cycle", "启动")
        records = [{"date": k, "emotion_state": v} for k, v in sorted(cached.items())]
        save_emotion_cache(records, cache_path)
    df = pd.read_csv(cache_path)
    df["date"] = pd.to_datetime(df["date"])
    return df


def run_emotion_backtest(
    returns_series: pd.Series,
    emotion_df: pd.DataFrame,
) -> Dict[str, Any]:
    """
    按情绪分组统计收益。
    :param returns_series: index=date(DatetimeIndex), value=日收益率
    :param emotion_df: columns [date, emotion_state]
    :return: by_emotion 各阶段指标 + summary
    """
    from backtest.performance_analyzer import analyze_returns

    returns_series = returns_series.dropna()
    df = returns_series.to_frame("return")
    df = df.reset_index()
    # 收益表日期列可能为 trade_date（DuckDB）或 date，统一为 date
    date_col = "trade_date" if "trade_date" in df.columns else "date"
    if date_col != "date":
        df["date"] = pd.to_datetime(df[date_col]).dt.normalize()
    else:
        df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    emotion_df = emotion_df.copy()
    if "date" not in emotion_df.columns and len(emotion_df.columns) >= 1:
        emotion_df["date"] = pd.to_datetime(emotion_df.iloc[:, 0]).dt.normalize()
    else:
        emotion_df["date"] = pd.to_datetime(emotion_df["date"]).dt.normalize()
    merged = df.merge(emotion_df[["date", "emotion_state"]], on="date", how="left")
    merged["emotion_state"] = merged["emotion_state"].fillna("未知")

    by_emotion: Dict[str, Dict[str, Any]] = {}
    for state, g in merged.groupby("emotion_state"):
        rets = g["return"].astype(float).tolist()
        by_emotion[state] = analyze_returns(rets)
        by_emotion[state]["mean_return"] = round(sum(rets) / len(rets), 6) if rets else 0.0

    # 全市场
    all_rets = merged["return"].astype(float).tolist()
    summary = analyze_returns(all_rets)
    summary["mean_return"] = round(sum(all_rets) / len(all_rets), 6) if all_rets else 0.0

    return {
        "by_emotion": by_emotion,
        "summary": summary,
        "trade_days": len(merged),
    }


def run_emotion_backtest_from_bars(
    bars_df: pd.DataFrame,
    start_date: str,
    end_date: str,
    emotion_cache_path: str = DEFAULT_EMOTION_CACHE,
) -> Dict[str, Any]:
    """
    从日线 DataFrame 计算日收益，再按情绪分组回测。
    bars_df: index=trade_date, columns 含 close
    """
    if bars_df is None or len(bars_df) == 0:
        return {"by_emotion": {}, "summary": {}, "trade_days": 0}
    close = bars_df["close"] if "close" in bars_df.columns else bars_df["收盘"]
    returns = close.pct_change().dropna()
    emotion_df = _ensure_emotion_history(start_date, end_date, emotion_cache_path)
    return run_emotion_backtest(returns, emotion_df)


def run_multi_strategy_emotion_backtest(
    strategy_returns: Dict[str, pd.Series],
    start_date: str,
    end_date: str,
    emotion_cache_path: str = DEFAULT_EMOTION_CACHE,
    report_path: str = DEFAULT_REPORT_PATH,
) -> Dict[str, Any]:
    """
    多策略情绪回测：每个策略一个 returns Series，汇总各策略按情绪的表现。
    strategy_returns: { "strategy_name": returns_series }
    """
    emotion_df = _ensure_emotion_history(start_date, end_date, emotion_cache_path)
    strategies_result = {}
    for name, ret_series in strategy_returns.items():
        if ret_series is None or len(ret_series) == 0:
            continue
        strategies_result[name] = run_emotion_backtest(ret_series, emotion_df)

    report = {
        "start_date": start_date,
        "end_date": end_date,
        "strategies": strategies_result,
    }
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report
