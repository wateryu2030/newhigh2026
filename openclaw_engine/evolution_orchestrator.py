"""
进化周期编排：加载种群 → 选择 → 交叉/变异 → 回测评估 → 优秀个体写入策略市场。
"""

from __future__ import annotations

from typing import Any, Dict, List

from .gene import StrategyGene
from .genetic import crossover, mutate, selection
from .evaluation import evaluate_gene
from .population_manager import load_population_from_market, save_gene_to_market


def run_evolution_cycle(
    population_limit: int = 10,
    elite_size: int = 2,
    offspring_size: int = 4,
    mutation_rate: float = 0.1,
    symbol: str = "000001.SZ",
) -> Dict[str, Any]:
    """
    执行一轮进化：从 strategy_market 加载种群，评估适应度，选择+交叉+变异生成子代，评估子代，
    若子代适应度超过阈值则写入 strategy_market。
    返回 { "generation": 1, "population_size", "offspring_evaluated", "saved": int, "best_fitness", "error" }。
    """
    result = {
        "generation": 1,
        "population_size": 0,
        "offspring_evaluated": 0,
        "saved": 0,
        "best_fitness": None,
        "error": None,
    }
    try:
        population = load_population_from_market(limit=population_limit)
        if len(population) < 2:
            result["population_size"] = len(population)
            return result
        result["population_size"] = len(population)
        pop_dicts = [g.to_dict() for g in population]
        fitness_scores = []
        for g in population:
            ev = evaluate_gene(g, symbol=symbol)
            fitness_scores.append(ev.get("fitness") or 0.0)
        selected = selection(pop_dicts, fitness_scores, elite_size=elite_size)
        if len(selected) < 2:
            return result
        offspring: List[StrategyGene] = []
        for _ in range(offspring_size):
            p1, p2 = selected[0], selected[1]
            if len(selected) > 2:
                p1, p2 = selected[_ % len(selected)], selected[(_ + 1) % len(selected)]
            child = mutate(crossover(p1, p2), mutation_rate=mutation_rate)
            child.strategy_id = f"openclaw_gen1_{_}"
            offspring.append(child)
        best_fitness = max(fitness_scores) if fitness_scores else None
        result["best_fitness"] = best_fitness
        saved = 0
        for child in offspring:
            ev = evaluate_gene(child, symbol=symbol)
            result["offspring_evaluated"] += 1
            f = ev.get("fitness") or 0
            if best_fitness is not None and f >= best_fitness * 0.9:
                save_gene_to_market(
                    child,
                    name=child.strategy_id,
                    return_pct=(
                        ev.get("total_return") * 100 if ev.get("total_return") is not None else None
                    ),
                    sharpe_ratio=ev.get("sharpe_ratio"),
                    max_drawdown=ev.get("max_drawdown"),
                    status="active",
                )
                saved += 1
        result["saved"] = saved
    except (ImportError, ModuleNotFoundError, ValueError, TypeError, AttributeError) as e:
        result["error"] = str(e)
    return result
