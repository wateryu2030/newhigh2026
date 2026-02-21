# -*- coding: utf-8 -*-
"""
信号排序：结合 AI 分数与策略信号，计算最终排名。
final_score = 0.6 * ai_score + 0.4 * strategy_score
"""
from __future__ import annotations
from typing import Dict, List, Optional
import pandas as pd


def rank_signals(
    ai_scores: pd.DataFrame,
    strategy_scores: Optional[pd.DataFrame] = None,
    ai_weight: float = 0.6,
    strategy_weight: float = 0.4,
) -> pd.DataFrame:
    """
    合并 AI 分与策略分，得到最终排序表。
    :param ai_scores: 列 symbol, score (0–1)
    :param strategy_scores: 列 symbol, score (0–1)，可选
    :return: 列 symbol, ai_score, strategy_score, final_score，按 final_score 降序
    """
    out = ai_scores.copy()
    out = out.rename(columns={"score": "ai_score"})
    if "ai_score" not in out.columns:
        out["ai_score"] = 0.5
    out["strategy_score"] = 0.5
    if strategy_scores is not None and len(strategy_scores) > 0:
        ss = strategy_scores.rename(columns={"score": "strategy_score"})[["symbol", "strategy_score"]]
        out = out.drop(columns=["strategy_score"], errors="ignore").merge(ss, on="symbol", how="left")
        out["strategy_score"] = out["strategy_score"].fillna(0.5)
    out["final_score"] = ai_weight * out["ai_score"] + strategy_weight * out["strategy_score"]
    out = out.sort_values("final_score", ascending=False).reset_index(drop=True)
    return out


def top_n_symbols(
    ranked: pd.DataFrame,
    n: int = 20,
    min_final_score: float = 0.0,
) -> List[str]:
    """取最终排名 Top N 的 symbol 列表。"""
    r = ranked[ranked["final_score"] >= min_final_score].head(n)
    return r["symbol"].tolist()
