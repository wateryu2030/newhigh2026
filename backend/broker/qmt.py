# -*- coding: utf-8 -*-
"""
QMT 实盘接入：配置驱动，send_order / cancel_order / query_position / get_balance。
实盘需安装 QMT 客户端并配置 miniquant 或官方 Python 接口；此处为完整骨架与配置项。
"""
from __future__ import annotations
import logging
from typing import Any, Dict, Optional

from .base import BrokerBase

logger = logging.getLogger(__name__)


class QMTBroker(BrokerBase):
    """
    QMT 实盘券商。
    配置示例（config）:
      - qmt_path: QMT 安装路径或 miniquant 地址
      - account_id: 资金账号
      - timeout: 请求超时秒数
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._connected = False
        self._order_id = 0
        # 实盘接入时可持有一个 connection / session 对象
        self._client: Any = None

    def connect(self) -> bool:
        try:
            # 方式1: miniquant 等 HTTP 封装
            # self._client = MiniquantClient(self.config.get("qmt_path"), ...)
            # 方式2: QMT 官方 Python API
            # from xtquant import xttrader
            # self._client = xttrader.XtQuantTrader(path)
            self._connected = True
            logger.info("QMT connect (stub)")
            return True
        except Exception as e:
            logger.exception("QMT connect failed: %s", e)
            return False

    def _ensure_connected(self) -> bool:
        if not self._connected:
            return self.connect()
        return True

    def send_order(self, order: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        symbol = order.get("symbol") or order.get("code")
        qty = abs(int(order.get("qty", 0) or 0))
        side = (order.get("side") or "BUY").upper()
        price = order.get("price")
        if not symbol or qty <= 0:
            return None
        if not self._ensure_connected():
            return None
        # TODO: 调用 QMT 下单，例如
        # order_id = self._client.order_stock(account, symbol, order_type, qty, price)
        self._order_id += 1
        order_id = f"qmt_{self._order_id}"
        out = {
            "order_id": order_id,
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "price": price,
            "status": "SUBMITTED",
            "broker": "qmt",
        }
        logger.info("QMT send_order (stub): %s", out)
        return out

    def buy(
        self,
        symbol: str,
        qty: float,
        price: Optional[float] = None,
        order_type: str = "limit",
    ) -> Optional[Dict[str, Any]]:
        return self.send_order({"symbol": symbol, "qty": int(qty), "side": "BUY", "price": price})

    def sell(
        self,
        symbol: str,
        qty: float,
        price: Optional[float] = None,
        order_type: str = "limit",
    ) -> Optional[Dict[str, Any]]:
        return self.send_order({"symbol": symbol, "qty": int(qty), "side": "SELL", "price": price})

    def cancel_order(self, order_id: str) -> bool:
        if not self._ensure_connected():
            return False
        # TODO: self._client.cancel_order(order_id)
        logger.info("QMT cancel_order (stub): %s", order_id)
        return True

    def query_position(self, symbol: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        if not self._ensure_connected():
            return {}
        # TODO: positions = self._client.get_stock_positions(account); 转为 { order_book_id: { qty, cost, ... } }
        return {}

    def get_balance(self) -> Dict[str, float]:
        if not self._ensure_connected():
            return {"total_asset": 0.0, "cash": 0.0, "frozen": 0.0}
        # TODO: acc = self._client.get_account(account); return { "total_asset": ..., "cash": ..., "frozen": ... }
        return {"total_asset": 0.0, "cash": 0.0, "frozen": 0.0}


def create_qmt_broker(config: Optional[Dict[str, Any]] = None) -> QMTBroker:
    """从配置创建 QMT Broker；config 可从 YAML/ENV 读取。"""
    if config is None:
        import os
        config = {
            "qmt_path": os.environ.get("QMT_PATH", ""),
            "account_id": os.environ.get("QMT_ACCOUNT_ID", ""),
            "timeout": float(os.environ.get("QMT_TIMEOUT", "10")),
        }
    return QMTBroker(config=config)
