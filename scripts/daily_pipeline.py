#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机构级每日流水线：OpenClaw 调度入口。
Step 1~11：更新数据 → 情绪周期 → 扫描 → 评分 → 龙头池 → 交易计划 → 记录 → 更新权重。
输出：daily_report.json（emotion_cycle, dragon_pool, buy_list, sell_list, risk_level）。

用法：
  python scripts/daily_pipeline.py [--output path] [--skip-fetch]
  --output  默认 ./daily_report.json
  --skip-fetch  跳过 Step1 数据更新（数据已由 cron 更新时使用）
"""
from __future__ import annotations
import argparse
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
try:
    from core.log_config import init_logging
    init_logging(level=logging.INFO)
except Exception:
    pass
logger = logging.getLogger(__name__)


def step1_update_market_data() -> bool:
    """Step 1: 更新市场数据（日线等）。"""
    try:
        from scripts.daily_fetch_after_close import run_incremental_fetch, sync_new_stocks
        sync_new_stocks(delay_seconds=0.1)
        run_incremental_fetch(delay_seconds=0.08)
        return True
    except Exception as e:
        logger.warning("Step1 更新市场数据失败: %s", e)
        return False


def step2_update_fund_data() -> bool:
    """Step 2: 更新资金数据（可在此调用 akshare 资金流缓存等）。"""
    # 当前为实时查询，无独立缓存步骤
    return True


def step3_update_policy_data() -> Dict[str, Any]:
    """Step 3: 更新政策数据。"""
    try:
        from core.policy_engine import get_policy_signal
        return get_policy_signal()
    except Exception as e:
        logger.debug("Step3 policy: %s", e)
        return {"bias": "neutral", "score": 50, "highlights": []}


def step4_emotion_cycle(market_data: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Step 4: 计算情绪周期。"""
    try:
        from core.sentiment_engine import get_emotion_state
        return get_emotion_state(market_data=market_data)
    except Exception as e:
        logger.debug("Step4 emotion: %s", e)
        return {"emotion_cycle": "复苏", "suggested_position_pct": 0.4, "description": "—"}


def step5_run_scanner(limit: int = 2000) -> List[Dict[str, Any]]:
    """Step 5: 运行市场扫描器。"""
    try:
        from core.market_scanner import run_scan
        return run_scan(strategy_id="breakout", limit=limit)
    except Exception as e:
        logger.warning("Step5 扫描失败: %s", e)
        return []


def step6_scoring(
    scan_results: List[Dict[str, Any]],
    emotion_cycle: str,
    policy_score: float,
) -> List[Dict[str, Any]]:
    """Step 6: 计算综合评分。"""
    try:
        from core.fund_engine import rank_by_fund
        from core.scoring_engine import score_candidates
    except ImportError as e:
        logger.warning("Step6 scoring import: %s", e)
        return scan_results[:50]
    symbols = [r.get("symbol") or (r.get("order_book_id") or "").split(".")[0] for r in scan_results]
    fund_rank = rank_by_fund(symbols, days=5)
    fund_map = {r["symbol"]: r["score"] for r in fund_rank}
    sentiment_score = 70.0 if emotion_cycle == "加速期" else (35.0 if emotion_cycle in ("冰点", "退潮") else 50.0)
    return score_candidates(
        scan_results,
        fund_scores=fund_map,
        sentiment_score=sentiment_score,
        policy_score=policy_score,
    )


def step7_dragon_pool(scored: List[Dict[str, Any]], top_n: int = 30) -> List[str]:
    """Step 7: 输出龙头池（代码列表）。"""
    pool: List[str] = []
    seen = set()
    for r in scored[: top_n * 2]:
        sym = r.get("symbol") or r.get("order_book_id") or ""
        code = sym.split(".")[0] if "." in sym else sym
        if code and code not in seen:
            seen.add(code)
            pool.append(code)
            if len(pool) >= top_n:
                break
    return pool


def step8_trade_plan(
    dragon_pool: List[str],
    current_holdings: List[str],
    emotion_cycle: str,
    max_buy: int = 10,
) -> tuple[List[str], List[str]]:
    """
    Step 8: 生成交易计划。
    简化逻辑：龙头池中未持仓的取前 max_buy 只作为 buy_list；持仓中不在龙头池的作为 sell_list 候选（实际卖出可由风控与人工确认）。
    """
    pool_set = set(dragon_pool)
    hold_set = set(current_holdings)
    buy_list = [s for s in dragon_pool if s not in hold_set][:max_buy]
    sell_list = [s for s in hold_set if s not in pool_set]
    return buy_list, sell_list


