# -*- coding: utf-8 -*-
"""
信号整合器：整合多个策略的 BUY/SELL/HOLD 信号，生成组合级信号。
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Union
import pandas as pd
import numpy as np


@dataclass
class AggregatorConfig:
    """信号聚合配置。"""
    mode: str = "majority"  # majority | strong_buy | weighted | ignore_lowest
    strong_buy_threshold: float = 0.8  # 得分高于此视为强 BUY
    min_buy_ratio: float = 0.5  # 多数 = 超过此比例的策略为 BUY
    ignore_lowest_n: int = 1  # 忽略得分最低的 n 个策略


class SignalAggregator:
    """
    整合多策略信号规则：
    - majority: 多数策略 BUY -> BUY，多数 SELL -> SELL
    - strong_buy: 任意策略强 BUY -> BUY
    - weighted: 加权求和，正为 BUY，负为 SELL
    - ignore_lowest: 忽略得分最低的 n 个策略后再 majority
    """

    def __init__(self, config: Optional[AggregatorConfig] = None):
        self.config = config or AggregatorConfig()

    def aggregate(
        self,
        signals: Dict[str, pd.Series],
        weights: Optional[Dict[str, float]] = None,
        scores: Optional[Dict[str, float]] = None,
    ) -> pd.Series:
        """
        :param signals: { strategy_id: Series(date -> 1/0/-1) }
        :param weights: 各策略权重，None 表示等权
        :param scores: 各策略得分，用于 strong_buy 和 ignore_lowest
        :return: 组合信号 Series
        """
        if not signals:
            return pd.Series(dtype=float)

        all_dates = set()
        for s in signals.values():
            if s is not None and len(s) > 0:
                all_dates.update(s.index.astype(str))
        dates = sorted(all_dates)
        if not dates:
            return pd.Series(dtype=float)

        ids = list(signals.keys())
        w = self._get_weights(ids, weights)
        sc = scores or {k: 0.5 for k in ids}

        if self.config.mode == "ignore_lowest" and len(ids) > self.config.ignore_lowest_n:
            sorted_ids = sorted(ids, key=lambda x: sc.get(x, 0))
            ids = sorted_ids[self.config.ignore_lowest_n:]

        out = pd.Series(0.0, index=dates)
        for d in dates:
            vals = []
            ws = []
            for i, sid in enumerate(ids):
                s = signals.get(sid)
                if s is None or d not in s.index:
                    v = 0.0
                else:
                    v = float(s.loc[d]) if d in s.index else 0.0
                vals.append(v)
                ws.append(w.get(sid, 1.0 / len(ids)))

            if self.config.mode == "majority":
                out[d] = self._majority(vals, ws)
            elif self.config.mode == "strong_buy":
                out[d] = self._strong_buy(vals, ids, sc)
            elif self.config.mode == "ignore_lowest":
                out[d] = self._majority(vals, ws)
            else:  # weighted
                out[d] = self._weighted(vals, ws)
        return out

    def _get_weights(self, ids: List[str], weights: Optional[Dict[str, float]]) -> Dict[str, float]:
        if weights is None or len(weights) == 0:
            return {k: 1.0 / len(ids) for k in ids}
        s = sum(weights.get(k, 0) for k in ids)
        if s <= 0:
            return {k: 1.0 / len(ids) for k in ids}
        return {k: weights.get(k, 0) / s for k in ids}

    def _majority(self, vals: List[float], ws: List[float]) -> float:
        buy = sum(w for v, w in zip(vals, ws) if v > 0)
        sell = sum(w for v, w in zip(vals, ws) if v < 0)
        if buy > self.config.min_buy_ratio:
            return 1.0
        if sell > self.config.min_buy_ratio:
            return -1.0
        return 0.0

    def _strong_buy(self, vals: List[float], ids: List[str], scores: Dict[str, float]) -> float:
        for v, sid in zip(vals, ids):
            if v > 0 and scores.get(sid, 0) >= self.config.strong_buy_threshold:
                return 1.0
        sell = sum(1 for v in vals if v < 0)
        if sell > len(vals) / 2:
            return -1.0
        return 0.0

    def _weighted(self, vals: List[float], ws: List[float]) -> float:
        s = sum(v * w for v, w in zip(vals, ws))
        if s > 0.1:
            return 1.0
        if s < -0.1:
            return -1.0
        return 0.0
