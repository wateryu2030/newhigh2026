#!/usr/bin/env python3
"""
策略自动化（量化运维）：
  --seed   若 strategy_market 条目过少，登记 ai_fusion / market_agg / shareholder_chip 基线；
  --evolve 跑一轮 OpenClaw 进化（依赖库中已有 trade_signals 与各 strategy_id 回测可对齐标的）。

典型用法（定时任务）：
  python scripts/strategy_automation.py --all
  NEWHIGH_AUTO_STRATEGY_MARKET=1  # 随 system_runner 每轮自动 seed（见 strategy_orchestrator）
"""

from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from system_core.repo_paths import prepend_repo_sources  # noqa: E402

prepend_repo_sources(ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="策略市场基线登记 + OpenClaw 进化一轮")
    parser.add_argument("--seed", action="store_true", help="登记 strategy_market 基线（若过少）")
    parser.add_argument("--evolve", action="store_true", help="执行 run_evolution_cycle")
    parser.add_argument("--all", action="store_true", help="等价于 --seed --evolve")
    parser.add_argument("--population-limit", type=int, default=10)
    parser.add_argument("--symbol", type=str, default="000001.SZ", help="无信号标的时的回测 fallback")
    args = parser.parse_args()
    do_seed = args.seed or args.all
    do_evolve = args.evolve or args.all
    if not do_seed and not do_evolve:
        parser.error("请指定 --seed、--evolve 或 --all")

    if do_seed:
        from data_pipeline.strategy_market_writer import ensure_baseline_strategy_market_rows

        n = ensure_baseline_strategy_market_rows(min_rows=2)
        print("ensure_baseline_strategy_market_rows:", n, "insert attempts (if table was sparse)")

    if do_evolve:
        for _d in ["openclaw_engine", "backtest-engine/src", "data-pipeline/src", "core/src"]:
            _p = os.path.join(ROOT, _d)
            if os.path.isdir(_p) and _p not in sys.path:
                sys.path.insert(0, _p)
        from openclaw_engine import run_evolution_cycle

        out = run_evolution_cycle(
            population_limit=args.population_limit,
            symbol=args.symbol,
        )
        print(json.dumps(out, ensure_ascii=False, indent=2, default=str))

    return 0


if __name__ == "__main__":
    sys.exit(main())
