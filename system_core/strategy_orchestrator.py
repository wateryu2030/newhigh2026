"""
策略调度：执行 ai_fusion_strategy（主）与 trade_signal_aggregator（回退），输出 trade_signals。
"""

from __future__ import annotations

import os
from typing import Dict, Any


def run() -> Dict[str, Any]:
    """优先跑 AI 融合策略写入 trade_signals；无结果时用 market_signals 聚合回退。"""
    result = {
        "fusion": 0,
        "fallback": 0,
        "errors": [],
        "strategy_market_seed": 0,
    }
    if os.environ.get("NEWHIGH_AUTO_STRATEGY_MARKET", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        try:
            from data_pipeline.strategy_market_writer import ensure_baseline_strategy_market_rows

            result["strategy_market_seed"] = ensure_baseline_strategy_market_rows(min_rows=2)
        except (ImportError, RuntimeError, OSError, ValueError, TypeError) as e:
            result["errors"].append(f"strategy_market_seed: {e}")
    try:
        from strategy_engine.ai_fusion_strategy import run_ai_fusion

        n = run_ai_fusion()
        if n > 0:
            result["fusion"] = n
            return result
    except ImportError as e:
        result["errors"].append(str(e))
    except (RuntimeError, ValueError, TypeError, OSError) as e:
        result["errors"].append(f"fusion: {e}")

    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if os.path.isfile(get_db_path()):
            conn = get_conn(read_only=False)
            df = conn.execute("SELECT code, signal_type, score FROM market_signals").fetchdf()
            conn.close()
            if df is not None and not df.empty:
                from strategy_engine.trade_signal_aggregator import (
                    aggregate_market_signals_to_trade_signals,
                )

                signals = df.to_dict(orient="records")
                trades = aggregate_market_signals_to_trade_signals(signals, top_n=20)
                conn = get_conn(read_only=False)
                conn.execute("DELETE FROM trade_signals WHERE strategy_id = ?", ["market_agg"])
                for code, sig, conf, tp, sl in trades:
                    conn.execute(
                        """INSERT INTO trade_signals
                           (code, signal, confidence, target_price, stop_loss, strategy_id, signal_score)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        [code, sig, conf, tp, sl, "market_agg", 0.5],
                    )
                conn.close()
                result["fallback"] = len(trades)
    except (RuntimeError, ValueError, TypeError, OSError) as e:
        result["errors"].append(f"fallback: {e}")

    return result
