#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
portfolio_system 示例：回测 + 模拟交易 + 绩效报告。
目标年化 20~40%，代码可直接运行。
"""
from __future__ import annotations
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)


def main() -> None:
    from portfolio_system import Backtester, PortfolioSimulator, PortfolioConfig

    config = PortfolioConfig(
        initial_cash=1_000_000.0,
        target_annual_return_min=0.20,
        target_annual_return_max=0.40,
    )
    symbol = "000001"
    start_date = "2023-01-01"
    end_date = "2024-12-31"

    print("=" * 50)
    print("机构级 A 股组合系统 portfolio_system 示例")
    print("目标年化 20~40%")
    print("=" * 50)

    bt = Backtester(config)
    result = bt.run(symbol, start_date, end_date)

    if result.get("error"):
        print("回测失败:", result["error"])
        return

    s = result.get("summary", {})
    perf = result.get("performance_report", {})
    print("\n【回测结果】")
    print(f"  总收益率: {s.get('return_rate', 0) * 100:.2f}%")
    print(f"  最大回撤: {s.get('max_drawdown', 0) * 100:.2f}%")
    print(f"  夏普比率: {perf.get('sharpe_ratio', 0):.4f}")
    print(f"  年化收益: {perf.get('annual_return', 0) * 100:.2f}%")
    print(f"  交易次数: {result.get('stats', {}).get('trade_count', 0)}")

    print("\n【模拟交易】")
    sim = PortfolioSimulator(config)
    sim_result = sim.run(symbol, start_date, end_date)
    if sim_result.get("error"):
        print("模拟交易失败:", sim_result["error"])
    else:
        ss = sim_result.get("summary", {})
        print(f"  总收益: {ss.get('total_return', 0) * 100:.2f}%")
        print(f"  交易笔数: {len(sim_result.get('trades', []))}")

    print("\n完成。")


if __name__ == "__main__":
    main()
