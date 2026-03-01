# -*- coding: utf-8 -*-
"""
生产级每日交易循环：拉数据 → 策略信号 → 组合分配 → 风控 → 执行。
可配合 cron / supervisor / pm2 运行。
"""
from __future__ import annotations
import logging
import os
import sys
import time
from datetime import datetime, timedelta

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_daily_cycle(symbols: list[str] | None = None) -> dict:
    """
    单次日频闭环：使用 TradingEngine + 龙头/趋势/均值策略 + AI 权重 + 风控 + SimBroker。
    返回 engine.run_daily 结果。
    """
    from backend.engine import TradingEngine
    from backend.strategy.dragon import DragonStrategy
    from backend.strategy.trend import TrendStrategy
    from backend.strategy.mean_reversion import MeanReversion
    from backend.portfolio.production_allocator import ProductionAllocator
    from backend.risk.risk_engine import RiskEngine
    from backend.broker.sim import SimBroker
    from backend.ai.fund_manager import AIFundManager
    from data.data_loader import load_kline

    symbols = symbols or ["000001", "600519", "000858"]
    end = datetime.now().date()
    start = (end - timedelta(days=120)).strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    # 市场数据：symbols -> df, prices, total_asset, strategy_weights
    market_data = {"symbols": {}, "prices": {}, "total_asset": 1000000.0, "positions": {}}
    for code in symbols[:30]:
        try:
            df = load_kline(code, start, end_str, source="database")
            if df is not None and len(df) >= 20:
                market_data["symbols"][code] = df
                close = df["close"] if "close" in df.columns else df.get("收盘", df.iloc[:, 3])
                if close is not None and len(close) > 0:
                    market_data["prices"][code] = float(close.iloc[-1])
        except Exception:
            continue

    mgr = AIFundManager()
    regime = "sideways"
    if market_data["symbols"]:
        first_df = next(iter(market_data["symbols"].values()), None)
        if first_df is not None and len(first_df) >= 60:
            regime = mgr.detect_market_regime({"df": first_df})
    market_data["strategy_weights"] = mgr.decide_weights(regime)

    strategies = [
        ("dragon", DragonStrategy()),
        ("trend", TrendStrategy()),
        ("mean", MeanReversion()),
    ]
    portfolio = ProductionAllocator(total_asset=market_data["total_asset"], max_single_weight=0.2)
    risk = RiskEngine(max_single_weight=0.2, max_drawdown=0.15)
    broker = SimBroker(initial_cash=market_data["total_asset"])

    engine = TradingEngine(broker=broker, strategies=strategies, portfolio=portfolio, risk=risk)
    result = engine.run_daily(market_data)
    logger.info("run_daily: signals=%d orders=%d safe=%d sent=%d",
                len(result.get("signals", [])), len(result.get("orders", [])),
                len(result.get("safe_orders", [])), len(result.get("sent", [])))
    return result


def main_loop(interval_seconds: int = 60):
    """循环执行：run_daily_cycle 后 sleep。生产建议用 cron 定时调 run_daily_cycle。"""
    while True:
        try:
            run_daily_cycle()
        except Exception as e:
            logger.exception("trading_loop error: %s", e)
        time.sleep(interval_seconds)


if __name__ == "__main__":
    run_daily_cycle()
    # 若需常驻： main_loop(interval_seconds=3600)
