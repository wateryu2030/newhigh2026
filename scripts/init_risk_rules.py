#!/usr/bin/env python3
"""初始化风控规则表：写入行业默认风控参数。
用法: cd /Users/apple/Ahope/newhigh && .venv/bin/python scripts/init_risk_rules.py
"""

from __future__ import annotations

import datetime as dt
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data-pipeline", "src"))


def main():
    from data_pipeline.storage.duckdb_manager import get_conn, ensure_tables

    conn = get_conn(read_only=False)
    ensure_tables(conn)

    # 清空旧规则
    conn.execute("DELETE FROM risk_rules")
    print("  已清空旧规则")

    # 行业默认风控规则
    default_rules = [
        # (id, rule_type, value, 说明)
        (1, "single_position_pct_max", 0.20, "单票最大仓位 20%"),
        (2, "max_drawdown_pct", 0.15, "最大回撤 15%"),
        (3, "max_exposure_pct", 0.80, "总仓位上限 80%"),
        (4, "daily_loss_limit_pct", 0.05, "单日亏损上限 5%"),
        (5, "single_industry_pct_max", 0.30, "单一行业最大集中度 30%"),
        (6, "min_liquidity_rank", 500, "最低流动性排名（成交量前500）"),
        (7, "volatility_max_annualized", 0.60, "年化波动率上限 60%"),
    ]

    now = dt.datetime.now()
    for rule_id, rule_type, value, desc in default_rules:
        conn.execute(
            """INSERT INTO risk_rules (id, rule_type, value, enabled, updated_at)
               VALUES (?, ?, ?, true, ?)""",
            [rule_id, rule_type, value, now],
        )
        print(f"  ✅ {desc}: value={value} (id={rule_id})")

    n = conn.execute("SELECT COUNT(*) FROM risk_rules").fetchone()[0]
    conn.close()
    print(f"\n  共 {n} 条风控规则已初始化")


if __name__ == "__main__":
    main()
