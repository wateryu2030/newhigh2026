#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多策略组合系统入口。
示例：MA+RSI+MACD 三策略等权组合，运行 30 天模拟交易。
"""
import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ROOT)


def main():
    from portfolio import MultiStrategyPortfolio, PortfolioConfig, StrategyConfig
    from portfolio.attribution import StrategyAttribution

    print("=== newhigh2026 多策略组合系统 ===\n")

    # MACD + KDJ 组合（经验较有效）
    config = PortfolioConfig(
        strategies=[
            StrategyConfig(strategy_id="macd", symbol="600519", weight=0.5),
            StrategyConfig(strategy_id="kdj", symbol="600519", weight=0.5),
        ],
        initial_cash=1_000_000.0,
    )
    portfolio = MultiStrategyPortfolio(config=config)

    start = "2024-01-01"
    end = "2024-12-31"
    print(f"运行组合回测: {start} ~ {end}")
    print("策略: MACD 50% + KDJ 50%（经验推荐组合）\n")

    result = portfolio.run_backtest(start_date=start, end_date=end, timeframe="D")

    if result.get("error"):
        print("数据库回测失败，尝试 paper_trading + AKShare...")
        result = portfolio.run_with_paper_trading(start_date=start, end_date=end)

    if result.get("error"):
        print("回测失败:", result["error"])
        return

    s = result.get("summary", result)
    stats = result.get("stats", {})
    print("--- 组合结果 ---")
    print(f"总收益率: {s.get('return_rate', 0):.2%}")
    print(f"最大回撤: {s.get('max_drawdown', 0):.2%}")
    print(f"交易次数: {stats.get('tradeCount', 0)}")
    print(f"策略: {result.get('strategy_name', '-')}")
    weights = result.get("portfolio_weights", [])
    if weights:
        print("权重:", ", ".join(f"{w['strategy_id']}={w['weight']:.0%}" for w in weights))
    print("\n完成。")


if __name__ == "__main__":
    main()