def step9_execute_trades(buy_list: List[str], sell_list: List[str], dry_run: bool = True) -> Dict[str, Any]:
    """Step 9: 执行交易。默认 dry_run 仅记录不真实下单。"""
    if dry_run:
        return {"dry_run": True, "buy_count": len(buy_list), "sell_count": len(sell_list)}
    # 真实执行时可调用 trading.OrderExecutor
    return {"dry_run": False, "buy_count": len(buy_list), "sell_count": len(sell_list)}


def step10_record_results(report: Dict[str, Any], output_path: str) -> None:
    """Step 10: 记录结果，写入 daily_report.json。"""
    report["updated_at"] = datetime.now().isoformat()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    logger.info("已写入 %s", output_path)


def step11_update_weights(weights_path: str | None = None) -> Dict[str, float]:
    """Step 11: 更新策略权重（需有历史收益数据；无则返回默认权重）。"""
    try:
        from ai.weight_optimizer import optimize_weights, STRATEGY_IDS
        # 若有持久化的 strategy_returns 可在此加载
        if weights_path and os.path.exists(weights_path):
            with open(weights_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            strategy_returns = data.get("strategy_returns", {})
            if strategy_returns:
                return optimize_weights(strategy_returns)
        from portfolio.allocation_engine import DEFAULT_STRATEGY_WEIGHTS
        return dict(DEFAULT_STRATEGY_WEIGHTS)
    except Exception as e:
        logger.debug("Step11 weights: %s", e)
        return {"dragon_strategy": 0.4, "trend_strategy": 0.3, "mean_reversion": 0.3}


def get_risk_level(emotion_cycle: str, max_drawdown: float | None = None) -> str:
    """与 portfolio.risk_controller 一致。"""
    try:
        from portfolio.risk_controller import get_risk_level as _get
        return _get(emotion_cycle=emotion_cycle, max_drawdown=max_drawdown)
    except Exception:
        if emotion_cycle in ("冰点", "退潮", "过热"):
            return "中等"
        return "低"


def main() -> int:
    parser = argparse.ArgumentParser(description="机构级每日流水线 -> daily_report.json")
    parser.add_argument("--output", default="daily_report.json", help="输出 JSON 路径")
    parser.add_argument("--skip-fetch", action="store_true", help="跳过数据更新")
    parser.add_argument("--dry-run", action="store_true", help="不执行真实交易")
    parser.add_argument("--limit", type=int, default=2000, help="扫描股票数量上限")
    args = parser.parse_args()
    output_path = args.output
    if not os.path.isabs(output_path):
        output_path = os.path.join(_ROOT, output_path)

    logger.info("开始每日流水线")
    if not args.skip_fetch:
        step1_update_market_data()
    step2_update_fund_data()
    policy = step3_update_policy_data()
    policy_score = float(policy.get("score", 50))
    emotion = step4_emotion_cycle()
    emotion_cycle = emotion.get("emotion_cycle", "复苏")
    scan_results = step5_run_scanner(limit=args.limit)
    scored = step6_scoring(scan_results, emotion_cycle, policy_score)
    dragon_pool = step7_dragon_pool(scored, top_n=30)
    # 当前持仓：可从 broker/数据库读取，此处简化为空
    current_holdings: List[str] = []
    try:
        from backend.trading.broker_interface import Broker
        b = Broker(mode="simulation")
        b.connect()
        pos = b.get_positions()
        current_holdings = [k.split(".")[0] for k in pos if pos.get(k)]
    except Exception:
        pass
    buy_list, sell_list = step8_trade_plan(dragon_pool, current_holdings, emotion_cycle)
    step9_execute_trades(buy_list, sell_list, dry_run=args.dry_run)
    risk_level = get_risk_level(emotion_cycle, max_drawdown=None)
    weights = step11_update_weights()

    report: Dict[str, Any] = {
        "emotion_cycle": emotion_cycle,
        "dragon_pool": dragon_pool,
        "buy_list": buy_list,
        "sell_list": sell_list,
        "risk_level": risk_level,
        "strategy_weights": weights,
        "suggested_position_pct": emotion.get("suggested_position_pct"),
    }
    step10_record_results(report, output_path)
    logger.info("流水线完成: emotion=%s risk=%s dragon_pool=%d", emotion_cycle, risk_level, len(dragon_pool))
    return 0


if __name__ == "__main__":
    sys.exit(main())
