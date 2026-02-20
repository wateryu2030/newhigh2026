#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行回测脚本 - 使用 RQAlpha 运行策略

用法: python run_backtest.py <策略文件> [开始日期] [结束日期]
示例: python run_backtest.py strategies/strategy_wentai_demo.py 2024-01-01 2024-12-31
"""
import sys
import os
import subprocess

_root = os.path.dirname(os.path.abspath(__file__))


def main():
    if len(sys.argv) < 2:
        print("用法: python run_backtest.py <策略文件> [开始日期] [结束日期]")
        print("示例: python run_backtest.py strategies/strategy_wentai_demo.py 2024-01-01 2024-12-31")
        sys.exit(1)

    strategy_file = sys.argv[1]
    start_date = sys.argv[2] if len(sys.argv) > 2 else "2024-01-01"
    end_date = sys.argv[3] if len(sys.argv) > 3 else "2024-12-31"

    if not os.path.exists(strategy_file):
        print(f"策略文件不存在: {strategy_file}")
        sys.exit(1)

    os.makedirs(os.path.join(_root, "output"), exist_ok=True)
    os.makedirs(os.path.join(_root, "bundle"), exist_ok=True)
    strategy_abs = os.path.abspath(strategy_file)

    bundle_path = os.path.join(_root, "bundle")
    if not os.path.isdir(bundle_path) or not os.listdir(bundle_path):
        print("提示: 回测需要历史数据包。若尚未下载，请先执行：")
        print("  rqalpha update-bundle")
        print("（需配置数据源。若仅做策略语法测试，可忽略）")
        print()

    print(f"运行策略: {strategy_file}")
    print(f"回测期间: {start_date} 至 {end_date}")
    print("-" * 50)

    # 在子进程中运行，避免当前目录遮蔽 rqalpha 导致 ImportError
    runner = os.path.join(_root, "scripts", "run_backtest_impl.py")
    if not os.path.exists(runner):
        # 内联实现：用 -c 执行，且把工作目录设为非项目根
        code = f'''
import sys, os
root = {repr(_root)}
strategy_abs_path = {repr(strategy_abs)}
# 先导入 rqalpha（此时 cwd 仍为 /tmp，sys.path[0] 不会指向项目根）
from rqalpha import run_file
os.chdir(root)
config = {{
    "base": {{
        "strategy_file": strategy_abs_path,
        "start_date": {repr(start_date)},
        "end_date": {repr(end_date)},
        "frequency": "1d",
        "accounts": {{"stock": 1000000}},
        "data_bundle_path": os.path.join(root, "bundle"),
    }},
    "mod": {{
        "sys_analyser": {{"enabled": True}},
        "sys_progress": {{"enabled": True}},
        "sys_simulation": {{"enabled": True}},
        "sys_accounts": {{"enabled": True}},
    }},
    "extra": {{"log_level": "INFO"}},
}}
run_file(strategy_abs_path, config)
print("\\n回测完成！")
'''
        try:
            site = next((p for p in sys.path if "venv" in p and "site-packages" in p), None)
            env = {**os.environ}
            # 仅使用 site-packages，不加入项目根，否则会加载到 astock/rqalpha（仓库根）而非 rqalpha 包
            if site:
                env["PYTHONPATH"] = site
            r = subprocess.run(
                [sys.executable, "-c", code],
                cwd="/tmp",
                env=env,
            )
            sys.exit(r.returncode)
        except Exception as e:
            print(f"回测失败: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    try:
        r = subprocess.run(
            [sys.executable, runner, strategy_abs, start_date, end_date],
            cwd=_root,
        )
        sys.exit(r.returncode)
    except Exception as e:
        print(f"回测失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
