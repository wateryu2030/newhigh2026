# -*- coding: utf-8 -*-
"""
生产级遗传算法参数优化模块。
目标：最大化 core.scoring.score_strategy(stats)。
流程：初始化种群 → 适应度评估 → 选择 → 交叉 → 变异 → 精英保留 → 迭代。
"""
import os
import sys
import random
import copy
from typing import Dict, Any, List, Tuple, Optional, Callable

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

from .ga_config import GAConfig


# ---------------------------------------------------------------------------
# 参数空间与个体表示
# ---------------------------------------------------------------------------

def random_params(space: Dict[str, List[float]]) -> Dict[str, Any]:
    """
    在参数空间内随机采样一组参数（整数或浮点）。
    :param space: {"param_name": [min, max]}，min/max 为 int 则采样整数
    """
    params = {}
    for k, v in space.items():
        if not v or len(v) < 2:
            continue
        low, high = float(v[0]), float(v[1])
        if isinstance(v[0], int) and isinstance(v[1], int):
            params[k] = random.randint(int(low), int(high))
        else:
            params[k] = round(low + random.random() * (high - low), 4)
    return params


def _is_int_param(space: Dict[str, List], key: str) -> bool:
    """判断某参数是否为整数类型。"""
    v = space.get(key)
    if not v or len(v) < 2:
        return False
    return isinstance(v[0], int) and isinstance(v[1], int)


def _clip_param(value: float, low: float, high: float, is_int: bool) -> Any:
    """将参数裁剪到 [low, high]，并按类型取整。"""
    v = max(low, min(high, value))
    return int(round(v)) if is_int else round(v, 4)


# ---------------------------------------------------------------------------
# 遗传算子：交叉、变异
# ---------------------------------------------------------------------------

def _crossover(
    parent_a: Dict[str, Any],
    parent_b: Dict[str, Any],
    space: Dict[str, List[float]],
    rate: float,
) -> Dict[str, Any]:
    """
    算术交叉：子代 = parent_a * (1-t) + parent_b * t，t 随机。
    保证子代在空间范围内。
    """
    child = {}
    for k in parent_a:
        if k not in parent_b or random.random() > rate:
            child[k] = copy.deepcopy(parent_a[k])
            continue
        low, high = float(space[k][0]), float(space[k][1])
        t = random.random()
        v = (1 - t) * float(parent_a[k]) + t * float(parent_b[k])
        child[k] = _clip_param(v, low, high, _is_int_param(space, k))
    return child


def _mutate(
    individual: Dict[str, Any],
    space: Dict[str, List[float]],
    rate: float,
    strength: float,
) -> Dict[str, Any]:
    """
    均匀变异：以 probability 对每个基因在范围内随机扰动。
    strength 表示相对范围的比例（如 0.3 表示最多在 30% 范围内扰动）。
    """
    mutant = copy.deepcopy(individual)
    for k, v in space.items():
        if not v or len(v) < 2 or random.random() > rate:
            continue
        if k not in mutant:
            continue
        low, high = float(v[0]), float(v[1])
        span = high - low
        delta = (random.random() * 2 - 1) * strength * span
        new_v = float(mutant[k]) + delta
        mutant[k] = _clip_param(new_v, low, high, _is_int_param(space, k))
    return mutant


# ---------------------------------------------------------------------------
# 选择：锦标赛
# ---------------------------------------------------------------------------

def _tournament_select(
    population: List[Dict[str, Any]],
    fitness: List[float],
    k: int,
) -> Dict[str, Any]:
    """从种群中随机取 k 个个体，返回适应度最高的一个。"""
    idxs = random.sample(range(len(population)), min(k, len(population)))
    best_i = max(idxs, key=lambda i: fitness[i])
    return copy.deepcopy(population[best_i])


# ---------------------------------------------------------------------------
# 主流程：进化
# ---------------------------------------------------------------------------

def optimize_strategy(
    strategy_id: str,
    stock_code: str,
    start_date: str,
    end_date: str,
    param_space: Dict[str, List[float]],
    timeframe: str = "D",
    generations: int = 25,
    population_per_gen: int = 30,
    config: Optional[GAConfig] = None,
) -> Tuple[Dict[str, Any], float, List[Dict[str, Any]]]:
    """
    使用遗传算法搜索使策略评分最高的参数组合。

    :param strategy_id: 策略 id（ma_cross / rsi / macd / breakout）
    :param stock_code: 标的代码
    :param start_date: 回测开始日期
    :param end_date: 回测结束日期
    :param param_space: 参数空间，如 {"fast": [5, 20], "slow": [20, 60]}
    :param timeframe: D / W / M
    :param generations: 进化代数（若提供 config 则以 config 为准）
    :param population_per_gen: 种群大小（若提供 config 则以 config 为准）
    :param config: 可选 GA 配置；为 None 时使用默认 GAConfig
    :return: (best_params, best_score, history)，
             history 为每代最优的 [{gen, params, score}, ...]
    """
    from run_backtest_plugins import run_plugin_backtest
    from core.scoring import score_strategy

    cfg = config or GAConfig()
    n_pop = cfg.population_size
    n_gen = cfg.generations
    elite_n = min(cfg.elite_count, n_pop)
    history: List[Dict[str, Any]] = []

    def evaluate(params: Dict[str, Any]) -> float:
        try:
            result = run_plugin_backtest(
                strategy_id,
                stock_code,
                start_date,
                end_date,
                timeframe=timeframe,
                param_overrides=params,
            )
            if result.get("error"):
                return -1.0
            stats = result.get("stats") or {}
            score, _ = score_strategy(stats)
            return float(score)
        except Exception:
            return -1.0

    # 初始化种群
    population: List[Dict[str, Any]] = []
    for _ in range(n_pop):
        p = random_params(param_space)
        if p:
            population.append(p)
    while len(population) < n_pop:
        population.append(random_params(param_space))

    fitness = [evaluate(ind) for ind in population]
    best_score = max(fitness)
    best_idx = fitness.index(best_score)
    best_params = copy.deepcopy(population[best_idx])
    history.append({"gen": 0, "params": copy.deepcopy(best_params), "score": best_score})

    for gen in range(1, n_gen):
        # 精英保留
        indexed = list(zip(fitness, population))
        indexed.sort(key=lambda x: -x[0])
        new_pop = [copy.deepcopy(indexed[i][1]) for i in range(elite_n)]

        # 选择、交叉、变异生成剩余个体
        while len(new_pop) < n_pop:
            p1 = _tournament_select(population, fitness, cfg.tournament_size)
            p2 = _tournament_select(population, fitness, cfg.tournament_size)
            child = _crossover(p1, p2, param_space, cfg.crossover_rate)
            child = _mutate(child, param_space, cfg.mutation_rate, cfg.mutation_strength)
            if child:
                new_pop.append(child)

        population = new_pop
        fitness = [evaluate(ind) for ind in population]
        gen_best = max(fitness)
        gen_best_idx = fitness.index(gen_best)
        if gen_best > best_score:
            best_score = gen_best
            best_params = copy.deepcopy(population[gen_best_idx])
        history.append({"gen": gen, "params": copy.deepcopy(best_params), "score": best_score})

    return best_params, round(best_score, 2), history


