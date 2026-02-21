#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
newhigh2026 主入口：运行模拟交易示例 30 天。
"""
import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ROOT)


def main():
    from paper_trading import PaperBroker, TradeEngine, Performance
    from strategies.ma_cross import MACrossStrategy
    from data.data_loader import load_kline

    print("=== newhigh2026 模拟交易示例 ===\n")
    broker = PaperBroker(initial_cash=1_000_000)
    engine = TradeEngine(broker=broker)
    strat = MACrossStrategy()

    # 加载 K 线（优先 AKShare，其次数据库）
    symbol = "600519"
    start = "2024-01-01"
    end = "2024-12-31"
    print(f"加载 {symbol} {start} ~ {end} K 线...")
    df = load_kline(symbol, start, end, source="akshare")
    if df is None or len(df) < 30:
        df = load_kline(symbol, start, end, source="database")
    if df is None or len(df) < 30:
        print("无法获取 K 线，请确保 data/ 有数据或网络可用。")
        return

    order_book = symbol + ".XSHG" if symbol.startswith("6") else symbol + ".XSHE"

    def get_signals(kline):
        return strat.generate_signals(kline)

    engine.run_from_kline(df, order_book, get_signals)

    perf = Performance(broker.account)
    s = perf.summary()
    print("\n--- 回测结果 ---")
    print(f"初始资金: ¥{s['initial_cash']:,.0f}")
    print(f"当前资产: ¥{s['total_equity']:,.0f}")
    print(f"总收益率: {s['total_return']:.2%}")
    print(f"最大回撤: {s['max_drawdown']:.2%}")
    print(f"夏普比率: {s['sharpe_ratio']:.3f}")
    print(f"交易次数: {s['trade_count']}")
    print("\n完成。")


if __name__ == "__main__":
    main()
