# OpenClaw evolution engine V1
from .gene import StrategyGene
from .genetic import crossover, mutate, selection
from .evaluation import evaluate_gene
from .population_manager import load_population_from_market, save_gene_to_market
from .evolution_orchestrator import run_evolution_cycle
from .multi_objective import composite_fitness, fitness_from_backtest_result

__all__ = [
    "StrategyGene",
    "crossover",
    "mutate",
    "selection",
    "evaluate_gene",
    "load_population_from_market",
    "save_gene_to_market",
    "run_evolution_cycle",
    "composite_fitness",
    "fitness_from_backtest_result",
]
