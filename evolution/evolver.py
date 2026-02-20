# -*- coding: utf-8 -*-
"""
策略进化器：维护种群，按适应度（回测夏普/收益）选择、变异、交叉，逐代进化。
"""
import random
from typing import Callable, List, Optional, Tuple
from .strategy_gene import StrategyGene, mutate, crossover


def default_fitness(gene: StrategyGene) -> float:
    """默认适应度：随机数模拟回测结果，实际应替换为真实回测（返回夏普或收益）。"""
    return random.gauss(0.5, 0.3)


class StrategyEvolver:
    """
    种群进化：evaluate 函数接受 StrategyGene，返回适应度（越高越好）。
    每代保留 top_k，再通过变异与交叉生成新种群。
    """

    def __init__(
        self,
        population_size: int = 50,
        top_k: int = 10,
        mutate_rate: float = 0.2,
        fitness_fn: Optional[Callable[[StrategyGene], float]] = None,
    ):
        self.population_size = population_size
        self.top_k = top_k
        self.mutate_rate = mutate_rate
        self.fitness_fn = fitness_fn or default_fitness
        self.population: List[StrategyGene] = []
        self.generation = 0

    def _init_population(self, schema: Optional[dict] = None) -> None:
        schema = schema or {}
        self.population = [
            StrategyGene(schema=schema or None) for _ in range(self.population_size)
        ]

    def run_generation(self, schema: Optional[dict] = None) -> Tuple[StrategyGene, float]:
        """
        运行一代：若种群为空则初始化；否则评估、排序、选择 top_k，再变异+交叉填满 population_size。
        :return: (当前代最优基因, 其适应度)
        """
        if not self.population:
            self._init_population(schema)
        scored: List[Tuple[float, StrategyGene]] = []
        for g in self.population:
            try:
                f = self.fitness_fn(g)
            except Exception:
                f = -1e9
            scored.append((f, g))
        scored.sort(key=lambda x: -x[0])
        best_gene, best_fitness = scored[0][1], scored[0][0]
        elites = [g for _, g in scored[: self.top_k]]
        next_gen: List[StrategyGene] = list(elites)
        while len(next_gen) < self.population_size:
            a, b = random.sample(elites, 2)
            child = crossover(a, b)
            child = mutate(child, rate=self.mutate_rate)
            next_gen.append(child)
        self.population = next_gen[: self.population_size]
        self.generation += 1
        return best_gene, best_fitness

    def evolve(self, n_generations: int = 20, schema: Optional[dict] = None) -> StrategyGene:
        """进化 n 代，返回全局最优基因。"""
        best_ever = None
        best_f = -1e9
        for _ in range(n_generations):
            gene, f = self.run_generation(schema=schema)
            if f > best_f:
                best_f = f
                best_ever = gene
        return best_ever or self.population[0]
