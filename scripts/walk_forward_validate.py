#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前 9 个月训练 + 后 3 个月验证的滚动验证。
结合现有数据，轮巡多标的×多策略，验证策略在样本外是否可行。

用法:
  python scripts/walk_forward_validate.py
  WF_MAX_STOCKS=5 python scripts/walk_forward_validate.py  # 只测 5 只
  python scripts/walk_forward_validate.py --csv output/wf_report.csv  # 输出 CSV
"""
import argparse
import csv
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)


def get_stocks_with_data(min_bars: int = 200) -> List[Tuple[str, str, str, int]]:
    """从 DuckDB 获取有足够数据的股票及日期范围。返回 [(order_book_id, start, end, count), ...]"""
    import duckdb
    db_path = os.path.join(ROOT, "data", "quant.duckdb")
    if not os.path.exists(db_path):
        return []
    conn = duckdb.connect(db_path, read_only=True)
    rows = conn.execute(
        """
        SELECT order_book_id, MIN(trade_date)::VARCHAR, MAX(trade_date)::VARCHAR, COUNT(*)
        FROM daily_bars GROUP BY order_book_id
        HAVING COUNT(*) >= ?
        ORDER BY COUNT(*) DESC
        """,
        [min_bars],
    ).fetchall()
    conn.close()
    return [(r[0], str(r[1]), str(r[2]), r[3]) for r in rows]


def split_9_3(start: str, end: str) -> Optional[Tuple[str, str, str, str]]:
    """
    将 [start, end] 分为前 9 月（训练）和后 3 月（验证）。
    返回 (train_start, train_end, test_start, test_end) 或 None。
    """
    try:
        d_start = datetime.strptime(start[:10], "%Y-%m-%d")
        d_end = datetime.strptime(end[:10], "%Y-%m-%d")
    except ValueError:
        return None
    delta = (d_end - d_start).days
    if delta < 300:  # 至少约 12 个月
        return None
    # 总区间约 12 个月，前 9 月 train，后 3 月 test
    split_d = d_start + timedelta(days=int(delta * 9 / 12))
    train_end = split_d.strftime("%Y-%m-%d")
    test_start = (split_d + timedelta(days=1)).strftime("%Y-%m-%d")
    return start[:10], train_end, test_start, end[:10]


def run_strategy_on_range(
    strategy_id: str,
    stock_code: str,
    start_date: str,
    end_date: str,
) -> Dict[str, Any]:
    """在指定区间运行插件策略回测，返回 stats。"""
    try:
        from run_backtest_plugins import run_plugin_backtest
        result = run_plugin_backtest(
            strategy_id=strategy_id,
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date,
            timeframe="D",
        )
        if result.get("error"):
            return {"error": result["error"], "total_return": None, "max_drawdown": None}
        s = result.get("stats", {})
        curve = result.get("curve", [])
        total_return = s.get("return", s.get("total_returns"))
        if total_return is None and curve:
            total_return = curve[-1].get("value", 1.0) - 1.0
        max_dd = s.get("maxDrawdown", s.get("max_drawdown"))
        if max_dd is None and curve:
            peak = 1.0
            max_dd = 0.0
            for p in curve:
                v = p.get("value", 1.0)
                if v > peak:
                    peak = v
                if peak > 0:
                    dd = (peak - v) / peak
                    if dd > max_dd:
                        max_dd = dd
        return {
            "error": None,
            "total_return": total_return if total_return is not None else 0.0,
            "max_drawdown": max_dd if max_dd is not None else 0.0,
            "trade_count": s.get("tradeCount", len(result.get("signals", []))),
        }
    except Exception as e:
        return {"error": str(e), "total_return": None, "max_drawdown": None}


def send_feishu(webhook_url: str, content: str, at_user_id: Optional[str] = None) -> bool:
    """发送飞书消息。webhook 从群机器人获取，at_user_id 可选（如 8db735f2）用于 @用户。"""
    try:
        import json
        import requests
        # 纯文本
        payload = {"msg_type": "text", "content": {"text": content}}
        if at_user_id:
            payload["content"]["text"] += f'\n<at user_id="{at_user_id}">余为军</at>'
        resp = requests.post(webhook_url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"飞书发送失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="前9月训练+后3月验证")
    parser.add_argument("--csv", help="输出 CSV 报告路径")
    parser.add_argument("--stocks", type=int, default=None, help="最多测试标的数")
    parser.add_argument("--strategies", default=None, help="指定策略，逗号分隔，如 macd,kdj（经验推荐）。默认全部")
    parser.add_argument("--feishu", action="store_true", help="结束后发送到飞书（需 FEISHU_WEBHOOK_URL 环境变量）")
    args = parser.parse_args()

    from strategies import PLUGIN_STRATEGIES

    all_strategies = list(PLUGIN_STRATEGIES.keys())
    if args.strategies:
        strategies = [s.strip() for s in args.strategies.split(",") if s.strip() and s.strip() in PLUGIN_STRATEGIES]
        if not strategies:
            strategies = all_strategies
    else:
        strategies = all_strategies
    stocks = get_stocks_with_data(min_bars=200)
    if not stocks:
        print("数据库无足够数据（需 >= 200 根日线），请先同步：")
        print("  python scripts/sync_pool_stocks.py --start 20240220 --end 20260220")
        return 1

    # 限制标的数量
    max_stocks = args.stocks or int(os.environ.get("WF_MAX_STOCKS", "10"))
    stocks = stocks[:max_stocks]

    print("=" * 70)
    print("前 9 月训练 + 后 3 月验证（样本外）")
    print("=" * 70)
    print(f"策略: {', '.join(strategies)}")
    print(f"标的: {len(stocks)} 只")
    print("-" * 70)

    results: List[Dict[str, Any]] = []

    for order_book_id, start, end, cnt in stocks:
        split = split_9_3(start, end)
        if not split:
            print(f"⏭ {order_book_id} 数据不足 12 月，跳过")
            continue
        train_start, train_end, test_start, test_end = split
        print(f"\n{order_book_id} | {start}~{end} | 训练 {train_start}~{train_end} | 验证 {test_start}~{test_end}")

        for sid in strategies:
            train_r = run_strategy_on_range(sid, order_book_id, train_start, train_end)
            test_r = run_strategy_on_range(sid, order_book_id, test_start, test_end)

            train_ret = train_r.get("total_return")
            test_ret = test_r.get("total_return")
            train_dd = train_r.get("max_drawdown")
            test_dd = test_r.get("max_drawdown")
            train_err = train_r.get("error")
            test_err = test_r.get("error")

            ok = train_err is None and test_err is None
            status = "✅" if ok else "❌"
            tr = f"{train_ret:.2%}" if train_ret is not None else "-"
            te = f"{test_ret:.2%}" if test_ret is not None else "-"
            td = f"{train_dd:.2%}" if train_dd is not None else "-"
            te_dd = f"{test_dd:.2%}" if test_dd is not None else "-"
            print(f"  {status} {sid:12} | 训练收益 {tr:>8} 回撤 {td:>7} | 验证收益 {te:>8} 回撤 {te_dd:>7}")
            if train_err:
                print(f"      训练错误: {train_err[:80]}")
            if test_err:
                print(f"      验证错误: {test_err[:80]}")

            results.append({
                "stock": order_book_id,
                "strategy": sid,
                "train_return": train_ret,
                "test_return": test_ret,
                "train_dd": train_dd,
                "test_dd": test_dd,
                "ok": ok,
            })

    # 汇总
    print("\n" + "=" * 70)
    print("汇总")
    print("=" * 70)
    ok_count = sum(1 for r in results if r["ok"])
    print(f"通过: {ok_count}/{len(results)}")
    strategy_summary: List[Tuple[str, float, int, int]] = []
    best = ("macd", 0.0, 0, 0)
    if results:
        by_strategy: Dict[str, List[float]] = {}
        for r in results:
            if r["ok"] and r["test_return"] is not None:
                by_strategy.setdefault(r["strategy"], []).append(r["test_return"])
        print("\n验证期收益（样本外）按策略平均:")
        for sid in strategies:
            vals = by_strategy.get(sid, [])
            avg = sum(vals) / len(vals) if vals else 0
            win = sum(1 for v in vals if v > 0)
            total = len(vals)
            print(f"  {sid:12} 平均 {avg:.2%}  胜率 {win}/{total}")
            strategy_summary.append((sid, avg, win, total))
        if strategy_summary:
            best = max(strategy_summary, key=lambda x: (x[2] / max(x[3], 1), x[1]))
        weak = [s for s, a, w, t in strategy_summary if a <= 0 or (t > 0 and w / t < 0.5)]
        print("\n策略建议:")
        print(f"  推荐优先: {best[0]} (验证期胜率 {best[2]}/{best[3]}, 平均收益 {best[1]:.2%})")
        if weak:
            print(f"  建议观望: {', '.join(weak)}")
        if "breakout" in strategies and by_strategy.get("breakout"):
            br_avg = sum(by_strategy["breakout"]) / len(by_strategy["breakout"])
            if br_avg == 0:
                print("  说明: breakout 多数标的无信号，可考虑调参或暂不使用")

    # 飞书通知
    feishu_url = os.environ.get("FEISHU_WEBHOOK_URL")
    if args.feishu:
        if not feishu_url:
            print("\n⚠ 未设置 FEISHU_WEBHOOK_URL，跳过飞书通知。请创建群机器人获取 webhook 并设置环境变量。")
        elif results and feishu_url:
            lines = [
                "【前9月+后3月验证结果】",
                f"通过: {ok_count}/{len(results)}",
            ]
            if strategy_summary:
                lines.append("验证期收益:")
                for sid, avg, win, total in strategy_summary:
                    lines.append(f"  {sid}: 平均{avg:.2%} 胜率{win}/{total}")
                lines.append(f"推荐策略: {best[0]}")
            if args.csv:
                lines.append(f"报告: {args.csv}")
            send_feishu(feishu_url, "\n".join(lines), at_user_id=os.environ.get("FEISHU_AT_USER_ID"))

    # 输出 CSV
    if args.csv and results:
        d = os.path.dirname(args.csv)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["stock", "strategy", "train_return", "test_return", "train_dd", "test_dd", "ok"])
            w.writeheader()
            for r in results:
                tr = r.get("train_return")
                te = r.get("test_return")
                td = r.get("train_dd")
                te_d = r.get("test_dd")
                w.writerow({
                    "stock": r["stock"],
                    "strategy": r["strategy"],
                    "train_return": f"{tr:.4f}" if tr is not None else "",
                    "test_return": f"{te:.4f}" if te is not None else "",
                    "train_dd": f"{td:.4f}" if td is not None else "",
                    "test_dd": f"{te_d:.4f}" if te_d is not None else "",
                    "ok": r.get("ok", False),
                })
        print(f"\n报告已保存: {args.csv}")

    return 0 if ok_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
