# -*- coding: utf-8 -*-
"""
AI 基金经理主调度服务（多策略版）：每日自动运行全流程并写日志。
新流程：1.获取数据 2.多策略生成信号 3.AI策略评分 4.资金分配 5.组合生成 6.风控检查 7.执行交易 8.保存日志
"""
from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ai_trading")


def _get_data_engine():
    try:
        from backend.data.duckdb_engine import get_engine
        e = get_engine()
        if e is not None:
            return e
    except Exception:
        pass
    try:
        from database.duckdb_backend import get_db_backend
        return get_db_backend()
    except Exception:
        return None


def run_daily_trading(
    symbols: Optional[List[str]] = None,
    max_stocks: int = 10,
    broker_mode: str = "simulation",
) -> Dict[str, Any]:
    """
    多策略版每日交易：获取数据 → 多策略信号 → AI策略评分 → 资金分配 → 组合生成 → 风控 → 执行 → 日志。
    """
    result = {
        "regime": "sideways",
        "signals_by_strategy": {},
        "candidates": [],
        "strategy_weights": {},
        "capital_weights": {},
        "portfolio": [],
        "orders": [],
        "logs": [],
        "error": None,
    }
    engine = _get_data_engine()
    if engine is None:
        logger.error("无数据引擎")
        result["error"] = "无数据引擎"
        return result

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")
    if symbols is None:
        stocks = engine.get_stocks()
        symbols = [s[0] for s in stocks[:300]]
    if not symbols:
        result["error"] = "无标的"
        return result

    # 1. 获取数据
    logger.info("1. 获取数据")
    market_data: Dict[str, pd.DataFrame] = {}
    prices: Dict[str, float] = {}
    for sym in symbols:
        try:
            df = engine.get_daily_bars(sym, start_date, end_date)
            if df is None or len(df) < 30:
                continue
            market_data[sym] = df
            prices[sym] = float(df["close"].iloc[-1])
        except Exception:
            continue
    if not market_data:
        result["error"] = "无行情数据"
        return result
    logger.info("标的数: %s", len(market_data))

    # 2. 多策略生成信号
    logger.info("2. 多策略生成信号")
    from backend.ai.strategy_manager import StrategyManager
    strategy_mgr = StrategyManager()
    signals_by_strategy = strategy_mgr.collect_signals(market_data)
    result["signals_by_strategy"] = {k: len(v) for k, v in signals_by_strategy.items()}
    candidates = strategy_mgr.get_candidate_pool(signals_by_strategy, min_confidence=0.5, min_strategies_buy=1)
    result["candidates"] = candidates[:20]
    logger.info("候选数: %s", len(candidates))

    # 3. AI 策略评分（无历史表现时用等权）
    logger.info("3. AI 策略评分")
    from backend.ai.strategy_scorer import StrategyScorer, compute_strategy_weights
    strategy_ids = list(signals_by_strategy.keys())
    perfs = {sid: {"return": 0.0, "sharpe": 0.3, "max_drawdown": 0.2, "win_rate": 0.5, "stability": 0.6} for sid in strategy_ids}
    strategy_weights = compute_strategy_weights(perfs, "score_based")
    result["strategy_weights"] = strategy_weights

    # 4. 资金分配
    logger.info("4. 资金分配")
    from backend.ai.capital_allocator import CapitalAllocator
    allocator = CapitalAllocator(method="equal_weight")
    capital_weights = allocator.allocate(strategy_ids, strategy_weights=strategy_weights)
    result["capital_weights"] = capital_weights

    # 5. 组合生成（含风控）
    logger.info("5. 组合生成与风控")
    from backend.ai.market_regime import detect_regime
    from backend.ai.risk_controller import RiskController
    from backend.ai.portfolio_builder import build_portfolio
    market_df = pd.concat(list(market_data.values())[:1], axis=0) if market_data else pd.DataFrame()
    if len(market_df) < 20 and market_data:
        market_df = list(market_data.values())[0]
    regime = detect_regime(market_df)
    result["regime"] = regime
    risk = RiskController()
    from backend.execution.broker_api import BrokerAPI
    from backend.execution.position_manager import PositionManager
    broker = BrokerAPI(mode=broker_mode)
    broker.connect()
    total_asset = broker.get_balance().get("total_asset", 1000000.0)
    portfolio = build_portfolio(
        candidates,
        strategy_weights,
        capital_weights,
        total_asset,
        prices,
        regime,
        risk,
        max_stocks=max_stocks,
        max_weight_per_stock=0.20,
    )
    result["portfolio"] = portfolio
    logger.info("组合标的数: %s", len(portfolio))

    # 6. 风控已在 build_portfolio 中；7. 执行交易 8. 保存日志
    logger.info("6-8. 风控检查、执行交易、保存日志")
    from backend.execution.order_manager import OrderManager
    order_mgr = OrderManager(broker)
    for item in portfolio:
        sym = item.get("symbol")
        qty = item.get("qty", 0)
        side = (item.get("side") or "buy").upper()
        if side != "BUY" or qty < 100:
            continue
        p = prices.get(sym)
        if p is None or p <= 0:
            continue
        order = order_mgr.place_order(sym, qty, "BUY", price=p)
        if order:
            result["orders"].append(order)
            result["logs"].append(f"下单 {sym} BUY {qty} @ {p}")
            try:
                from backend.data.duckdb_engine import get_engine
                eng = get_engine()
                if eng and hasattr(eng, "log_trade"):
                    eng.log_trade(sym, "BUY", qty, p)
            except Exception:
                pass
    logger.info("下单数: %s", len(result["orders"]))
    return result
