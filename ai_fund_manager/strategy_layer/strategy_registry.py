# -*- coding: utf-8 -*-
"""
策略注册中心：注册策略、更新表现、获取列表。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional


class StrategyRegistry:
    def __init__(self) -> None:
        self.strategies: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, strategy_obj: Any, metrics: Optional[Dict] = None) -> None:
        self.strategies[name] = {
            "obj": strategy_obj,
            "metrics": metrics or {},
        }

    def update_metrics(self, name: str, metrics: Dict[str, Any]) -> None:
        if name in self.strategies:
            self.strategies[name]["metrics"] = metrics

    def get_all(self) -> Dict[str, Dict[str, Any]]:
        return dict(self.strategies)

    def get_names(self) -> List[str]:
        return list(self.strategies.keys())
