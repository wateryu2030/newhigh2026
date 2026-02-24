# -*- coding: utf-8 -*-
"""
参数优化器：遗传算法 GA，流程为生成种群 → 交叉 → 变异 → 选择。
目标：最大化收益、夏普，最小化回撤（通过统一评分体现）。
"""
from __future__ import annotations
import copy
import logging
import random
from typing import Any, Callable, Dict, List, Tuple

logger = logging.getLogger(__name__)


class ParameterOptimizer:
    """
    遗传算法优化策略参数。
    适应度由外部传入（通常为回测后的评分：0.4*return + 0.3*sharpe - 0.3*drawdown）。
    """

    def __init__(
        self,
        param_space: Dict[str, List[Any]],
        population_size: int = 20,
        generations: int = 10,
        crossover_rate: float = 0.7,
        mutation_rate: float = 0.2,
        elite_keep: int = 2,
        seed: int | None = None,
    ) -> None:
        self.param_space = dict(param_space)
        self.population_size = max(4, population_size)
        self.generations = generations
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.elite_keep = max(0, elite_keep)
        if seed is not None:
            random.seed(seed)

    def _random_individual(self) -> Dict[str, Any]:
        """在参数空间内随机生成一个个体（一组参数）。"""
        ind: Dict[str, Any] = {}
        for key, bounds in self.param_space.items():
            if not bounds or len(bounds) < 2:
                continue
            low, high = bounds[0], bounds[1]
            if isinstance(low, int) and isinstance(high, int):
                ind[key] = random.randint(int(low), int(high))
            else:
                ind[key] = round(low + random.random() * (high - low), 4)
        return ind

    def _generate_population(self) -> List[Dict[str, Any]]:
        """生成初始种群。"""
        return [self._random_individual() for _ in range(self.population_size)]

    def _crossover(
        self,
        parent_a: Dict[str, Any],
        parent_b: Dict[str, Any],
    ) -> Dict[str, Any]:
        """算术交叉：子代 = parent_a * (1-t) + parent_b * t，t 随机。"""
        child: Dict[str, Any] = {}
        for key in parent_a:
            if key not in parent_b or random.random() > self.crossover_rate:
                child[key] = copy.deepcopy(parent_a[key])
                continue
            bounds = self.param_space.get(key, [0, 1])
            if not bounds or len(bounds) < 2:
                child[key] = copy.deepcopy(parent_a[key])
                continue
            low, high = float(bounds[0]), float(bounds[1])
            t = random.random()
            v = (1 - t) * float(parent_a[key]) + t * float(parent_b[key])
            v = max(low, min(high, v))
            child[key] = int(round(v)) if isinstance(bounds[0], int) else round(v, 4)
        return child

    def _mutate(self, individual: Dict[str, Any]) -> Dict[str, Any]:
        """以 mutation_rate 对每个参数做随机扰动。"""
        mutated = copy.deepcopy(individual)
        for key, bounds in self.param_space.items():
            if not bounds or len(bounds) < 2 or random.random() > self.mutation_rate:
                continue
            low, high = bounds[0], bounds[1]
            if isinstance(low, int) and isinstance(high, int):
                delta = random.randint(-max(1, (high - low) // 5), max(1, (high - low) // 5))
                mutated[key] = max(int(low), min(int(high), mutated.get(key, low) + delta))
            else:
                delta = (high - low) * 0.2 * (random.random() - 0.5)
                mutated[key] = round(max(low, min(high, mutated.get(key, low) + delta)), 4)
        return mutated

    def _select(
        self,
        population: List[Dict[str, Any]],
        fitnesses: List[float],
        k: int,
    ) -> List[Dict[str, Any]]:
        """按适应度从高到低选择前 k 个个体（锦标赛式：取 fitness 大的）。"""
        indexed = list(zip(fitnesses, population))
        indexed.sort(key=lambda x: (-x[0], random.random()))
        return [p for _, p in indexed[:k]]

    def optimize(
        self,
        fitness_fn: Callable[[Dict[str, Any]], float],
    ) -> Tuple[Dict[str, Any], float]:
        """
        执行遗传算法优化。
        :param fitness_fn: 接受参数字典，返回适应度（越大越好）。
        :return: (最佳参数字典, 最佳适应度)
        """
        population = self._generate_population()
        best_ind: Dict[str, Any] = {}
        best_fit: float = -float("inf")

        for gen in range(self.generations):
            fitnesses = [fitness_fn(ind) for ind in population]
            for i, fit in enumerate(fitnesses):
                if fit > best_fit:
                    best_fit = fit
                    best_ind = copy.deepcopy(population[i])

            # 精英保留
            elites = self._select(population, fitnesses, self.elite_keep)
            next_pop: List[Dict[str, Any]] = list(elites)

            # 选择、交叉、变异直至补满种群
            selected = self._select(population, fitnesses, self.population_size)
            while len(next_pop) < self.population_size:
                a, b = random.sample(selected, 2)
                child = self._crossover(a, b)
                child = self._mutate(child)
                next_pop.append(child)

            population = next_pop[: self.population_size]
            logger.info("GA gen %d/%d best_fit=%.4f", gen + 1, self.generations, best_fit)

        return best_ind, best_fit
