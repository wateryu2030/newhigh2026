# -*- coding: utf-8 -*-
"""
进化管理器：流程为 生成策略 → 优化参数 → 回测 → 评分 → 保存最佳；支持循环进化。
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

from .strategy_generator import StrategyGenerator
from .parameter_optimizer import ParameterOptimizer
from .strategy_evaluator import StrategyEvaluator
from .strategy_repository import StrategyRepository
from .backtest_engine import run_backtest

logger = logging.getLogger(__name__)


class EvolutionManager:
    """串联：生成 → 优化 → 回测 → 评分 → 保存，支持多轮进化。"""

    def __init__(
        self,
        stock_code: str = "000001.XSHE",
        start_date: str = "2024-01-01",
        end_date: str = "2024-12-31",
        timeframe: str = "D",
        population_size: int = 16,
        generations: int = 8,
        evolution_rounds: int = 3,
        repository: Optional[StrategyRepository] = None,
    ) -> None:
        self.stock_code = stock_code
        self.start_date = start_date
        self.end_date = end_date
        self.timeframe = timeframe
        self.population_size = population_size
        self.generations = generations
        self.evolution_rounds = evolution_rounds
        self.generator = StrategyGenerator()
        self.evaluator = StrategyEvaluator()
        self.repository = repository or StrategyRepository()

    def _fitness_for_ga(self, strategy_id: str, params: Dict[str, Any]) -> float:
        """供 GA 调用的适应度：回测 + 评分。"""
        metrics = run_backtest(
            strategy_id=strategy_id,
            params=params,
            stock_code=self.stock_code,
            start_date=self.start_date,
            end_date=self.end_date,
            timeframe=self.timeframe,
        )
        return self.evaluator.evaluate(metrics)

    def run_one_evolution(self) -> Dict[str, Any]:
        """
        执行一轮进化：生成一条策略 → GA 优化其参数 → 回测 → 评分 → 保存。
        :return: 本轮最佳策略信息（含 score, params 等）
        """
        config = self.generator.generate_one()
        strategy_id = config.get("strategy_id", "ma_cross")
        strategy_type = config.get("type", strategy_id)
        param_space = self.generator.get_param_space(strategy_id)
        if not param_space:
            logger.warning("No param space for %s, skip evolution", strategy_id)
            return {"strategy_id": strategy_id, "score": 0.0, "params": config.get("params", {})}

        optimizer = ParameterOptimizer(
            param_space=param_space,
            population_size=self.population_size,
            generations=self.generations,
            crossover_rate=0.7,
            mutation_rate=0.2,
            elite_keep=2,
        )

        def fitness_fn(ind: Dict[str, Any]) -> float:
            return self._fitness_for_ga(strategy_id, ind)

        best_params, best_fit = optimizer.optimize(fitness_fn)

        # 最终回测取 return/sharpe/drawdown
        metrics = run_backtest(
            strategy_id=strategy_id,
            params=best_params,
            stock_code=self.stock_code,
            start_date=self.start_date,
            end_date=self.end_date,
            timeframe=self.timeframe,
        )

        self.repository.save(
            strategy_id=strategy_id,
            strategy_type=strategy_type,
            params=best_params,
            score=best_fit,
            return_rate=metrics.get("return", 0.0),
            sharpe=metrics.get("sharpe", 0.0),
            drawdown=metrics.get("drawdown", 0.0),
            meta={"stock_code": self.stock_code, "start_date": self.start_date, "end_date": self.end_date},
        )

        result = {
            "strategy_id": strategy_id,
            "strategy_type": strategy_type,
            "params": best_params,
            "score": best_fit,
            "return": metrics.get("return", 0.0),
            "sharpe": metrics.get("sharpe", 0.0),
            "drawdown": metrics.get("drawdown", 0.0),
        }
        logger.info("Evolution round best: %s", result)
        return result

    def run(self) -> List[Dict[str, Any]]:
        """
        执行多轮进化，每轮生成并优化一条策略，保存到仓库。
        :return: 每轮最佳结果列表
        """
        results: List[Dict[str, Any]] = []
        for r in range(self.evolution_rounds):
            logger.info("Evolution round %d/%d", r + 1, self.evolution_rounds)
            try:
                best = self.run_one_evolution()
                results.append(best)
            except Exception as e:
                logger.exception("Evolution round failed: %s", e)
        best_saved = self.repository.get_best(top_n=5)
        logger.info("Top 5 strategies in repository: %s", best_saved)
        return results
