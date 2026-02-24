# -*- coding: utf-8 -*-
"""
实盘反馈学习：记录真实收益、滑点、交易成本，用于策略再优化。
"""
from __future__ import annotations
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_FEEDBACK_DIR = os.path.join(_ROOT, "output", "ai_evolution", "live_feedback")


class LiveFeedback:
    """记录实盘交易结果，供后续策略再优化使用。"""

    def __init__(self, data_dir: Optional[str] = None) -> None:
        self.data_dir = data_dir or DEFAULT_FEEDBACK_DIR
        os.makedirs(self.data_dir, exist_ok=True)

    def record_trade(
        self,
        strategy_id: str,
        params: Dict[str, Any],
        symbol: str,
        side: str,
        price: float,
        quantity: int,
        slippage: float = 0.0,
        commission: float = 0.0,
        realized_pnl: Optional[float] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        记录单笔成交。
        :param strategy_id: 策略 id
        :param params: 策略参数
        :param symbol: 标的
        :param side: BUY / SELL
        :param price: 成交价
        :param quantity: 数量
        :param slippage: 滑点（金额或比例，由 meta 说明）
        :param commission: 手续费
        :param realized_pnl: 该笔实现盈亏（若有）
        :param meta: 其他信息
        """
        record = {
            "ts": datetime.now().isoformat(),
            "strategy_id": strategy_id,
            "params": params,
            "symbol": symbol,
            "side": side,
            "price": price,
            "quantity": quantity,
            "slippage": slippage,
            "commission": commission,
            "realized_pnl": realized_pnl,
            "meta": meta or {},
        }
        path = os.path.join(self.data_dir, "trades.jsonl")
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning("Record trade failed: %s", e)

    def record_daily_pnl(
        self,
        strategy_id: str,
        params: Dict[str, Any],
        date: str,
        pnl: float,
        commission: float = 0.0,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """记录按日汇总的盈亏（便于与回测对比）。"""
        record = {
            "date": date,
            "strategy_id": strategy_id,
            "params": params,
            "pnl": pnl,
            "commission": commission,
            "meta": meta or {},
        }
        path = os.path.join(self.data_dir, "daily_pnl.jsonl")
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning("Record daily pnl failed: %s", e)

    def get_trades(self, strategy_id: Optional[str] = None, limit: int = 1000) -> List[Dict[str, Any]]:
        """读取已记录成交（可选按 strategy_id 过滤）。"""
        path = os.path.join(self.data_dir, "trades.jsonl")
        if not os.path.exists(path):
            return []
        records = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                    if strategy_id is None or r.get("strategy_id") == strategy_id:
                        records.append(r)
                except Exception:
                    continue
        return records[-limit:]

    def get_daily_pnls(self, strategy_id: Optional[str] = None, limit: int = 500) -> List[Dict[str, Any]]:
        """读取按日盈亏记录。"""
        path = os.path.join(self.data_dir, "daily_pnl.jsonl")
        if not os.path.exists(path):
            return []
        records = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                    if strategy_id is None or r.get("strategy_id") == strategy_id:
                        records.append(r)
                except Exception:
                    continue
        return records[-limit:]

    def compute_real_metrics(self, strategy_id: str, params: Dict[str, Any]) -> Dict[str, float]:
        """
        根据已记录的交易/日盈亏汇总真实收益、成本等，用于与回测对比或再优化。
        返回格式与 backtest_engine 一致: return, sharpe, drawdown（若可算）。
        """
        pnls = self.get_daily_pnls(strategy_id=strategy_id)
        if not pnls:
            return {"return": 0.0, "sharpe": 0.0, "drawdown": 0.0}
        total_pnl = sum(float(p.get("pnl", 0)) for p in pnls)
        # 简化：假设初始资金 1e6，return = total_pnl / 1e6
        import math
        returns = [float(p.get("pnl", 0)) / 1e6 for p in pnls]
        mean_ret = sum(returns) / len(returns) if returns else 0.0
        var = sum((r - mean_ret) ** 2 for r in returns) / len(returns) if returns else 0.0
        std = math.sqrt(var) if var > 0 else 1e-10
        sharpe = (mean_ret / std) * math.sqrt(252) if std else 0.0
        nav = 1.0
        peak = 1.0
        max_dd = 0.0
        for r in returns:
            nav += r
            if nav > peak:
                peak = nav
            if peak > 0:
                dd = (peak - nav) / peak
                if dd > max_dd:
                    max_dd = dd
        return {"return": total_pnl / 1e6, "sharpe": sharpe, "drawdown": max_dd}
