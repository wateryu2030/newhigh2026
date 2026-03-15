# Genetic operations for strategy evolution
from __future__ import annotations
import random
from typing import Dict, List
from .gene import StrategyGene


def crossover(parent1: StrategyGene, parent2: StrategyGene) -> StrategyGene:
    c = parent1.copy()
    if random.random() < 0.5 and parent2.rule_tree:
        keys = list(c.rule_tree.keys())
        if keys:
            k = random.choice(keys)
            if isinstance(c.rule_tree[k], list) and isinstance(parent2.rule_tree.get(k), list):
                p2_list = parent2.rule_tree[k]
                if p2_list:
                    idx = random.randint(0, len(c.rule_tree[k]))
                    c.rule_tree[k] = c.rule_tree[k][:idx] + p2_list[idx:]
    if random.random() < 0.5 and parent2.params:
        for k, v in parent2.params.items():
            if random.random() < 0.5:
                c.params[k] = v
    return c


def mutate(gene: StrategyGene, mutation_rate: float = 0.1) -> StrategyGene:
    c = gene.copy()
    for k in list(c.params.keys()):
        if random.random() < mutation_rate and isinstance(c.params[k], (int, float)):
            delta = (random.random() - 0.5) * 0.2 * abs(c.params[k])
            c.params[k] = c.params[k] + delta
    return c


def selection(
    population: List[Dict], fitness_scores: List[float], elite_size: int = 2
) -> List[StrategyGene]:
    if not population or not fitness_scores or len(population) != len(fitness_scores):
        return []
    indexed = list(zip(population, fitness_scores))
    indexed.sort(key=lambda x: (x[1] or 0), reverse=True)
    elites = [
        StrategyGene.from_dict(p) if isinstance(p, dict) else p for p, _ in indexed[:elite_size]
    ]
    rest = indexed[elite_size:]
    if not rest:
        return elites
    total = sum(max(0, s) for _, s in rest)
    if total <= 0:
        return elites
    selected = []
    for _ in range(min(len(rest), max(0, len(population) - elite_size))):
        r = random.uniform(0, total)
        for p, s in rest:
            r -= max(0, s)
            if r <= 0:
                selected.append(StrategyGene.from_dict(p) if isinstance(p, dict) else p)
                break
    return elites + selected
