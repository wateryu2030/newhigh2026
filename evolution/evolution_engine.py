# -*- coding: utf-8 -*-
"""
自进化引擎：循环 生成策略 → 回测 → 评分 → 保留最优 → 淘汰差策略，实现 AI 基金经理式进化。
"""
from __future__ import annotations
import pandas as pd
from typing import Any, Callable, Dict, List, Optional, Tuple

from .strategy_generator import StrategyGenerator
from .strategy_runner import StrategyRunner
from .strategy_evaluator import StrategyEvaluator


class EvolutionEngine:
    """
    自进化引擎：使用 LLM 生成策略，回测评估，保留高分策略。
    """

    def __init__(
        self,
        generator: Optional[StrategyGenerator] = None,
        runner: Optional[StrategyRunner] = None,
        evaluator: Optional[StrategyEvaluator] = None,
        min_score: float = -1e9,
    ):
        self.generator = generator or StrategyGenerator()
        self.runner = runner or StrategyRunner()
        self.evaluator = evaluator or StrategyEvaluator()
        self.min_score = min_score
        self.best_strategies: List[Tuple[str, Dict[str, Any]]] = []

    def evolve(
        self,
        idea: str,
        df: pd.DataFrame,
        rounds: int = 10,
        indicators: Optional[List[str]] = None,
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        进化多轮：每轮生成策略 → 运行 → 评估，按 score 排序保留最优。
        :param idea: 策略思想描述
        :param df: 训练期 K 线
        :param rounds: 生成轮数
        :param indicators: 可选指标列表
        :return: [(code, metrics), ...] 按 score 降序，最多前 5
        """
        self.best_strategies = []
        for i in range(rounds):
            try:
                code = self.generator.generate(idea, indicators=indicators)
            except Exception as e:
                continue
            result = self.runner.run(code, df)
            if result.get("error") or result.get("equity") is None:
                continue
            equity = result["equity"]
            df_out = result.get("df")
            metrics = self.evaluator.evaluate(equity, df_with_signals=df_out)
            if metrics["score"] >= self.min_score:
                self.best_strategies.append((code, metrics))
        self.best_strategies.sort(key=lambda x: x[1]["score"], reverse=True)
        return self.best_strategies[:5]
