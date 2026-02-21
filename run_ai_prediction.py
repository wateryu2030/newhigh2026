#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 预测脚本：加载模型，对当前股票池打分，输出今日推荐股票 Top N。
"""
from __future__ import annotations
import os
import sys
from datetime import datetime, timedelta

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)


def load_multi_symbols(symbols: list[str], days: int = 120) -> dict[str, "pd.DataFrame"]:
    """从数据库或 akshare 加载多标的 K 线。"""
    import pandas as pd
    from data.data_loader import load_kline

    end = datetime.now().date()
    start = (end - timedelta(days=days)).strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")
    out = {}
    for s in symbols:
        code = s.split(".")[0] if "." in s else s
        df = load_kline(code, start, end_str, source="database")
        if df is None or len(df) < 60:
            df = load_kline(code, start, end_str, source="akshare")
        if df is not None and len(df) >= 60:
            key = s if "." in s else (s + ".XSHG" if s.startswith("6") else s + ".XSHE")
            out[key] = df
    return out


def main() -> None:
    from ai_models.model_manager import ModelManager
    from ai_models.signal_ranker import rank_signals, top_n_symbols

    TOP_N = int(os.environ.get("AI_TOP_N", "20"))
    symbols = [
        "000001", "000002", "000858", "600519", "600036", "600745", "300750",
        "601318", "000333", "002415", "300059", "600276", "000568", "601012",
        "002594", "300760", "603259", "600309",
    ]
    print("1. 加载当前行情...")
    market_data = load_multi_symbols(symbols, days=120)
    print(f"   已加载 {len(market_data)} 只标的")
    if not market_data:
        print("   无数据，请先运行 train_ai_model.py 并确保有历史数据")
        sys.exit(1)

    print("2. AI 打分...")
    manager = ModelManager()
    ai_scores = manager.predict(market_data)
    if ai_scores.empty:
        print("   未找到已训练模型，请先运行: python train_ai_model.py")
        sys.exit(1)

    ranked = rank_signals(ai_scores, ai_weight=1.0, strategy_weight=0.0)
    top = top_n_symbols(ranked, n=TOP_N)
    print(f"\n今日推荐股票 Top {TOP_N}（按 AI 分数）:")
    print("-" * 40)
    for i, sym in enumerate(top, 1):
        row = ranked[ranked["symbol"] == sym].iloc[0]
        print(f"  {i:2}. {sym:12}  score={row['final_score']:.3f}")
    print("\n完成。")


if __name__ == "__main__":
    main()
