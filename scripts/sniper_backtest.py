#!/usr/bin/env python3
"""
游资狙击回测：T 日识别 → T+1 买入 → T+3 卖出。
输出：胜率、平均收益、最大回撤（占位）。
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in ["data-pipeline/src", "market-scanner/src"]:
    p = os.path.join(ROOT, d)
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)


def load_sniper_signals(limit: int = 200) -> list:
    """从 sniper_candidates 历史或当前快照加载（当前实现为当前快照）。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        if not os.path.isfile(get_db_path()):
            return []
        conn = get_conn(read_only=True)
        df = conn.execute(
            "SELECT code, theme, sniper_score, confidence FROM sniper_candidates ORDER BY sniper_score DESC LIMIT ?",
            [limit],
        ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")
    except Exception:
        return []


def get_price(conn, code: str, date) -> float | None:
    """取 code 在 date 的收盘价。"""
    try:
        row = conn.execute(
            "SELECT close FROM a_stock_daily WHERE code = ? AND date = ?",
            [code, date],
        ).fetchone()
        return float(row[0]) if row and row[0] is not None else None
    except Exception:
        return None


def sniper_backtest(holding_days: int = 3) -> dict:
    """
    T 日信号 → T+1 买入、T+holding_days 卖出，统计胜率与平均收益。
    注意：当前 sniper_candidates 无历史日期，仅做当日信号与最近日线模拟。
    """
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        if not os.path.isfile(get_db_path()):
            return {"win_rate": None, "avg_return": None, "max_drawdown": None, "trades": 0}
        conn = get_conn(read_only=True)
        signals = load_sniper_signals()
        if not signals:
            conn.close()
            return {"win_rate": None, "avg_return": None, "max_drawdown": None, "trades": 0}

        # 取最近交易日
        latest = conn.execute("SELECT MAX(date) FROM a_stock_daily").fetchone()[0]
        if not latest:
            conn.close()
            return {"win_rate": None, "avg_return": None, "max_drawdown": None, "trades": 0}

        returns = []
        for s in signals:
            code = s.get("code")
            if not code:
                continue
            buy_price = get_price(conn, code, latest)
            if buy_price is None or buy_price <= 0:
                continue
            # T+holding_days：取之后第 holding_days 个交易日
            try:
                next_dates = conn.execute("""
                    SELECT date FROM a_stock_daily
                    WHERE code = ? AND date > ?
                    ORDER BY date LIMIT ?
                """, [code, latest, holding_days]).fetchdf()
                if next_dates is None or len(next_dates) < holding_days:
                    continue
                sell_date = next_dates["date"].iloc[holding_days - 1]
                sell_price = get_price(conn, code, sell_date)
                if sell_price is None or sell_price <= 0:
                    continue
                ret = sell_price / buy_price - 1
                returns.append(ret)
            except Exception:
                continue

        conn.close()
        if not returns:
            return {"win_rate": None, "avg_return": None, "max_drawdown": None, "trades": 0}
        win_rate = sum(1 for r in returns if r > 0) / len(returns)
        avg_return = sum(returns) / len(returns)
        # 最大回撤占位
        max_drawdown = None
        return {"win_rate": win_rate, "avg_return": avg_return, "max_drawdown": max_drawdown, "trades": len(returns)}
    except Exception as e:
        return {"win_rate": None, "avg_return": None, "max_drawdown": None, "trades": 0, "error": str(e)}


def main() -> int:
    result = sniper_backtest(holding_days=3)
    print("Sniper backtest (T+1 buy, T+3 sell):", result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
