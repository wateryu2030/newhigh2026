# -*- coding: utf-8 -*-
"""
AI 基金经理核心：串联市场判断 → 选股 → 风险评估 → 资金分配 → 生成交易指令。
不破坏现有交易代码，输出 trade_orders.json 供 execution_engine 执行。
"""
from __future__ import annotations
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _default_orders_path() -> str:
    return os.path.join(_ROOT, "output", "trade_orders.json")


class AIManager:
    """
    AI 基金经理：模块化流程，支持未来替换为 AI 模型。
    1. MarketAgent 市场判断
    2. StockAgent 选股评分
    3. RiskAgent 风险评估
    4. PortfolioOptimizer 资金分配
    5. 生成交易指令并写入 trade_orders.json
    """

    def __init__(
        self,
        capital: float = 1_000_000.0,
        portfolio_method: str = "equal_weight",
        top_n: int = 10,
    ) -> None:
        self.capital = capital
        self.portfolio_method = portfolio_method
        self.top_n = top_n
        self._market_agent = None
        self._stock_agent = None
        self._risk_agent = None
        self._optimizer = None

    @property
    def market_agent(self):
        if self._market_agent is None:
            from .agents.market_agent import MarketAgent
            self._market_agent = MarketAgent(index_days=120)
        return self._market_agent

    @property
    def stock_agent(self):
        if self._stock_agent is None:
            from .agents.stock_agent import StockAgent
            self._stock_agent = StockAgent(lookback_days=120, max_stocks=200)
        return self._stock_agent

    @property
    def risk_agent(self):
        if self._risk_agent is None:
            from .agents.risk_agent import RiskAgent
            self._risk_agent = RiskAgent(default_stop_loss=0.08)
        return self._risk_agent

    @property
    def optimizer(self):
        if self._optimizer is None:
            from .portfolio_optimizer import PortfolioOptimizer
            self._optimizer = PortfolioOptimizer(
                method=self.portfolio_method,
                top_n=self.top_n,
                max_position=0.9,
            )
        return self._optimizer

    def run(
        self,
        index_df: Optional[Any] = None,
        candidate_symbols: Optional[List[str]] = None,
        orders_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        执行完整流程，生成交易指令并写入 JSON。
        :param index_df: 可选指数 K 线；None 则 MarketAgent 内部从 DuckDB 加载。
        :param candidate_symbols: 可选选股候选列表；None 则 StockAgent 从库中取。
        :param orders_path: 输出路径；None 则 output/trade_orders.json。
        :return: 汇总结果 {market, stock_scores, risk, positions, orders_path, orders_count}
        """
        result: Dict[str, Any] = {
            "market": {},
            "stock_scores": [],
            "risk": {},
            "positions": {},
            "orders_path": None,
            "orders_count": 0,
            "timestamp": datetime.now().isoformat(),
        }
        orders_path = orders_path or _default_orders_path()

        try:
            # 1. 市场判断
            market_out = self.market_agent.run(index_df=index_df)
            result["market"] = market_out
            logger.info("Market: trend=%s risk_level=%s recommended_position=%s",
                        market_out.get("market_trend"), market_out.get("risk_level"), market_out.get("recommended_position"))

            # 2. 选股评分
            stock_scores = self.stock_agent.run(symbols=candidate_symbols, stock_limit=self.top_n * 3)
            result["stock_scores"] = stock_scores[: self.top_n * 2]
            if not stock_scores:
                logger.warning("No stock scores, skip allocation")
                risk_out = self.risk_agent.run(
                    market_risk_level=result["market"].get("risk_level", 0.5),
                    market_trend=result["market"].get("market_trend", "neutral"),
                )
                result["risk"] = risk_out
                os.makedirs(os.path.dirname(orders_path) or ".", exist_ok=True)
                with open(orders_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "timestamp": result["timestamp"],
                        "capital": self.capital,
                        "market": result["market"],
                        "risk": risk_out,
                        "positions": {},
                        "orders": [],
                    }, f, ensure_ascii=False, indent=2)
                result["orders_path"] = orders_path
                logger.info("Orders written: %s (0 orders, no candidates)", orders_path)
                return result

            # 3. 风险评估（用市场风险与趋势约束仓位）
            risk_out = self.risk_agent.run(
                market_risk_level=market_out.get("risk_level", 0.5),
                market_trend=market_out.get("market_trend", "neutral"),
            )
            result["risk"] = risk_out
            # 建议总仓位由市场 agent 的 recommended_position 与 risk 的 max_position 取小
            recommended_total = min(
                market_out.get("recommended_position", 0.7),
                risk_out.get("max_position", 0.7),
            )

            # 4. 资金分配
            positions = self.optimizer.run(
                stock_scores=stock_scores,
                risk_params={**risk_out, "max_position": recommended_total},
            )
            result["positions"] = positions

            # 5. 生成交易指令（目标金额 + 止损）
            orders = self._build_orders(positions, risk_out.get("stop_loss", 0.08))
            result["orders_count"] = len(orders)

            os.makedirs(os.path.dirname(orders_path) or ".", exist_ok=True)
            with open(orders_path, "w", encoding="utf-8") as f:
                json.dump({
                    "timestamp": result["timestamp"],
                    "capital": self.capital,
                    "market": market_out,
                    "risk": risk_out,
                    "positions": positions,
                    "orders": orders,
                }, f, ensure_ascii=False, indent=2)
            result["orders_path"] = orders_path
            logger.info("Orders written: %s (%d orders)", orders_path, len(orders))

        except Exception as e:
            logger.exception("AIManager run error: %s", e)
            result["error"] = str(e)
        return result

    def _build_orders(
        self,
        positions: Dict[str, float],
        stop_loss: float,
    ) -> List[Dict[str, Any]]:
        """将仓位权重转为订单列表：symbol, side, weight, target_value, stop_loss。"""
        orders = []
        for code, weight in positions.items():
            if weight <= 0:
                continue
            target_value = self.capital * weight
            orders.append({
                "symbol": code,
                "side": "BUY",
                "weight": weight,
                "target_value": round(target_value, 2),
                "stop_loss": stop_loss,
            })
        return orders
