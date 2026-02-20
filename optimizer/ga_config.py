# -*- coding: utf-8 -*-
"""
遗传算法优化器配置。
生产级可读：所有超参数集中管理，便于调参与扩展。
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass
class GAConfig:
    """
    遗传算法运行参数。
    """

    # 种群与迭代
    population_size: int = 30
    """每代个体数量"""
    generations: int = 25
    """进化代数"""
    elite_count: int = 2
    """每代保留的最优个体数（精英保留）"""

    # 遗传算子
    crossover_rate: float = 0.7
    """交叉概率"""
    mutation_rate: float = 0.15
    """变异概率"""
    mutation_strength: float = 0.3
    """变异强度：相对参数范围的扰动比例"""

    # 选择压力（锦标赛规模越大，选择压力越大）
    tournament_size: int = 3
    """锦标赛选择：每次从 tournament_size 个个体中取最优"""

    def to_dict(self) -> Dict[str, Any]:
        """导出为字典，便于日志与 API 透出。"""
        return {
            "population_size": self.population_size,
            "generations": self.generations,
            "elite_count": self.elite_count,
            "crossover_rate": self.crossover_rate,
            "mutation_rate": self.mutation_rate,
            "mutation_strength": self.mutation_strength,
            "tournament_size": self.tournament_size,
        }
