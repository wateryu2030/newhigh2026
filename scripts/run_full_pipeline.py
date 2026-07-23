#!/usr/bin/env python3
"""全链路端到端测试：信号 → 风控 → 模拟下单 → 结果验证。
用法: cd /Users/apple/Ahope/newhigh && .venv/bin/python scripts/run_full_pipeline.py [--dry] [--verbose]
"""

from __future__ import annotations
import sys, os, time

# 确保所有模块可导入
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for d in ["data-pipeline/src", "risk-engine/src", "execution-engine/src",
           "strategy/src", "core/src"]:
    p = os.path.join(_ROOT, d)
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)


def banner(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def check_prerequisites():
    """检查前置条件：数据库连接、数据新鲜度、风险规则"""
    import duckdb
    from data_pipeline.storage.duckdb_manager import get_db_path

    db = get_db_path()
    if not os.path.exists(db):
        print(f"  FATAL: 数据库不存在 {db}")
        return False

    conn = duckdb.connect(db, read_only=True)

    # 信号
    sigs = conn.execute("SELECT COUNT(*) FROM trade_signals").fetchone()[0]
    recent = conn.execute("SELECT COUNT(*) FROM trade_signals WHERE snapshot_time > '2026-07-01'").fetchone()[0]
    print(f"  trade_signals: {sigs}条 (7月后{recent}条)")

    # 风险规则
    rules = conn.execute("SELECT COUNT(*) FROM risk_rules WHERE enabled=true").fetchone()[0]
    print(f"  risk_rules: {rules}条已启用")

    # 实时行情
    rt = conn.execute("SELECT COUNT(*), MAX(snapshot_time) FROM a_stock_realtime").fetchone()
    print(f"  a_stock_realtime: {rt[0]}条, 最新{rt[1]}")

    # K线
    kl = conn.execute("SELECT COUNT(*), MAX(date) FROM a_stock_daily").fetchone()
    print(f"  a_stock_daily: {kl[0]}条, 最新{kl[1]}")

    conn.close()
    return True


def check_signals():
    """查看当前信号状态"""
    import duckdb
    from data_pipeline.storage.duckdb_manager import get_db_path

    conn = duckdb.connect(get_db_path(), read_only=True)
    print(f"\n  {'Recent Signals':-^50}")
    df = conn.execute("""
        SELECT code, signal, signal_score, confidence,
               target_price, stop_loss, snapshot_time
        FROM trade_signals
        ORDER BY snapshot_time DESC LIMIT 10
    """).fetchdf()
    if df.empty:
        print("  (no signals)")
    else:
        for _, r in df.iterrows():
            print(f"  {r['code']:>8s} | {r['signal']:4s} | score={r['signal_score']:6.2f} | "
                  f"target={r['target_price']:8.2f} | stop={r['stop_loss']:8.2f} | {str(r['snapshot_time'])[:19]}")
    conn.close()


def check_sim_status():
    """查看模拟盘当前状态"""
    import duckdb
    from data_pipeline.storage.duckdb_manager import get_db_path

    conn = duckdb.connect(get_db_path(), read_only=True)

    # 账户
    snap = conn.execute("""
        SELECT snapshot_time, cash, equity, total_assets
        FROM sim_account_snapshots ORDER BY snapshot_time DESC LIMIT 1
    """).fetchone()
    if snap:
        print(f"\n  {'模拟账户':-^50}")
        print(f"  时间: {snap[0]}")
        print(f"  现金: {snap[1]:>12,.2f}")
        print(f"  持仓市值: {snap[2]:>12,.2f}")
        print(f"  总资产: {snap[3]:>12,.2f}")
    else:
        print(f"\n  {'模拟账户':-^50}")
        print(f"  (未初始化，将使用默认初始资金 1,000,000)")

    # 持仓
    pos = conn.execute("SELECT code, side, qty, avg_price FROM sim_positions ORDER BY qty DESC").fetchdf()
    if not pos.empty:
        print(f"\n  {'模拟持仓':-^50}")
        for _, r in pos.iterrows():
            mv = float(r['qty']) * float(r['avg_price'])
            print(f"  {r['code']:>8s} | {r['side']:4s} | {int(r['qty']):>6d}股 | "
                  f"均价{r['avg_price']:>8.2f} | 市值{mv:>12,.2f}")

    # 订单
    orders = conn.execute("SELECT id, code, side, qty, price, status, created_at FROM sim_orders ORDER BY created_at DESC LIMIT 10").fetchdf()
    if not orders.empty:
        print(f"\n  {'最近订单':-^50}")
        for _, r in orders.iterrows():
            print(f"  #{int(r['id'])} | {r['code']:>8s} | {r['side']:4s} | {int(r['qty']):>5d}股 | "
                  f"@{r['price']:>8.2f} | {r['status']} | {str(r['created_at'])[:19]}")

    conn.close()


def run_pipeline_step(dry_run: bool = True) -> dict:
    """执行一次全链路 step"""
    from execution_engine.simulated.engine import step_simulated

    return step_simulated(
        buy_threshold=0.0,    # 降低阈值以捕获所有信号
        sell_threshold=1.0,   # 提高卖出阈值（仅在信号明确卖出时卖出）
        initial_cash=1_000_000.0,
        lot_size=100,
        max_buys=20,
        max_sells=20,
        risk_check=True,      # 启用风控
    )


def run_risk_check():
    """单独验证风控"""
    from risk_engine.risk_monitor import evaluate_current
    return evaluate_current()


def main():
    dry_run = "--live" not in sys.argv
    verbose = "--verbose" in sys.argv

    print("=" * 60)
    print("  红山量化平台 - 全链路端到端测试")
    print(f"  模式: {'模拟 (dry_run)' if dry_run else '实盘 (live)'}")
    print(f"  时间: {__import__('datetime').datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 60)

    # 1. 前置检查
    banner("1/5 前置条件检查")
    if not check_prerequisites():
        print("\n  FATAL: 前置条件不满足，退出")
        return 1

    # 2. 查看当前信号
    banner("2/5 当前信号")
    check_signals()

    # 3. 风控独立检查
    banner("3/5 风控预检")
    risk_result = run_risk_check()
    if risk_result.get("pass"):
        print("  ✅ 风控通过")
    else:
        print(f"  ❌ 风控拦截: {len(risk_result.get('violations', []))} 条违规")
        for v in risk_result.get('violations', []):
            print(f"     - {v.get('message', str(v))}")

    # 4. 执行全链路
    banner("4/5 执行全链路 step")
    t0 = time.time()
    result = run_pipeline_step(dry_run=dry_run)
    elapsed = time.time() - t0

    print(f"\n  执行结果:")
    print(f"  {'✅ 成功' if result.get('ok') else '❌ 失败'}")
    print(f"  耗时: {elapsed:.1f}s")
    if 'orders_created' in result:
        print(f"  生成订单: {result['orders_created']}")
    if result.get('risk_violations'):
        print(f"  风控违规: {len(result['risk_violations'])}")
        for v in result['risk_violations']:
            print(f"     - {v.get('message', str(v))}")
    if result.get('cash'):
        print(f"  现金: {result.get('cash', 0):,.2f}")
    if result.get('equity'):
        print(f"  持仓市值: {result.get('equity', 0):,.2f}")
    if result.get('total_assets'):
        print(f"  总资产: {result.get('total_assets', 0):,.2f}")
    if result.get('error'):
        print(f"  错误: {result['error']}")

    # 5. 验证最终状态
    banner("5/5 最终状态验证")
    check_sim_status()

    print(f"\n{'='*60}")
    print(f"  全链路测试完成")
    print(f"{'='*60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
