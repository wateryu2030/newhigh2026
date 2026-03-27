#!/usr/bin/env python3
"""
将反量化 / 筹码候选写入 trade_signals，strategy_id = shareholder_chip。
仅删除并覆盖该 strategy_id 的行，不影响 ai_fusion 等其他策略写入的数据。

用法：
  python3 scripts/push_shareholder_chip_signals.py
  python3 scripts/push_shareholder_chip_signals.py --limit 80 --min-top10-ratio 50

依赖：与 GET /financial/anti-quant-pool 相同的 lib 流水线（top_10_shareholders 等）。

环境变量：
  NEWHIGH_PUSH_SHAREHOLDER_CHIP_SIGNALS=0  外层可跳过（调度器内判断）
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _setup_path() -> None:
    os.chdir(ROOT)
    for p in (
        str(ROOT),
        str(ROOT / "lib"),
        str(ROOT / "data-pipeline" / "src"),
        str(ROOT / "strategy" / "src"),
        str(ROOT / "core" / "src"),
    ):
        if p not in sys.path:
            sys.path.insert(0, p)


def normalize_code(raw: str) -> str:
    s = "".join(ch for ch in str(raw) if ch.isdigit())
    if len(s) >= 6:
        return s[:6]
    if s:
        return s.zfill(6)
    return ""


def main() -> int:
    _setup_path()

    try:
        from newhigh_env import load_dotenv_if_present

        load_dotenv_if_present(ROOT)
    except ImportError:
        pass

    parser = argparse.ArgumentParser(description="Push anti-quant chip pool to trade_signals")
    parser.add_argument("--limit", type=int, default=100, help="最多写入条数（与池接口默认一致）")
    parser.add_argument(
        "--min-top10-ratio",
        type=float,
        default=50.0,
        help="持股集中度下限 %%（与 anti-quant-pool 默认一致）",
    )
    args = parser.parse_args()

    import pandas as pd
    from core.types import Signal
    from lib.anti_quant_strategy import CONFIG, calc_top10_ratio, load_data_from_duckdb, run_strategy
    from lib.database import ensure_core_tables, get_connection
    from lib.shareholder_chip_metrics import enrich_candidates_chip
    from strategy_engine.price_reference import buy_target_stop_from_last, get_last_price

    factors, candidates = run_strategy()
    if candidates is None or candidates.empty:
        print("push_shareholder_chip: run_strategy 无候选，跳过写入")
        return 0

    candidates = candidates[candidates["top10_ratio_latest"] >= args.min_top10_ratio].copy()
    if candidates.empty:
        print(f"push_shareholder_chip: top10_ratio>={args.min_top10_ratio}% 无候选")
        return 0

    candidates = candidates.head(args.limit)

    try:
        raw_chip = load_data_from_duckdb()
        _cut = pd.Timestamp.now() - pd.DateOffset(years=CONFIG["years_back"])
        raw_chip = raw_chip[raw_chip["report_date"] >= _cut].copy()
        ratio_chip = calc_top10_ratio(raw_chip)
        candidates = enrich_candidates_chip(raw_chip, ratio_chip, candidates)
    except Exception as e:
        print(f"push_shareholder_chip: 筹码 enrich 跳过 ({e})")

    conn = get_connection(read_only=False)
    if conn is None:
        print("push_shareholder_chip: 数据库连接失败", file=sys.stderr)
        return 1

    ensure_core_tables(conn)
    conn.execute("DELETE FROM trade_signals WHERE strategy_id = ?", ["shareholder_chip"])

    inserted = 0
    for _, row in candidates.iterrows():
        code = normalize_code(row.get("stock_code", ""))
        if not code:
            continue
        chip = float(row["chip_score"]) if pd.notna(row.get("chip_score")) else None
        top10 = float(row.get("top10_ratio_latest", 0) or 0)
        base = chip if chip is not None else top10
        signal_score = round(float(base), 4)
        confidence = min(0.99, max(0.05, float(base) / 100.0))

        last = get_last_price(code) or 0.0
        target_price, stop_loss = buy_target_stop_from_last(last)

        conn.execute(
            """INSERT INTO trade_signals
               (code, signal, confidence, target_price, stop_loss, strategy_id, signal_score)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [code, Signal.BUY.value, confidence, target_price, stop_loss, "shareholder_chip", signal_score],
        )
        inserted += 1

    conn.close()

    analyzed = len(factors) if factors is not None and not getattr(factors, "empty", True) else 0
    print(
        f"push_shareholder_chip: 写入 {inserted} 条（strategy_id=shareholder_chip），"
        f"全库分析标的约 {analyzed}，min_top10={args.min_top10_ratio}%，limit={args.limit}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
