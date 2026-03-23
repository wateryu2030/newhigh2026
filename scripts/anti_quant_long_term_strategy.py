#!/usr/bin/env python3
"""
反量化长线选股策略

基于 5 年十大股东数据，计算股东稳定性、机构纯度、换主频率等因子，
筛选出筹码结构稳定、长期资金主导的股票池。

用法:
  python scripts/anti_quant_long_term_strategy.py           # 从 DuckDB 读取并输出
  python scripts/anti_quant_long_term_strategy.py --csv X  # 从 CSV 读取（如有）

可调优参数见 lib/anti_quant_strategy.CONFIG。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lib"))

from lib.anti_quant_strategy import (
    CONFIG,
    load_data_from_duckdb,
    calc_factors,
    filter_stocks,
    run_strategy,
)


def load_data_from_csv(csv_path: str):
    """从 CSV 加载（备用）"""
    import pandas as pd
    df = pd.read_csv(csv_path)
    df["report_date"] = pd.to_datetime(df["report_date"])
    df["shareholder_name"] = df["shareholder_name"].fillna("").astype(str).str.strip()
    df["shareholder_type"] = df["shareholder_type"].fillna("").astype(str)
    return df


def main():
    parser = argparse.ArgumentParser(description="反量化长线选股策略")
    parser.add_argument("--csv", type=str, help="从 CSV 读取（替代 DuckDB）")
    parser.add_argument("--output", type=str, default="candidate_stocks.csv", help="输出文件")
    parser.add_argument("--plot", action="store_true", help="生成图表")
    parser.add_argument("--years", type=int, default=None, help="回溯年数（默认用 CONFIG）")
    args = parser.parse_args()

    print("加载数据...")
    if args.csv:
        df = load_data_from_csv(args.csv)
    else:
        df = load_data_from_duckdb()
    print(f"  记录数: {len(df)}, 股票数: {df['stock_code'].nunique()}, 报告期: {df['report_date'].nunique()}")

    print("计算因子...")
    factors, candidates = run_strategy(df=df, years_back=args.years)
    candidates = candidates.sort_values("top10_ratio_latest", ascending=False)

    out_path = ROOT / "output" / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    candidates.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\n筛选后股票数: {len(candidates)} (模式: {candidates['filter_mode'].iloc[0] if not candidates.empty else 'N/A'})")
    print("示例（前 10）:")
    cols = ["stock_code", "top10_ratio_latest", "institution_count_current", "long_term_institution_count", "turnover_avg", "top10_ratio_std", "filter_mode"]
    cols = [c for c in cols if c in candidates.columns]
    print(candidates[cols].head(10).to_string())

    if args.plot:
        try:
            import matplotlib.pyplot as plt
            fig, axes = plt.subplots(1, 2, figsize=(12, 4))
            valid_std = factors["top10_ratio_std"].dropna()
            if len(valid_std) > 0:
                valid_std.hist(ax=axes[0], bins=30, edgecolor="black", alpha=0.7)
            axes[0].set_title("top10_ratio_std 分布（有效值）")
            axes[0].axvline(CONFIG["top10_ratio_std_max"], color="r", linestyle="--")
            valid_turn = factors["turnover_avg"].dropna()
            if len(valid_turn) > 0:
                valid_turn.hist(ax=axes[1], bins=30, edgecolor="black", alpha=0.7)
            axes[1].set_title("turnover_avg 分布（有效值）")
            axes[1].axvline(CONFIG["turnover_avg_max"], color="r", linestyle="--")
            plt.tight_layout()
            plt.savefig(ROOT / "output" / "factor_distribution.png", dpi=150, bbox_inches="tight")
            print(f"  图表已保存: output/factor_distribution.png")
        except Exception as e:
            print(f"  绘图失败: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
