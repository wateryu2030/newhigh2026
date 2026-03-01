# -*- coding: utf-8 -*-
"""
机构级策略层：龙头突破、趋势机构、Alpha 因子。
"""
from .dragon_strategy import DragonLeaderStrategy
from .trend_strategy import TrendInstitutionStrategy
from .alpha_factor import AlphaFactorModel

__all__ = [
    "DragonLeaderStrategy",
    "TrendInstitutionStrategy",
    "AlphaFactorModel",
]
