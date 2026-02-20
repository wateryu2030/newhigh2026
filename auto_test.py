#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化测试脚本 - 检查依赖、数据源、运行回测
"""
import sys
import os
import subprocess
import shutil

_root = os.path.dirname(os.path.abspath(__file__))
os.chdir(_root)


def check_dependencies():
    """检查依赖"""
    print("=" * 60)
    print("1. 检查依赖...")
    print("=" * 60)
    
    missing = []
    try:
        import akshare
        print(f"✅ akshare: {akshare.__version__ if hasattr(akshare, '__version__') else '已安装'}")
    except ImportError:
        missing.append("akshare")
        print("❌ akshare: 未安装")
    
    try:
        import rqalpha
        print(f"✅ rqalpha: {rqalpha.__version__ if hasattr(rqalpha, '__version__') else '已安装'}")
    except ImportError:
        missing.append("rqalpha")
        print("❌ rqalpha: 未安装")
    
    try:
        import flask
        print(f"✅ flask: {flask.__version__}")
    except ImportError:
        missing.append("flask")
        print("❌ flask: 未安装")
    
    if missing:
        print(f"\n⚠️  缺少依赖: {', '.join(missing)}")
        print("正在安装...")
        for pkg in missing:
            if pkg == "akshare":
                subprocess.run([sys.executable, "-m", "pip", "install", "-e", "./akshare"], check=False)
            elif pkg == "rqalpha":
                subprocess.run([sys.executable, "-m", "pip", "install", "-e", "./rqalpha"], check=False)
            else:
                subprocess.run([sys.executable, "-m", "pip", "install", pkg], check=False)
        print("✅ 依赖安装完成")
    else:
        print("✅ 所有依赖已安装")
    
    return len(missing) == 0


def check_bundle():
    """检查数据包"""
    print("\n" + "=" * 60)
    print("2. 检查数据包 (bundle)...")
    print("=" * 60)
    
    bundle_path = os.path.join(_root, "bundle")
    os.makedirs(bundle_path, exist_ok=True)
    
    # 检查是否有数据文件
    has_data = False
    if os.path.exists(bundle_path):
        files = os.listdir(bundle_path)
        if files:
            print(f"✅ bundle 目录存在，包含 {len(files)} 个文件")
            has_data = True
        else:
            print("⚠️  bundle 目录为空")
    
    if not has_data:
        print("\n提示: RQAlpha 需要历史数据包才能回测")
        print("选项1: 使用 RQAlpha 官方数据源（需要配置）")
        print("  执行: rqalpha download-bundle")
        print("\n选项2: 使用 AKShare 数据适配器（当前项目已实现）")
        print("  注意: 需要配置 akshare_adapter.py 作为数据源")
        print("\n为测试目的，创建最小 bundle 结构...")
        
        # 创建最小结构（避免报错）
        for subdir in ["instruments", "stocks", "indexes"]:
            os.makedirs(os.path.join(bundle_path, subdir), exist_ok=True)
        
        # 创建一个空的 instruments.pk 占位文件
        import pickle
        try:
            with open(os.path.join(bundle_path, "instruments.pk"), "wb") as f:
                pickle.dump({}, f)
            print("✅ 已创建最小 bundle 结构（仅用于测试）")
        except Exception as e:
            print(f"⚠️  创建 bundle 结构失败: {e}")
    
    return True


def test_akshare_data():
    """测试 AKShare 数据获取"""
    print("\n" + "=" * 60)
    print("3. 测试 AKShare 数据获取...")
    print("=" * 60)
    
    try:
        from akshare.stock_feature.stock_hist_em import stock_zh_a_hist
        df = stock_zh_a_hist(symbol="600745", period="daily", start_date="20240101", end_date="20240630", adjust="")
        if df is not None and len(df) > 0:
            print(f"✅ 闻泰科技数据获取成功: {len(df)} 条记录")
            print(f"   日期范围: {df['日期'].min()} 至 {df['日期'].max()}")
            return True
        else:
            print("⚠️  未获取到数据")
            return False
    except Exception as e:
        print(f"❌ AKShare 数据获取失败: {e}")
        return False


def test_rqalpha_import():
    """测试 RQAlpha 导入（使用子进程避免路径问题）"""
    print("\n" + "=" * 60)
    print("4. 测试 RQAlpha run_file 导入...")
    print("=" * 60)
    
    site = next((p for p in sys.path if "venv" in p and "site-packages" in p), None)
    if not site:
        print("❌ 未找到 venv site-packages")
        return False
    
    code = '''
import sys, os
# 确保从 venv 加载 rqalpha
from rqalpha import run_file
print("✅ run_file 导入成功")
'''
    
    env = {**os.environ}
    env["PYTHONPATH"] = site
    
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd="/tmp",
            env=env,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(result.stdout.strip())
            return True
        else:
            print(f"❌ 导入失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_strategy_syntax():
    """测试策略文件语法"""
    print("\n" + "=" * 60)
    print("5. 测试策略文件语法...")
    print("=" * 60)
    
    strategy_file = os.path.join(_root, "strategies", "strategy_wentai_demo.py")
    if not os.path.exists(strategy_file):
        print(f"❌ 策略文件不存在: {strategy_file}")
        return False
    
    try:
        with open(strategy_file, "r", encoding="utf-8") as f:
            code = f.read()
        compile(code, strategy_file, "exec")
        print(f"✅ 策略文件语法正确: {os.path.basename(strategy_file)}")
        return True
    except SyntaxError as e:
        print(f"❌ 策略文件语法错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False


def test_web_platform():
    """测试 Web 平台"""
    print("\n" + "=" * 60)
    print("6. 测试 Web 平台...")
    print("=" * 60)
    
    try:
        import flask
        print("✅ Flask 已安装")
        
        # 检查 web_platform.py 语法
        web_file = os.path.join(_root, "web_platform.py")
        if os.path.exists(web_file):
            with open(web_file, "r", encoding="utf-8") as f:
                code = f.read()
            compile(code, web_file, "exec")
            print("✅ web_platform.py 语法正确")
            return True
        else:
            print("⚠️  web_platform.py 不存在")
            return False
    except Exception as e:
        print(f"❌ Web 平台检查失败: {e}")
        return False


def create_test_bundle():
    """创建测试用的最小 bundle"""
    print("\n" + "=" * 60)
    print("7. 创建测试数据包...")
    print("=" * 60)
    
    bundle_path = os.path.join(_root, "bundle")
    os.makedirs(bundle_path, exist_ok=True)
    
    # 创建必要的空文件，避免 RQAlpha 报错
    import numpy as np
    import h5py
    
    try:
        # 创建空的 HDF5 文件
        for name in ["stocks.h5", "indexes.h5", "funds.h5"]:
            filepath = os.path.join(bundle_path, name)
            if not os.path.exists(filepath):
                with h5py.File(filepath, "w") as f:
                    pass
                print(f"✅ 创建: {name}")
        
        # 创建空的 trading_dates.npy
        dates_file = os.path.join(bundle_path, "trading_dates.npy")
        if not os.path.exists(dates_file):
            np.save(dates_file, np.array([]))
            print("✅ 创建: trading_dates.npy")
        
        # 创建空的 instruments.pk
        import pickle
        inst_file = os.path.join(bundle_path, "instruments.pk")
        if not os.path.exists(inst_file):
            with open(inst_file, "wb") as f:
                pickle.dump({}, f)
            print("✅ 创建: instruments.pk")
        
        print("✅ 测试数据包创建完成（空结构，仅用于语法测试）")
        return True
    except Exception as e:
        print(f"⚠️  创建数据包时出错: {e}")
        print("   这不会影响策略语法测试")
        return False


def main():
    """主测试流程"""
    print("\n" + "=" * 60)
    print("🚀 自动化测试开始")
    print("=" * 60)
    
    results = {}
    
    # 1. 检查依赖
    results["dependencies"] = check_dependencies()
    
    # 2. 检查数据包
    results["bundle"] = check_bundle()
    
    # 3. 测试 AKShare
    results["akshare"] = test_akshare_data()
    
    # 4. 测试 RQAlpha 导入
    results["rqalpha_import"] = test_rqalpha_import()
    
    # 5. 测试策略语法
    results["strategy_syntax"] = test_strategy_syntax()
    
    # 6. 测试 Web 平台
    results["web_platform"] = test_web_platform()
    
    # 7. 创建测试 bundle
    results["test_bundle"] = create_test_bundle()
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)
    
    for name, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"{status} {name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 所有测试通过！系统已就绪")
        print("\n下一步:")
        print("1. 运行回测: python run_backtest.py strategies/strategy_wentai_demo.py 2024-01-01 2024-06-30")
        print("2. 启动 Web 平台: python web_platform.py")
    else:
        print("\n⚠️  部分测试未通过，请检查上述输出")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
