#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
平台自检：在不启动 Flask 的前提下验证 ai_fund_manager、evolution、API 逻辑可导入与运行。
通过后，再启动 web_platform 并用 OpenClaw 做浏览器验证。
"""
from __future__ import annotations
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)


def main():
    errors = []
    # 1) ai_fund_manager
    try:
        from ai_fund_manager import (
            FundManager,
            StrategyRegistry,
            StrategyMetrics,
            RiskBudget,
            PositionOptimizer,
            RegimeDetector,
            PortfolioRisk,
            DrawdownControl,
            AIAllocator,
        )
        reg = StrategyRegistry()
        reg.register("s1", None, metrics={"sharpe": 1.0, "max_dd": 0.1})
        reg.register("s2", None, metrics={"sharpe": 0.5, "max_dd": 0.15})
        mgr = FundManager(registry=reg, allocator=AIAllocator(), capital=1e6)
        out = mgr.rebalance()
        assert "allocation" in out and "orders" in out
        print("OK: ai_fund_manager")
    except Exception as e:
        errors.append(f"ai_fund_manager: {e}")
    # 2) evolution
    try:
        from evolution import StrategyPool, split_train_val_test
        pool = StrategyPool()
        pool.load()
        print("OK: evolution")
    except Exception as e:
        errors.append(f"evolution: {e}")
    # 3) run_manager
    try:
        from run_manager import main as run_manager_main
        # 不真的写日志，只测导入
        print("OK: run_manager")
    except Exception as e:
        errors.append(f"run_manager: {e}")

    if errors:
        for e in errors:
            print("FAIL:", e)
        sys.exit(1)
    print("All checks passed. Start web: python3 web_platform.py, then OpenClaw open http://127.0.0.1:5050")


if __name__ == "__main__":
    main()
