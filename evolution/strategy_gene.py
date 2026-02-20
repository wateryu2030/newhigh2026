# -*- coding: utf-8 -*-
"""
策略基因：将策略参数编码为可变异、可交叉的向量，供进化器评估与进化。
"""
import copy
import random
from typing import Dict, Any, List, Optional


# 默认参数空间：均线周期、阈值等，可扩展
DEFAULT_GENE_SCHEMA = {
    "ma_short": (5, 30),
    "ma_long": (20, 120),
    "momentum_period": (5, 30),
    "threshold_buy": (0.0, 0.05),
    "threshold_sell": (-0.05, 0.0),
}


class StrategyGene:
    """
    策略基因：一组数值参数，对应某一类策略（如双均线+动量阈值）。
    """

    def __init__(self, params: Optional[Dict[str, float]] = None, schema: Optional[Dict[str, tuple]] = None):
        self.schema = schema or DEFAULT_GENE_SCHEMA
        if params is not None:
            self.params = dict(params)
        else:
            self.params = self._random_params()

    def _random_params(self) -> Dict[str, float]:
        return {
            k: random.uniform(v[0], v[1]) if isinstance(v[0], (int, float)) else random.randint(v[0], v[1])
            for k, v in self.schema.items()
        }

    def copy(self) -> "StrategyGene":
        return StrategyGene(params=copy.deepcopy(self.params), schema=self.schema)

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.params)


def mutate(gene: StrategyGene, rate: float = 0.2, sigma: float = 0.2) -> StrategyGene:
    """对基因随机变异：以 rate 概率对每个参数加高斯扰动（或重采样）。"""
    out = gene.copy()
    for k in out.params:
        if random.random() > rate:
            continue
        lo, hi = out.schema.get(k, (0, 1))
        if isinstance(lo, int) and isinstance(hi, int):
            out.params[k] = int(random.gauss(out.params[k], (hi - lo) * sigma))
            out.params[k] = max(lo, min(hi, out.params[k]))
        else:
            out.params[k] = out.params[k] + random.gauss(0, (hi - lo) * sigma)
            out.params[k] = max(lo, min(hi, out.params[k]))
    return out


def crossover(gene_a: StrategyGene, gene_b: StrategyGene) -> StrategyGene:
    """交叉：每个参数以 0.5 概率取 A 或 B。"""
    schema = gene_a.schema
    params = {}
    for k in schema:
        params[k] = gene_a.params[k] if random.random() < 0.5 else gene_b.params[k]
    return StrategyGene(params=params, schema=schema)
