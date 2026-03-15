"""
Strategy Evolution Engine — 遗传算法
Select top strategies → crossover → mutate → new population.
"""

import copy
import random
from typing import Any, Callable, Dict, List, Tuple


def select_elite(
    strategies_with_scores: List[Tuple[Dict[str, Any], float]],
    elite_size: int = 100,
) -> List[Dict[str, Any]]:
    """Select top elite_size strategies by score."""
    sorted_list = sorted(strategies_with_scores, key=lambda x: -x[1])
    return [s for s, _ in sorted_list[:elite_size]]


def _deep_merge(a: Dict, b: Dict) -> Dict:
    out = copy.deepcopy(a)
    for k, v in b.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def crossover(s1: Dict[str, Any], s2: Dict[str, Any]) -> Dict[str, Any]:
    """Combine two strategies: random mix of params and indicators."""
    child = copy.deepcopy(s1)
    if random.random() < 0.5:
        child["strategy_type"] = s2.get("strategy_type", child["strategy_type"])
    if random.random() < 0.5:
        child["params"] = _deep_merge(child.get("params", {}), s2.get("params", {}))
    if random.random() < 0.5 and "indicators" in s2:
        child["indicators"] = list(
            set((child.get("indicators", []) or []) + (s2["indicators"] or []))
        )[:4]
    if random.random() < 0.5:
        child["timeframe"] = s2.get("timeframe", child.get("timeframe", "1h"))
    return child


STRATEGY_TYPES = ["trend_following", "mean_reversion", "breakout"]
INDICATORS = ["rsi", "macd", "vwap", "atr", "momentum", "volatility"]
TIMEFRAMES = ["1m", "5m", "1h", "1d"]


def _random_params(strategy_type: str) -> Dict[str, Any]:
    if strategy_type == "trend_following":
        return {"fast_period": random.randint(5, 30), "slow_period": random.randint(30, 120)}
    if strategy_type == "mean_reversion":
        return {
            "rsi_period": random.randint(7, 21),
            "oversold": random.uniform(20, 40),
            "overbought": random.uniform(60, 80),
        }
    if strategy_type == "breakout":
        return {"lookback": random.randint(10, 50)}
    return {}


def mutate(
    strategy: Dict[str, Any],
    mutation_rate: float = 0.2,
) -> Dict[str, Any]:
    """Randomly mutate params and indicators."""
    s = copy.deepcopy(strategy)
    if random.random() < mutation_rate:
        s["strategy_type"] = random.choice(STRATEGY_TYPES)
        s["params"] = _random_params(s["strategy_type"])
    if random.random() < mutation_rate and "params" in s:
        for k in s["params"]:
            if isinstance(s["params"][k], (int, float)):
                if isinstance(s["params"][k], int):
                    s["params"][k] = max(1, s["params"][k] + random.randint(-3, 3))
                else:
                    s["params"][k] = max(0.01, s["params"][k] * random.uniform(0.8, 1.2))
    if random.random() < mutation_rate:
        s["indicators"] = random.sample(INDICATORS, k=min(random.randint(1, 3), len(INDICATORS)))
    if random.random() < mutation_rate:
        s["timeframe"] = random.choice(TIMEFRAMES)
    return s


def evolve_population(
    strategies_with_scores: List[Tuple[Dict[str, Any], float]],
    population_size: int = 1000,
    elite_size: int = 100,
    mutation_rate: float = 0.2,
) -> List[Dict[str, Any]]:
    """
    Generate new population: elite + crossover offspring + mutated, fill to population_size.
    """
    elite = select_elite(strategies_with_scores, elite_size=elite_size)
    if not elite:
        return []
    new_pop = list(elite)
    while len(new_pop) < population_size:
        if random.random() < 0.5 and len(elite) >= 2:
            a, b = random.sample(elite, 2)
            child = crossover(a, b)
        else:
            child = copy.deepcopy(random.choice(elite))
        child = mutate(child, mutation_rate=mutation_rate)
        new_pop.append(child)
    return new_pop[:population_size]
