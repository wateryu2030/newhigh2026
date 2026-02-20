#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用数据库数据源运行回测
"""
import sys
import os
import subprocess

_root = os.path.dirname(os.path.abspath(__file__))
os.chdir(_root)


def main():
    if len(sys.argv) < 2:
        print("用法: python run_backtest_db.py <策略文件> [开始日期] [结束日期]")
        print("示例: python run_backtest_db.py strategies/strategy_wentai_demo.py 2024-01-01 2024-06-30")
        sys.exit(1)

    strategy_file = sys.argv[1]
    start_date = sys.argv[2] if len(sys.argv) > 2 else "2024-01-01"
    end_date = sys.argv[3] if len(sys.argv) > 3 else "2024-12-31"

    if not os.path.exists(strategy_file):
        print(f"策略文件不存在: {strategy_file}")
        sys.exit(1)

    os.makedirs("output", exist_ok=True)
    strategy_abs = os.path.abspath(strategy_file)

    print(f"运行策略: {strategy_file}")
    print(f"回测期间: {start_date} 至 {end_date}")
    print("使用数据库数据源（SQLite）")
    print("-" * 50)

    # 检查数据库是否存在
    db_path = os.path.join(_root, "data", "astock.db")
    if not os.path.exists(db_path):
        print("⚠️  数据库不存在，正在获取数据...")
        from database.data_fetcher import DataFetcher
        fetcher = DataFetcher()
        fetcher.fetch_wentai_data()
        print("✅ 数据获取完成")

    site = next((p for p in sys.path if "venv" in p and "site-packages" in p), None)
    if not site:
        print("❌ 未找到 venv")
        sys.exit(1)

    code = f'''
import sys, os
root = {repr(_root)}
strategy_abs_path = {repr(strategy_abs)}
# 先导入 rqalpha（此时 cwd 仍为 /tmp）
from rqalpha import run_func
os.chdir(root)

# 导入策略函数
import importlib.util
spec = importlib.util.spec_from_file_location("strategy", strategy_abs_path)
strategy_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strategy_module)

# 导入数据库数据源 Mod
from database.db_data_source_mod import DatabaseDataSourceMod

# 配置：使用数据库数据源 Mod
config = {{
    "base": {{
        "start_date": {repr(start_date)},
        "end_date": {repr(end_date)},
        "frequency": "1d",
        "accounts": {{"stock": 1000000}},
    }},
    "mod": {{
        "sys_analyser": {{"enabled": True, "output_file": os.path.join(root, "output", "last_backtest_result.pkl")}},
        "sys_progress": {{"enabled": True}},
        "sys_simulation": {{"enabled": True}},
        "sys_accounts": {{"enabled": True}},
        "db_data_source": {{
            "enabled": True,
            "lib": "database.db_data_source_mod",
            "db_path": os.path.join(root, "data", "astock.db"),
        }},
    }},
    "extra": {{"log_level": "INFO", "stock_code": os.environ.get("STOCK_CODE", "")}},
}}

# 构建 user_funcs，只包含存在的函数（不包含 None）
user_funcs = {{
    "init": strategy_module.init,
    "handle_bar": strategy_module.handle_bar,
}}
if hasattr(strategy_module, "before_trading") and strategy_module.before_trading is not None:
    user_funcs["before_trading"] = strategy_module.before_trading
if hasattr(strategy_module, "after_trading") and strategy_module.after_trading is not None:
    user_funcs["after_trading"] = strategy_module.after_trading

try:
    result = run_func(config=config, **user_funcs)
    print("\\n✅ 回测完成！")
    # 写出 JSON 供 Web 展示（指标 + 净值曲线）
    import json
    import pickle
    pkl_path = os.path.join(root, "output", "last_backtest_result.pkl")
    json_path = os.path.join(root, "output", "last_backtest_result.json")
    if os.path.exists(pkl_path):
        with open(pkl_path, "rb") as f:
            rd = pickle.load(f)
        def _to_json(v):
            if v is None: return None
            if hasattr(v, "item"):
                x = v.item()
                if isinstance(x, float) and (x != x or abs(x) == 1e300): return None
                return _to_json(x) if isinstance(x, (dict, list, tuple)) else x
            if hasattr(v, "tolist"): return [_to_json(x) for x in v.tolist()]
            if isinstance(v, (list, tuple)): return [_to_json(x) for x in v]
            if isinstance(v, dict): return {{k: _to_json(x) for k, x in v.items()}}
            if isinstance(v, float) and (v != v or abs(v) == 1e300): return None
            import datetime
            if isinstance(v, (datetime.date, datetime.datetime)): return str(v)
            if hasattr(v, "start_date") and hasattr(v, "end_date"): return {{"start_date": str(v.start_date), "end_date": str(v.end_date)}}
            try: json.dumps(v); return v
            except (TypeError, ValueError): return str(v)
        summary = rd.get("summary") or {{}}
        out = {{"summary": {{k: _to_json(v) for k, v in summary.items()}}}}
        if "portfolio" in rd and rd["portfolio"] is not None:
            try:
                pf = rd["portfolio"]
                if hasattr(pf, "index"):
                    dates = [str(d)[:10] for d in pf.index]
                    nav = pf["unit_net_value"] if "unit_net_value" in getattr(pf, "columns", []) else pf.iloc[:, 0]
                    out["curve"] = [{{"date": d, "value": float(x) if x == x else None}} for d, x in zip(dates, nav)]
            except Exception:
                out["curve"] = []
        else:
            out["curve"] = []
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
except Exception as e:
    print(f"\\n⚠️  回测过程出错: {{e}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''

    env = {**os.environ}
    env["PYTHONPATH"] = site

    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd="/tmp",
            env=env,
        )
        sys.exit(result.returncode)
    except Exception as e:
        print(f"回测失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
