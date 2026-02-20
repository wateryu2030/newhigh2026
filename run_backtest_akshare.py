#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的回测入口 - 使用 AKShare 数据源
核心目标：让用户能够自主选择 A 股股票进行量化分析

用法：
    python run_backtest_akshare.py <策略文件> <开始日期> <结束日期> [股票代码]

示例：
    python run_backtest_akshare.py strategies/simple_akshare_strategy.py 2024-01-01 2024-12-31 600745.XSHG
"""
import sys
import os
import subprocess

_root = os.path.dirname(os.path.abspath(__file__))
os.chdir(_root)


def main():
    if len(sys.argv) < 4:
        print("用法: python run_backtest_akshare.py <策略文件> <开始日期> <结束日期> [股票代码]")
        print("示例: python run_backtest_akshare.py strategies/simple_akshare_strategy.py 2024-01-01 2024-12-31 600745.XSHG")
        sys.exit(1)
    
    strategy_file = sys.argv[1]
    start_date = sys.argv[2]
    end_date = sys.argv[3]
    stock_code = sys.argv[4] if len(sys.argv) > 4 else None
    
    if not os.path.exists(strategy_file):
        print(f"❌ 策略文件不存在: {strategy_file}")
        sys.exit(1)
    
    strategy_abs = os.path.abspath(strategy_file)
    
    print("=" * 60)
    print("🚀 量化回测 - AKShare 数据源")
    print("=" * 60)
    print(f"策略文件: {strategy_file}")
    print(f"回测期间: {start_date} 至 {end_date}")
    if stock_code:
        print(f"股票代码: {stock_code}")
    print("=" * 60)
    
    # 设置股票代码环境变量
    if stock_code:
        os.environ['STOCK_CODE'] = stock_code
    
    # 找到 venv 的 site-packages（参考 run_backtest_db.py）
    site = next((p for p in sys.path if "venv" in p and "site-packages" in p), None)
    if not site:
        print("❌ 未找到 venv，请先激活虚拟环境: source venv/bin/activate")
        sys.exit(1)
    
    # 构建 Python 代码字符串（使用子进程方式，避免导入路径问题）
    # 关键：先导入 rqalpha（在 /tmp 目录），然后再切换到项目目录
    code = f'''
import sys, os
root = {repr(_root)}
strategy_abs_path = {repr(strategy_abs)}
stock_code = {repr(stock_code)}

# 关键：先导入 rqalpha（此时 cwd 仍为 /tmp，避免路径冲突）
# 需要将 rqalpha 目录添加到路径（RQAlpha 是克隆的仓库，不是通过 pip 安装的）
sys.path.insert(0, os.path.join(root, "rqalpha"))
from rqalpha import run_func
from rqalpha.environment import Environment
import rqalpha.main as rqmain_module

# 然后切换到项目目录
os.chdir(root)
sys.path.insert(0, root)

# 设置股票代码环境变量
if stock_code:
    os.environ['STOCK_CODE'] = stock_code

# 导入 AKShare 数据源 Mod
from data_source.akshare_data_source_mod import AKShareDataSourceMod

# 导入策略函数
import importlib.util
spec = importlib.util.spec_from_file_location("strategy", strategy_abs_path)
strategy_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strategy_module)

# 配置：使用 AKShare 数据源 Mod
config = {{
    "base": {{
        "start_date": {repr(start_date)},
        "end_date": {repr(end_date)},
        "frequency": "1d",
        "accounts": {{"stock": 1000000}},
    }},
    "mod": {{
        "sys_analyser": {{"enabled": True}},
        "sys_progress": {{"enabled": True}},
        "sys_simulation": {{"enabled": True}},
        "sys_accounts": {{"enabled": True}},
        "akshare_data_source": {{
            "enabled": True,
            "lib": "data_source.akshare_data_source_mod",
            "cache_ttl_hours": 1,
        }},
    }},
    "extra": {{
        "stock_code": stock_code,
        "log_level": "INFO",
    }},
}}

# 构建 user_funcs，只包含存在的函数
user_funcs = {{
    "init": strategy_module.init,
    "handle_bar": strategy_module.handle_bar,
}}
if hasattr(strategy_module, "before_trading") and strategy_module.before_trading is not None:
    user_funcs["before_trading"] = strategy_module.before_trading
if hasattr(strategy_module, "after_trading") and strategy_module.after_trading is not None:
    user_funcs["after_trading"] = strategy_module.after_trading

try:
    print("\\n✅ 开始回测...\\n")
    result = run_func(config=config, **user_funcs)
    print("\\n" + "=" * 60)
    print("✅ 回测完成！")
    print("=" * 60)
    if result:
        # RQAlpha 返回 result[mod_name]，分析结果在 sys_analyser.summary
        summary = (result.get("sys_analyser") or {{}}).get("summary") or {{}}
        tr = summary.get("total_returns")
        ar = summary.get("annualized_returns")
        md = summary.get("max_drawdown")
        sr = summary.get("sharpe")
        print("\\n回测结果:")
        print(f"  总收益率: {{tr:.2%}}" if tr is not None else "  总收益率: N/A")
        print(f"  年化收益率: {{ar:.2%}}" if ar is not None else "  年化收益率: N/A")
        print(f"  最大回撤: {{md:.2%}}" if md is not None else "  最大回撤: N/A")
        print(f"  夏普比率: {{sr:.2f}}" if sr is not None and sr == sr else "  夏普比率: N/A")
except Exception as e:
    print(f"\\n❌ 回测失败:")
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''
    
    env = {**os.environ}
    env["PYTHONPATH"] = site  # 只使用 venv 的 site-packages，避免路径冲突
    
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd="/tmp",  # 使用 /tmp 作为工作目录，避免路径冲突
            env=env,
        )
        sys.exit(result.returncode)
    except Exception as e:
        print(f"❌ 回测失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
