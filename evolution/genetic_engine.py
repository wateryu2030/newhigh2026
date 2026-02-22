# -*- coding: utf-8 -*-
"""
遗传进化：对策略代码进行交叉与变异，实现「优秀策略 A + 优秀策略 B → 子代 C」的基因组合。
"""
from __future__ import annotations
import random
import re
from typing import List, Optional, Tuple


def crossover(code1: str, code2: str, cut: Optional[int] = None) -> str:
    """
    两条策略代码按行交叉，生成子代。
    :param code1: 策略代码 A
    :param code2: 策略代码 B
    :param cut: 切割行号（None 则随机）
    :return: 子代代码
    """
    p1 = [line for line in code1.split("\n") if line.strip()]
    p2 = [line for line in code2.split("\n") if line.strip()]
    if not p1:
        return code2
    if not p2:
        return code1
    if cut is None:
        cut = random.randint(1, min(len(p1), len(p2)) - 1) if min(len(p1), len(p2)) > 1 else 0
    cut = max(0, min(cut, len(p1), len(p2)))
    child = p1[:cut] + p2[cut:]
    return "\n".join(child)


def mutate(code: str, rate: float = 0.1, rng: Optional[random.Random] = None) -> str:
    """
    对策略代码做轻微变异：以 rate 概率随机替换某行或插入/删除空行（保守变异）。
    :param code: 策略代码
    :param rate: 变异概率
    :param rng: 随机数生成器
    """
    rng = rng or random
    lines = code.split("\n")
    out = []
    for i, line in enumerate(lines):
        if rng.random() > rate:
            out.append(line)
            continue
        # 数字常量变异：加减 1 或 *1.1
        def _sub(m):
            try:
                v = float(m.group(0))
                if rng.random() < 0.5:
                    return str(int(v) + rng.choice([-1, 1])) if v == int(v) else str(round(v * 1.1, 2))
                return m.group(0)
            except Exception:
                return m.group(0)
        new_line = re.sub(r"\b\d+\.?\d*\b", _sub, line)
        out.append(new_line)
    return "\n".join(out)


class GeneticEngine:
    """遗传引擎：交叉 + 变异，用于策略池内优秀策略的再进化。"""

    def __init__(self, mutate_rate: float = 0.1):
        self.mutate_rate = mutate_rate

    def crossover(self, code1: str, code2: str) -> str:
        return crossover(code1, code2)

    def mutate(self, code: str, rate: Optional[float] = None) -> str:
        return mutate(code, rate=rate or self.mutate_rate)

    def evolve_pair(
        self,
        code_a: str,
        code_b: str,
        num_children: int = 2,
    ) -> List[str]:
        """从两条代码生成 num_children 个子代（交叉后可选变异）。"""
        children = []
        for _ in range(num_children):
            c = self.crossover(code_a, code_b)
            c = self.mutate(c)
            children.append(c)
        return children
