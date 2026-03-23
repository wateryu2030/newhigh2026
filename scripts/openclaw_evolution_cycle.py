#!/usr/bin/env python3
"""
OpenClaw 自我进化单轮执行 — 按 OPENCLAW_MASTER_SYSTEM / OPENCLAW_AUTONOMOUS_DEV 规则运行。

一轮包含（dev_loop + strategy_loop，可选 data_loop）：
  1. read_project_plan：加载控制文件摘要
  2. ensure_data_completeness：缺数据时从 akshare/北交所 等自动拉取并写入本地 DuckDB（保证分析数据完整）
  3. run_tests：必须通过（validation.must_pass_tests）
  4. strategy_loop：generate_strategies → backtest → score_alpha → evolve → deploy
  5. 可选 data_loop：data_update → feature_generation
  6. 写状态到 scripts/.openclaw_state.json 供下一轮/Cursor 续跑

用法（在 newhigh 仓库根目录，已激活 .venv）：
  python scripts/openclaw_evolution_cycle.py
  python scripts/openclaw_evolution_cycle.py --skip-tests
  python scripts/openclaw_evolution_cycle.py --no-ensure-data   # 跳过数据补全（quant + market）
  python scripts/openclaw_evolution_cycle.py --no-features     # 跳过特征计算落库
  python scripts/openclaw_evolution_cycle.py --data-loop
  每轮会执行：ensure_ashare_data_completeness（quant_system.duckdb）、ensure_market_data（quant_system.duckdb 仅池+涨停/龙虎榜/资金流）、data_health_check（表条数写入 .openclaw_state.json）
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(ROOT, "scripts", ".openclaw_state.json")


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{ts}] {msg}", flush=True)


def read_project_plan() -> dict:
    """加载 OPENCLAW 控制文件摘要（不解析 YAML，仅列出存在性）。"""
    configs = [
        "OPENCLAW_MASTER_SYSTEM.yaml",
        "OPENCLAW_AUTONOMOUS_DEV.yaml",
        "OPENCLAW_AI_DEV_AGENT.yaml",
        "OPENCLAW_DATA_PIPELINE.yaml",
        "OPENCLAW_ALPHA_FACTORY.yaml",
        "OPENCLAW_META_FUND.yaml",
        "OPENCLAW_TASK_TREE.yaml",
        "FRONTEND_DATA_BINDING.yaml",
    ]
    found = []
    for name in configs:
        p = os.path.join(ROOT, name)
        if os.path.isfile(p):
            found.append(name)
    return {"configs_found": found, "root": ROOT}


def ensure_data_completeness() -> dict:
    """缺数据时从 akshare/北交所 等拉取并写入 DuckDB（quant_system.duckdb），保证分析数据完整。"""
    script = os.path.join(ROOT, "scripts", "ensure_ashare_data_completeness.py")
    if not os.path.isfile(script):
        _log("ensure_ashare_data_completeness.py not found; skip data fill")
        return {"filled": 0, "skipped": 0, "errors": 0}
    _log("Ensuring A-share/BSE data completeness (akshare + local DuckDB)...")
    r = subprocess.run(
        [sys.executable, script, "--max-symbols", "300"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=600,
    )
    out = (r.stdout or "").strip() + (r.stderr or "").strip()
    if out:
        for line in out.splitlines()[:15]:
            _log(line)
    return {"ok": r.returncode == 0, "returncode": r.returncode}


def ensure_market_data() -> dict:
    """填充 quant_system.duckdb（股票池、涨停/龙虎榜/资金流），支撑情绪/狙击/AI 交易页。快速模式避免长时间阻塞。"""
    script = os.path.join(ROOT, "scripts", "ensure_market_data.py")
    if not os.path.isfile(script):
        _log("ensure_market_data.py not found; skip market data fill")
        return {"ok": False, "returncode": -1}
    _log("Ensuring quant_system.duckdb (stock list + limitup/longhubang/fundflow)...")
    r = subprocess.run(
        [sys.executable, script, "--skip-kline"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    out = (r.stdout or "").strip() + (r.stderr or "").strip()
    if out:
        for line in out.splitlines()[:10]:
            _log(line)
    return {"ok": r.returncode == 0, "returncode": r.returncode}


def data_health_check() -> dict:
    """检查关键表数据量，写入 state 供下一轮或 Cursor 改进优先级。"""
    health = {}
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path

        if not os.path.isfile(get_db_path()):
            health["market_db"] = "missing"
            return health
        conn = get_conn(read_only=False)
        for table in [
            "a_stock_basic",
            "a_stock_daily",
            "a_stock_limitup",
            "market_emotion",
            "sniper_candidates",
            "trade_signals",
        ]:
            try:
                row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                health[table] = int(row[0]) if row and row[0] is not None else 0
            except Exception:
                health[table] = -1
        conn.close()
    except Exception as e:
        health["error"] = str(e)
    return health


def run_tests() -> bool:
    """执行 scripts/run_tests.sh；必须通过才继续进化。"""
    script = os.path.join(ROOT, "scripts", "run_tests.sh")
    if not os.path.isfile(script):
        _log("run_tests.sh not found; skipping tests")
        return True
    _log("Running tests (OPENCLAW validation: must_pass_tests)...")
    r = subprocess.run(["bash", script], cwd=ROOT)
    return r.returncode == 0


def run_strategy_loop() -> list[str]:
    """连接 pipeline 并执行 strategy_loop（run_evolution_pipeline）。"""
    _log("Strategy loop: connect_pipeline -> run_evolution_pipeline")
    # 优先注入 scheduler/src 路径
    scheduler_src = os.path.join(ROOT, "scheduler", "src")
    if os.path.isdir(scheduler_src) and scheduler_src not in sys.path:
        sys.path.insert(0, scheduler_src)
    sys.path.insert(0, ROOT)
    try:
        from scheduler import connect_pipeline
    except ImportError:
        # 若未安装 scheduler 包，用路径注入
        for d in ["scheduler/src", "core/src", "data-engine/src", "gateway/src"]:
            p = os.path.join(ROOT, d)
            if os.path.isdir(p) and p not in sys.path:
                sys.path.insert(0, p)
        from scheduler import connect_pipeline  # type: ignore
    s = connect_pipeline()
    ran = s.run_evolution_pipeline()
    _log("Evolution steps completed: " + ", ".join(ran))
    return ran


def run_compute_features_to_duckdb() -> dict:
    """从 daily_bars 计算特征写入 features_daily，供策略/回测与持续训练使用。"""
    script = os.path.join(ROOT, "scripts", "compute_features_to_duckdb.py")
    if not os.path.isfile(script):
        _log("compute_features_to_duckdb.py not found; skip feature write")
        return {"written": 0, "symbols_processed": 0, "errors": 0}
    _log("Computing features (daily_bars -> features_daily)...")
    r = subprocess.run(
        [sys.executable, script, "--limit", "500", "--max-symbols", "200"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=900,
    )
    out = (r.stdout or "").strip() + (r.stderr or "").strip()
    if out:
        for line in out.splitlines()[:10]:
            _log(line)
    return {"ok": r.returncode == 0, "returncode": r.returncode}


def run_data_loop() -> list[str]:
    """执行 data_loop 片段：data_update -> feature_generation。"""
    _log("Data loop: run_pipeline(data_update, feature_generation)")
    sys.path.insert(0, ROOT)
    try:
        from scheduler import connect_pipeline
    except ImportError:
        for d in ["scheduler/src", "core/src", "data-engine/src"]:
            p = os.path.join(ROOT, d)
            if os.path.isdir(p) and p not in sys.path:
                sys.path.insert(0, p)
        from scheduler import connect_pipeline  # type: ignore
    s = connect_pipeline()
    ran = s.run_pipeline("data_update", "feature_generation")
    _log("Data steps completed: " + ", ".join(ran))
    return ran


def write_state(
    plan: dict,
    tests_ok: bool,
    strategy_ran: list[str],
    data_ran: list[str] | None,
    data_completeness: dict | None = None,
    market_data: dict | None = None,
    data_health: dict | None = None,
) -> None:
    """写入 .openclaw_state.json 供下一轮或 Cursor 读取。"""
    state = {
        "last_run": datetime.now(timezone.utc).isoformat(),
        "plan": plan,
        "tests_passed": tests_ok,
        "strategy_loop_steps": strategy_ran,
        "data_loop_steps": data_ran,
        "data_completeness": data_completeness,
        "market_data": market_data,
        "data_health": data_health,
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    _log("State written to " + STATE_FILE)


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenClaw self-evolution cycle")
    parser.add_argument("--skip-tests", action="store_true", help="Skip test run (not recommended)")
    parser.add_argument(
        "--no-ensure-data", action="store_true", help="Skip A-share/BSE data completeness step"
    )
    parser.add_argument(
        "--no-features",
        action="store_true",
        help="Skip feature compute (daily_bars -> features_daily)",
    )
    parser.add_argument(
        "--data-loop", action="store_true", help="Run data_loop after strategy_loop"
    )
    args = parser.parse_args()

    os.chdir(ROOT)
    plan = read_project_plan()
    _log("Project plan: " + json.dumps(plan.get("configs_found", [])))

    data_completeness = None
    market_data = None
    if not args.no_ensure_data:
        data_completeness = ensure_data_completeness()
        market_data = ensure_market_data()

    data_health = data_health_check()
    _log("Data health: " + json.dumps(data_health, ensure_ascii=False))

    if not args.no_features:
        run_compute_features_to_duckdb()

    if not args.skip_tests:
        if not run_tests():
            _log("Tests failed; aborting evolution (OPENCLAW validation)")
            write_state(plan, False, [], None, data_completeness, market_data, data_health)
            return 1
    else:
        _log("Tests skipped (--skip-tests)")

    strategy_ran = run_strategy_loop()
    data_ran = run_data_loop() if args.data_loop else None
    if args.data_loop and data_ran is not None:
        _log("Data loop completed: " + ", ".join(data_ran))

    write_state(
        plan,
        not args.skip_tests,
        strategy_ran,
        data_ran,
        data_completeness,
        market_data,
        data_health,
    )
    _log("OpenClaw evolution cycle finished.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
