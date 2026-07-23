#!/usr/bin/env python3
"""批量回测：对所有 trade_signals 中的信号股跑回测，结果写入 backtest_runs + strategy_market。"""

import sys
import os
import uuid
from datetime import datetime

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backtest-engine", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data-pipeline", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import duckdb
import pandas as pd
from backtest_engine.run_with_db import run_backtest_from_db

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "quant_system.duckdb")


def get_signal_stocks(conn) -> pd.DataFrame:
    """获取所有去重的 (code, strategy_id) 组合。"""
    return conn.execute("""
        SELECT DISTINCT code, strategy_id
        FROM trade_signals
        WHERE signal ILIKE '%buy%' OR signal ILIKE '%long%'
        ORDER BY strategy_id, code
    """).fetchdf()


def save_backtest_run(conn, run_id, strategy_id, symbol, start, end, result):
    """保存单次回测结果到 backtest_runs。"""
    conn.execute("""
        INSERT INTO backtest_runs (run_id, strategy_id, symbol, start_date, end_date,
                                   sharpe_ratio, return_pct, max_drawdown_pct, win_rate_pct, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        run_id,
        strategy_id,
        symbol,
        start,
        end,
        result.get("sharpe_ratio"),
        result.get("total_return"),
        result.get("max_drawdown"),
        result.get("win_rate_pct"),
        datetime.now(),
    ])


def update_strategy_market(conn, strategy_id, aggregated):
    """更新 strategy_market 的策略汇总指标（INSERT OR REPLACE）。"""
    conn.execute("""
        INSERT OR REPLACE INTO strategy_market (strategy_id, name, return_pct, sharpe_ratio, max_drawdown, status, updated_at)
        VALUES (?, ?, ?, ?, ?, 'active', ?)
    """, [
        strategy_id,
        strategy_id.replace("_", " ").title(),
        aggregated.get("return_pct"),
        aggregated.get("sharpe_ratio"),
        aggregated.get("max_drawdown"),
        datetime.now(),
    ])


def main():
    start_date = "2023-01-01"
    end_date = "2026-07-22"

    conn = duckdb.connect(DB_PATH, read_only=False)
    stocks = get_signal_stocks(conn)
    print(f"共 {len(stocks)} 只信号股待回测")

    results_by_strategy = {}  # strategy_id -> list of result dicts
    success = 0
    fail = 0

    for _, row in stocks.iterrows():
        code = row["code"]
        strategy_id = row["strategy_id"]
        run_id = str(uuid.uuid4())[:8]

        print(f"  回测 {code} (strategy={strategy_id})...", end=" ")

        r = run_backtest_from_db(
            symbol=code,
            start_date=start_date,
            end_date=end_date,
            signal_source="trade_signals",
            strategy_id=strategy_id,
            init_cash=100000.0,
            fees=0.001,
            stop_loss_pct=0.08,
            conn=conn,  # 复用主连接，避免 DuckDB 配置冲突
        )

        if r.get("error"):
            print(f"FAILED: {r['error']}")
            fail += 1
            continue

        print(f"OK  return={r.get('total_return',0)*100:.2f}%  sharpe={r.get('sharpe_ratio')}  trades={r.get('trade_count')}")
        success += 1

        # 保存到 backtest_runs
        save_backtest_run(conn, run_id, strategy_id, code, start_date, end_date, r)

        # 汇总到 strategy
        if strategy_id not in results_by_strategy:
            results_by_strategy[strategy_id] = []
        results_by_strategy[strategy_id].append(r)

    # 汇总每个策略的指标
    print("\n=== 策略汇总 ===")
    for sid, results in results_by_strategy.items():
        valid = [r for r in results if r.get("total_return") is not None]
        if not valid:
            print(f"  {sid}: 无有效结果")
            continue

        avg_return = sum(r["total_return"] for r in valid) / len(valid)
        avg_sharpe = sum(r["sharpe_ratio"] for r in valid if r["sharpe_ratio"] is not None) / max(1, len([r for r in valid if r["sharpe_ratio"] is not None]))
        # max_drawdown: 取最差（最小）的
        dds = [r["max_drawdown"] for r in valid if r["max_drawdown"] is not None]
        avg_dd = sum(dds) / len(dds) if dds else None

        print(f"  {sid}: {len(valid)}只 | avg_return={avg_return*100:.2f}% | avg_sharpe={avg_sharpe:.2f} | avg_maxdd={avg_dd*100:.2f}%" if avg_dd else f"  {sid}: {len(valid)}只 | avg_return={avg_return*100:.2f}% | avg_sharpe={avg_sharpe:.2f}")

        aggregated = {
            "return_pct": avg_return,
            "sharpe_ratio": avg_sharpe,
            "max_drawdown": avg_dd,
        }
        update_strategy_market(conn, sid, aggregated)

    print(f"\n总计: {success} 成功, {fail} 失败")
    conn.close()


if __name__ == "__main__":
    main()
