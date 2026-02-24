# -*- coding: utf-8 -*-
"""
回测引擎适配：调用现有 run_plugin_backtest，输出统一为 return / sharpe / drawdown。
"""
from __future__ import annotations
import logging
import math
import os
import sys
from typing import Any, Dict

logger = logging.getLogger(__name__)

# 项目根目录
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def run_backtest(
    strategy_id: str,
    params: Dict[str, Any],
    stock_code: str,
    start_date: str,
    end_date: str,
    timeframe: str = "D",
) -> Dict[str, float]:
    """
    执行单次回测，返回统一指标。
    :return: {"return": float, "sharpe": float, "drawdown": float}，异常时返回无效值。
    """
    try:
        from run_backtest_plugins import run_plugin_backtest
    except Exception as e:
        logger.exception("Import run_plugin_backtest: %s", e)
        return {"return": 0.0, "sharpe": 0.0, "drawdown": 1.0}

    try:
        result = run_plugin_backtest(
            strategy_id=strategy_id,
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe,
            param_overrides=params,
        )
    except Exception as e:
        logger.exception("Backtest failed: %s", e)
        return {"return": 0.0, "sharpe": 0.0, "drawdown": 1.0}

    if result.get("error"):
        logger.warning("Backtest error: %s", result.get("error"))
        return {"return": 0.0, "sharpe": 0.0, "drawdown": 1.0}

    total_return = result.get("summary", {}).get("total_returns") or result.get("summary", {}).get("return_rate") or 0.0
    max_drawdown = result.get("summary", {}).get("max_drawdown") or result.get("stats", {}).get("maxDrawdown") or 0.0
    curve = result.get("curve") or []
    sharpe = _compute_sharpe(curve)

    return {
        "return": float(total_return),
        "sharpe": float(sharpe),
        "drawdown": float(max_drawdown),
    }


def _compute_sharpe(curve: list) -> float:
    """从净值曲线计算年化夏普（假设日频，252 交易日）。"""
    if not curve or len(curve) < 2:
        return 0.0
    values = [float(p.get("value", 1.0)) for p in curve]
    returns = []
    for i in range(1, len(values)):
        if values[i - 1] and values[i - 1] != 0:
            returns.append((values[i] - values[i - 1]) / values[i - 1])
        else:
            returns.append(0.0)
    if not returns:
        return 0.0
    mean_ret = sum(returns) / len(returns)
    variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
    std = math.sqrt(variance) if variance > 0 else 1e-10
    # 年化
    ann = mean_ret * 252
    ann_std = std * math.sqrt(252)
    if ann_std <= 0:
        return 0.0
    return ann / ann_std
