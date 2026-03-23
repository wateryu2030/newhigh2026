#!/usr/bin/env python3
"""
AI 交易终端单轮：扫描 → AI 分析 → 策略聚合 → 写 trade_signals。
可与 data-pipeline 配合：先跑 pipeline 更新行情/涨停/资金流，再跑本脚本。
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in [
    "data-pipeline/src",
    "market-scanner/src",
    "ai-models/src",
    "strategy-engine/src",
    "core/src",
]:
    p = os.path.join(ROOT, d)
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)
# ai-optimizer 可选
_opt = os.path.join(ROOT, "ai-optimizer/src")
if os.path.isdir(_opt) and _opt not in sys.path:
    sys.path.insert(0, _opt)


def main() -> int:
    # 1) 市场扫描 + 游资狙击
    try:
        from market_scanner import (
            run_limit_up_scanner,
            run_fund_flow_scanner,
            run_volume_spike_scanner,
            run_trend_scanner,
            run_sniper,
        )

        n1 = run_limit_up_scanner()
        n2 = run_fund_flow_scanner()
        n3 = run_volume_spike_scanner()
        n4 = run_trend_scanner()
        n5 = run_sniper(min_score=0.7, top_n=50)
        print(f"Scanner: limitup={n1} fundflow={n2} volume={n3} trend={n4} sniper={n5}")
    except Exception as e:
        print("Scanner error:", e)

    # 2) AI 分析
    try:
        from ai_models import run_emotion_cycle, run_hotmoney_detector, run_sector_rotation_ai

        stage = run_emotion_cycle()
        h = run_hotmoney_detector()
        s = run_sector_rotation_ai()
        print(f"AI: emotion={stage} hotmoney={h} sector={s}")
    except Exception as e:
        print("AI error:", e)

    # 3) AI 融合策略 → trade_signals（含 signal_score）
    try:
        from strategy_engine.ai_fusion_strategy import run_ai_fusion

        n_fusion = run_ai_fusion()
        if n_fusion > 0:
            print(f"AI fusion trade signals: {n_fusion}")
        else:
            from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
            import os as _os

            if _os.path.isfile(get_db_path()):
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
                    conn.execute("DELETE FROM trade_signals")
                    for code, sig, conf, tp, sl in trades:
                        conn.execute(
                            "INSERT INTO trade_signals (code, signal, confidence, target_price, stop_loss, signal_score) VALUES (?, ?, ?, ?, ?, ?)",
                            [code, sig, conf, tp, sl, 0.5],
                        )
                    conn.close()
                    print(f"Trade signals (fallback): {len(trades)}")
    except Exception as e:
        print("Trade signals error:", e)

    print("Terminal loop done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
