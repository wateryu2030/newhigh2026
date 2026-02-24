#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 自进化量化交易系统入口：执行策略生成 → 参数优化 → 回测 → 评分 → 保存最佳。
"""
from __future__ import annotations
import argparse
import logging
import os
import sys

_root = os.path.dirname(os.path.abspath(__file__))
os.chdir(_root)
sys.path.insert(0, _root)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="AI 自进化量化：生成策略、优化参数、回测、保存最佳")
    parser.add_argument("--stock", default="000001.XSHE", help="回测标的")
    parser.add_argument("--start", default="2024-01-01", help="回测开始日期")
    parser.add_argument("--end", default="2024-12-31", help="回测结束日期")
    parser.add_argument("--rounds", type=int, default=3, help="进化轮数")
    parser.add_argument("--population", type=int, default=16, help="GA 种群大小")
    parser.add_argument("--generations", type=int, default=8, help="GA 代数")
    args = parser.parse_args()

    from ai_evolution.evolution_manager import EvolutionManager
    from ai_evolution.strategy_repository import StrategyRepository

    repo = StrategyRepository(use_duckdb=True)
    manager = EvolutionManager(
        stock_code=args.stock,
        start_date=args.start,
        end_date=args.end,
        timeframe="D",
        population_size=args.population,
        generations=args.generations,
        evolution_rounds=args.rounds,
        repository=repo,
    )

    logger.info("Start evolution: stock=%s %s~%s rounds=%d", args.stock, args.start, args.end, args.rounds)
    results = manager.run()
    logger.info("Evolution done. Best per round: %s", results)

    best_list = repo.get_best(top_n=5)
    print("\n========== Top 5 策略 ==========")
    for i, s in enumerate(best_list, 1):
        print(f"{i}. {s.get('strategy_id')} type={s.get('strategy_type')} score={s.get('score'):.4f} "
              f"return={s.get('return_rate', 0):.4f} sharpe={s.get('sharpe', 0):.4f} drawdown={s.get('drawdown', 0):.4f}")
        print(f"   params: {s.get('params')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