def optimize_strategy_simple(
    strategy_id: str,
    stock_code: str,
    start_date: str,
    end_date: str,
    param_space: Dict[str, List[float]],
    timeframe: str = "D",
    generations: int = 20,
    population_per_gen: int = 20,
) -> Tuple[Dict[str, Any], float]:
    """
    简化接口：仅返回 (best_params, best_score)，兼容原有调用方。
    """
    best_params, best_score, _ = optimize_strategy(
        strategy_id, stock_code, start_date, end_date,
        param_space, timeframe, generations, population_per_gen,
    )
    return best_params, best_score


# ---------------------------------------------------------------------------
# 生产级 GeneticOptimizer 类：基于 DataFrame + 策略类 + 可插拔回测/评分
# ---------------------------------------------------------------------------

def _normalize_param_space(space: Dict[str, Any]) -> Dict[str, List[float]]:
    """将 (low, high) 或 [low, high] 统一为 [low, high]。"""
    out = {}
    for k, v in space.items():
        if isinstance(v, (list, tuple)) and len(v) >= 2:
            out[k] = [float(v[0]), float(v[1])]
        else:
            out[k] = [0, 1]
    return out


class GeneticOptimizer:
    """
    生产级遗传算法优化器：在给定参数空间内搜索策略最优参数。
    适应度由 score_fn(stats) 决定，stats 由 backtest_fn(df, strategy) 得到。
    """

    def __init__(
        self,
        population_size: int = 30,
        generations: int = 20,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.7,
        elite_count: int = 5,
    ):
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elite_count = min(elite_count, population_size // 2)

    def _random_params(self, space: Dict[str, List[float]]) -> Dict[str, Any]:
        """在空间内随机采样一组参数（整数或浮点）。"""
        return random_params(space)

    def _mutate(self, params: Dict[str, Any], space: Dict[str, List[float]]) -> Dict[str, Any]:
        """以 mutation_rate 对每个基因在范围内重新随机。"""
        mutant = copy.deepcopy(params)
        for k in list(mutant.keys()):
            if k not in space or random.random() >= self.mutation_rate:
                continue
            v = space[k]
            if not v or len(v) < 2:
                continue
            low, high = float(v[0]), float(v[1])
            if _is_int_param(space, k):
                mutant[k] = random.randint(int(low), int(high))
            else:
                mutant[k] = round(low + random.random() * (high - low), 4)
        return mutant

    def optimize(
        self,
        strategy_class: type,
        df: Any,
        param_space: Dict[str, Any],
        backtest_fn: Callable[[Any, Any], Dict[str, Any]],
        score_fn: Callable[[Dict[str, Any]], float],
    ) -> Tuple[Dict[str, Any], float]:
        """
        执行遗传算法优化。
        :param strategy_class: 策略类（可接受 **params 构造）
        :param df: 行情 DataFrame
        :param param_space: {"short_window": (5, 20), "long_window": (20, 60)} 或 [min, max]
        :param backtest_fn: (df, strategy_instance) -> stats dict
        :param score_fn: (stats) -> float 适应度
        :return: (best_params, best_score)
        """
        space = _normalize_param_space(param_space)
        population = [self._random_params(space) for _ in range(self.population_size)]
        best_params = None
        best_score = -1.0

        for gen in range(self.generations):
            scored = []
            for params in population:
                try:
                    strategy = strategy_class(**params)
                    stats = backtest_fn(df, strategy)
                    score = score_fn(stats)
                except Exception:
                    score = -1.0
                scored.append((score, params))
                if score > best_score:
                    best_score = score
                    best_params = copy.deepcopy(params)

            scored.sort(reverse=True, key=lambda x: x[0])
            survivors = [p for _, p in scored[: self.elite_count]]
            new_population = list(survivors)

            while len(new_population) < self.population_size:
                parent = copy.deepcopy(random.choice(survivors))
                child = self._mutate(parent, space)
                new_population.append(child)
            population = new_population

        return (best_params or {}), round(best_score, 2)
