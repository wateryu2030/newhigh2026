#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 基金经理每日运行：从策略池/注册表取策略指标 → 再平衡 → 输出分配与订单。
可被 OpenClaw 或 cron 每日收盘后调用。
"""
from __future__ import annotations
import os
import sys
import json

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)


def main():
    from ai_fund_manager import StrategyRegistry, StrategyMetrics, AIAllocator, FundManager
    from evolution.strategy_pool import StrategyPool

    # 从自进化策略池加载策略作为“虚拟策略”并赋予模拟指标
    pool_path = os.path.join(_ROOT, "data", "evolution", "strategy_pool.json")
    registry = StrategyRegistry()
    pool = StrategyPool(persist_path=pool_path)
    pool.load()
    for i, p in enumerate(pool.get_all()):
        name = p.get("id") or f"ev_{i}"
        metrics = p.get("metrics") or {}
        registry.register(name, None, metrics=metrics)

    # 若池为空，注册两个示例策略
    if not registry.get_all():
        registry.register("ma_cross", None, metrics={"sharpe": 1.2, "max_dd": 0.08})
        registry.register("rsi", None, metrics={"sharpe": 0.9, "max_dd": 0.12})

    allocator = AIAllocator()
    manager = FundManager(registry=registry, allocator=allocator, capital=1_000_000)
    result = manager.rebalance(current_max_drawdown=0.0)
    print("再平衡结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    os.makedirs(os.path.join(_ROOT, "logs"), exist_ok=True)
    from datetime import datetime
    log_path = os.path.join(_ROOT, "logs", datetime.now().strftime("%Y%m%d") + "_manager.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("已写入", log_path)


if __name__ == "__main__":
    main()
