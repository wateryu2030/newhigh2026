# -*- coding: utf-8 -*-
"""
策略池：仅优秀策略（夏普/回撤/稳定性达标）进入实盘候选，自动上线与淘汰。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import json
import os
import time


# 默认上线门槛（可配置）
DEFAULT_THRESHOLD = {
    "min_sharpe": 1.0,
    "max_drawdown": 0.20,
    "min_score": 1.0,
    "min_trades": 10,
}


class StrategyPool:
    """
    策略池：维护已通过评估的策略，支持按条件自动加入与淘汰。
    """

    def __init__(
        self,
        min_sharpe: float = 1.0,
        max_drawdown: float = 0.20,
        min_score: float = 1.0,
        persist_path: Optional[str] = None,
    ):
        self.min_sharpe = min_sharpe
        self.max_drawdown = max_drawdown
        self.min_score = min_score
        self.persist_path = persist_path
        self.pool: List[Dict[str, Any]] = []

    def add(self, strategy_code: str, metrics: Dict[str, Any], strategy_id: Optional[str] = None) -> bool:
        """
        仅当 score、sharpe、max_dd 满足条件时加入策略池。
        :return: 是否加入成功
        """
        score = metrics.get("score", 0)
        sharpe = metrics.get("sharpe", 0)
        max_dd = metrics.get("max_dd", 1)
        if score < self.min_score or sharpe < self.min_sharpe or max_dd > self.max_drawdown:
            return False
        self.pool.append({
            "id": strategy_id or f"ev_{int(time.time())}_{len(self.pool)}",
            "code": strategy_code,
            "metrics": metrics,
            "added_at": time.time(),
        })
        if self.persist_path:
            self._save()
        return True

    def get_all(self) -> List[Dict[str, Any]]:
        """返回池中所有策略。"""
        return list(self.pool)

    def get_best(self, top_k: int = 5) -> List[Dict[str, Any]]:
        """按 score 降序取前 top_k。"""
        sorted_pool = sorted(self.pool, key=lambda x: x["metrics"].get("score", 0), reverse=True)
        return sorted_pool[:top_k]

    def remove_by_id(self, strategy_id: str) -> bool:
        """按 id 淘汰策略。"""
        before = len(self.pool)
        self.pool = [p for p in self.pool if p.get("id") != strategy_id]
        if self.persist_path and len(self.pool) != before:
            self._save()
        return len(self.pool) != before

    def _save(self) -> None:
        if not self.persist_path:
            return
        try:
            os.makedirs(os.path.dirname(self.persist_path) or ".", exist_ok=True)
            with open(self.persist_path, "w", encoding="utf-8") as f:
                json.dump(self.pool, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def load(self) -> None:
        """从 persist_path 加载策略池。"""
        if not self.persist_path or not os.path.exists(self.persist_path):
            return
        try:
            with open(self.persist_path, "r", encoding="utf-8") as f:
                self.pool = json.load(f)
        except Exception:
            self.pool = []
