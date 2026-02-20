# -*- coding: utf-8 -*-
"""
高频做市策略：双边报价赚取买卖价差，根据库存与波动率调整报价与挂单量。
思路：mid 上下各 half_spread 挂单，库存偏离时 skew 报价促进减仓。
"""
from typing import Optional, Callable, Dict, Any, Tuple


class MarketMakingEngine:
    """
    做市引擎：根据 mid、库存、波动率计算 bid/ask 报价与建议挂单量。
    不直接下单，通过 on_quote 回调将 (bid, ask, size_bid, size_ask) 交给执行层。
    """

    def __init__(
        self,
        half_spread_bps: float = 5.0,
        inventory_skew_bps: float = 2.0,
        max_position: float = 1000.0,
        base_size: float = 100.0,
        on_quote: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """
        :param half_spread_bps: 半价差（基点），报价 = mid ± half_spread
        :param inventory_skew_bps: 每单位库存导致的报价偏移（基点）
        :param max_position: 最大允许库存（绝对值）
        :param base_size: 默认挂单量
        :param on_quote: 产出报价时回调 (bid, ask, size_bid, size_ask, ...)
        """
        self.half_spread_bps = half_spread_bps
        self.inventory_skew_bps = inventory_skew_bps
        self.max_position = max_position
        self.base_size = base_size
        self.on_quote = on_quote or self._default_quote
        self.inventory: float = 0.0
        self.last_mid: Optional[float] = None

    @staticmethod
    def _default_quote(q: Dict[str, Any]) -> None:
        print("QUOTE", q.get("bid"), q.get("ask"), "size", q.get("size_bid"), q.get("size_ask"))

    def on_tick(self, mid: float, bid: Optional[float] = None, ask: Optional[float] = None) -> None:
        """
        收到新行情：用 mid（或 (bid+ask)/2）与当前库存计算我们的 bid/ask 报价。
        """
        if mid <= 0:
            return
        self.last_mid = mid
        bps = 1e-4 * mid
        half = self.half_spread_bps * bps
        skew = self.inventory_skew_bps * bps * self.inventory
        our_bid = mid - half - skew
        our_ask = mid + half - skew
        size_bid = self.base_size if self.inventory < self.max_position else 0.0
        size_ask = self.base_size if self.inventory > -self.max_position else 0.0
        self.on_quote({
            "bid": round(our_bid, 2),
            "ask": round(our_ask, 2),
            "size_bid": size_bid,
            "size_ask": size_ask,
            "mid": mid,
            "inventory": self.inventory,
        })

    def on_fill(self, side: str, size: float, price: float) -> None:
        """成交回报：更新库存。"""
        if side.upper() in ("BUY", "B"):
            self.inventory += size
        else:
            self.inventory -= size

    def get_quote(self, mid: float) -> Tuple[float, float, float, float]:
        """仅计算不回调：返回 (bid, ask, size_bid, size_ask)。"""
        if mid <= 0:
            return 0.0, 0.0, 0.0, 0.0
        bps = 1e-4 * mid
        half = self.half_spread_bps * bps
        skew = self.inventory_skew_bps * bps * self.inventory
        our_bid = mid - half - skew
        our_ask = mid + half - skew
        size_bid = self.base_size if self.inventory < self.max_position else 0.0
        size_ask = self.base_size if self.inventory > -self.max_position else 0.0
        return our_bid, our_ask, size_bid, size_ask
