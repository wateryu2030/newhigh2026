# -*- coding: utf-8 -*-
"""
AI 基金经理系统入口。生产级可运行。
"""
from __future__ import annotations

if __name__ == "__main__":
    from backend.services.ai_trading_service import run_daily_trading
    result = run_daily_trading()
    print("regime:", result.get("regime"))
    print("signals_by_strategy:", result.get("signals_by_strategy"))
    print("candidates:", len(result.get("candidates", [])))
    print("strategy_weights:", result.get("strategy_weights"))
    print("portfolio:", len(result.get("portfolio", [])))
    print("orders:", len(result.get("orders", [])))
    print("logs:", result.get("logs", [])[:10])
    if result.get("error"):
        print("error:", result["error"])
