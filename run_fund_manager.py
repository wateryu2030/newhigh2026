#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 基金经理每日运行脚本。
流程：市场判断 → 选股 → 风险评估 → 资金分配 → 生成 trade_orders.json → 可选执行。
可配置为定时任务（如 crontab 每日开盘前执行）。
"""
from __future__ import annotations
import argparse
import json
import logging
import os
import sys

# 保证项目根在 path 中
_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ROOT)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="AI 基金经理：生成交易指令并可选执行")
    parser.add_argument("--capital", type=float, default=1_000_000, help="总资金")
    parser.add_argument("--method", choices=["equal_weight", "risk_parity", "kelly", "max_sharpe"], default="equal_weight")
    parser.add_argument("--top-n", type=int, default=10, dest="top_n", help="持仓标的数量")
    parser.add_argument("--output", default=None, help="trade_orders.json 输出路径")
    parser.add_argument("--execute", action="store_true", help="执行订单（否则仅生成 JSON）")
    parser.add_argument("--dry-run", action="store_true", help="执行时仅模拟，不下真实单")
    parser.add_argument("--demo", action="store_true", help="演示模式：用 akshare 取少量标的跑通流程")
    args = parser.parse_args()

    try:
        from ai_fund_manager.manager import AIManager
        manager = AIManager(capital=args.capital, portfolio_method=args.method, top_n=args.top_n)
        candidate_symbols = None
        if args.demo:
            try:
                from data.stock_pool import get_a_share_symbols
                candidate_symbols = get_a_share_symbols(exclude_delisted=True)[:30]
            except Exception:
                candidate_symbols = []
            if not candidate_symbols:
                candidate_symbols = ["000001", "600519", "600036", "000858", "601318", "600030", "000333", "601888"]
                logger.info("Demo: using fixed list of %d symbols", len(candidate_symbols))
            else:
                logger.info("Demo: using %d symbols from akshare", len(candidate_symbols))
        result = manager.run(orders_path=args.output, candidate_symbols=candidate_symbols)
        if result.get("error"):
            logger.error("Manager error: %s", result["error"])
            return 1

        logger.info("Market: %s", result.get("market"))
        logger.info("Risk: %s", result.get("risk"))
        scores = result.get("stock_scores") or []
        if scores:
            logger.info("Stock scores (code -> score):")
            for s in scores[: max(args.top_n * 2, 20)]:
                logger.info("  %s  %.4f", s.get("code", ""), s.get("score", 0))
        logger.info("Positions: %s", result.get("positions"))
        logger.info("Orders written: %s (%d orders)", result.get("orders_path"), result.get("orders_count", 0))

        if args.execute or args.dry_run:
            from ai_fund_manager.execution_engine import execute_with_callback
            exec_result = execute_with_callback(orders_path=result.get("orders_path"), dry_run=args.dry_run)
            logger.info("Execution: %s", exec_result)
            if exec_result.get("error"):
                logger.warning("Execution warning: %s", exec_result["error"])

        return 0
    except Exception as e:
        logger.exception("run_fund_manager failed: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
