"""
策略评估：调用回测引擎，返回适应度（如夏普比率）。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .gene import StrategyGene


def _eval_strategy_id(gene: StrategyGene) -> Optional[str]:
    """回测时使用的 trade_signals.strategy_id：子代继承自 params.eval_strategy_id。"""
    sid = (gene.params or {}).get("eval_strategy_id") or gene.strategy_id
    s = str(sid).strip() if sid else ""
    return s or None


def _resolve_eval_symbol(eval_strategy_id: Optional[str], default_symbol: str) -> str:
    """
    在库中选一只「该策略有信号且存在日 K」的标的，避免固定 000001 与实盘信号池脱节。
    """
    if not eval_strategy_id:
        return default_symbol
    try:
        import os
        import sys

        _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        dp = os.path.join(_root, "data-pipeline", "src")
        if os.path.isdir(dp) and dp not in sys.path:
            sys.path.insert(0, dp)
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path

        if not os.path.isfile(get_db_path()):
            return default_symbol
        conn = get_conn(read_only=True)
        row = conn.execute(
            """
            SELECT t.code
            FROM trade_signals t
            WHERE t.strategy_id = ?
              AND t.code IN (SELECT DISTINCT code FROM a_stock_daily)
            ORDER BY t.signal_score DESC NULLS LAST, t.snapshot_time DESC NULLS LAST
            LIMIT 1
            """,
            [eval_strategy_id],
        ).fetchone()
        conn.close()
        if row and row[0]:
            return str(row[0])
    except Exception:
        pass
    return default_symbol


def evaluate_gene(
    gene: StrategyGene,
    symbol: str = "000001.SZ",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    init_cash: float = 10000.0,
    use_multi_objective: bool = True,
) -> Dict[str, Any]:
    """
    用回测引擎评估：按 eval_strategy_id / strategy_id 过滤 trade_signals，并解析可交易标的代码。
    返回 { "fitness", "sharpe_ratio", "total_return", "max_drawdown", "error", "eval_symbol", "eval_strategy_id" }。
    """
    try:
        import os
        import sys
        from datetime import datetime, timedelta

        _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        for _d in ["backtest-engine/src", "data-pipeline/src", "core/src"]:
            _p = os.path.join(_root, _d)
            if os.path.isdir(_p) and _p not in sys.path:
                sys.path.insert(0, _p)
        from backtest_engine import run_backtest_from_db

        eval_sid = _eval_strategy_id(gene)
        use_symbol = _resolve_eval_symbol(eval_sid, symbol)

        end = end_date or datetime.now().strftime("%Y-%m-%d")
        start = start_date or (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        out = run_backtest_from_db(
            symbol=use_symbol,
            start_date=start,
            end_date=end,
            signal_source="trade_signals",
            strategy_id=eval_sid,
            init_cash=init_cash,
        )
        if out.get("error"):
            return {
                "fitness": 0.0,
                "error": out["error"],
                "eval_symbol": use_symbol,
                "eval_strategy_id": eval_sid,
            }
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
            "eval_symbol": use_symbol,
            "eval_strategy_id": eval_sid,
        }
    except (ImportError, ModuleNotFoundError, KeyError, TypeError, ValueError) as e:
        return {"fitness": 0.0, "error": str(e)}
