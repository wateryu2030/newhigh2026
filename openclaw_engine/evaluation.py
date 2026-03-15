"""
策略评估：调用回测引擎，返回适应度（如夏普比率）。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .gene import StrategyGene


def evaluate_gene(
    gene: StrategyGene,
    symbol: str = "000001.SZ",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    init_cash: float = 10000.0,
    use_multi_objective: bool = True,
) -> Dict[str, Any]:
    """
    用回测引擎评估策略基因。当前实现：使用 trade_signals 回测（基因仅影响 strategy_id 过滤，后续可扩展为生成信号）。
    返回 { "fitness": float (sharpe 或 total_return), "sharpe_ratio", "total_return", "max_drawdown", "error" }。
    """
    try:
        import sys
        import os

        _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        for _d in ["backtest-engine/src", "data-pipeline/src", "core/src"]:
            _p = os.path.join(_root, _d)
            if os.path.isdir(_p) and _p not in sys.path:
                sys.path.insert(0, _p)
        from backtest_engine import run_backtest_from_db
        from datetime import datetime, timedelta

        end = end_date or datetime.now().strftime("%Y-%m-%d")
        start = start_date or (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        out = run_backtest_from_db(
            symbol=symbol,
            start_date=start,
            end_date=end,
            signal_source="trade_signals",
            init_cash=init_cash,
        )
        if out.get("error"):
            return {"fitness": 0.0, "error": out["error"]}
        if use_multi_objective:
            from .multi_objective import fitness_from_backtest_result

            fitness = fitness_from_backtest_result(out, use_composite=True)
        else:
            sharpe = out.get("sharpe_ratio")
            total_return = out.get("total_return")
            fitness = (
                float(sharpe)
                if sharpe is not None
                else (float(total_return) if total_return is not None else 0.0)
            )
        return {
            "fitness": fitness,
            "sharpe_ratio": out.get("sharpe_ratio"),
            "total_return": out.get("total_return"),
            "max_drawdown": out.get("max_drawdown"),
            "error": None,
        }
    except Exception as e:
        return {"fitness": 0.0, "error": str(e)}
