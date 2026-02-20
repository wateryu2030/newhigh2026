#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整初始化脚本 - 自动安装依赖、配置数据源、创建必要文件
"""
import os
import sys
import json
import pickle
import numpy as np
import h5py
import subprocess

_root = os.path.dirname(os.path.abspath(__file__))
os.chdir(_root)

print("=" * 60)
print("🚀 完整初始化脚本")
print("=" * 60)

# 1. 检查并安装依赖
print("\n1. 检查依赖...")
try:
    import akshare
    print("✅ akshare")
except:
    print("安装 akshare...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-e", "./akshare"], check=False)

try:
    import rqalpha
    print("✅ rqalpha")
except:
    print("安装 rqalpha...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-e", "./rqalpha"], check=False)

try:
    import flask
    print("✅ flask")
except:
    print("安装 flask...")
    subprocess.run([sys.executable, "-m", "pip", "install", "flask"], check=False)

# 2. 创建目录结构
print("\n2. 创建目录结构...")
for d in ["strategies", "output", "data", "bundle"]:
    os.makedirs(d, exist_ok=True)
    print(f"✅ {d}/")

# 3. 创建完整的 bundle 文件
print("\n3. 创建 bundle 文件...")
bundle_path = os.path.join(_root, "bundle")

# future_info.json - 需要数组格式
future_info = [
    {
        "order_book_id": "TEST",
        "underlying_symbol": "TEST",
        "margin_rate": 0.1,
        "commission_type": "by_volume",
        "commission": 0.0,
    }
]
with open(os.path.join(bundle_path, "future_info.json"), "w", encoding="utf-8") as f:
    json.dump(future_info, f, ensure_ascii=False, indent=2)
print("✅ future_info.json")

# share_transformation.json
with open(os.path.join(bundle_path, "share_transformation.json"), "w", encoding="utf-8") as f:
    json.dump({}, f)
print("✅ share_transformation.json")

# HDF5 文件 - 创建带 data 数据集的结构
h5_files_with_data = [
    "yield_curve.h5",
    "suspended_days.h5",
    "st_stock_days.h5",
    "stocks.h5",
    "indexes.h5",
    "funds.h5",
    "futures.h5",
    "dividends.h5",
    "split_factor.h5",
    "ex_cum_factor.h5",
]

for filename in h5_files_with_data:
    filepath = os.path.join(bundle_path, filename)
    with h5py.File(filepath, "w") as f:
        # 创建空的 data 数据集
        f.create_dataset("data", data=np.array([], dtype=np.float64), maxshape=(None,))
    print(f"✅ {filename}")

# trading_dates.npy
np.save(os.path.join(bundle_path, "trading_dates.npy"), np.array([], dtype=np.uint64))
print("✅ trading_dates.npy")

# instruments.pk
with open(os.path.join(bundle_path, "instruments.pk"), "wb") as f:
    pickle.dump([], f)
print("✅ instruments.pk")

print("\n✅ Bundle 文件创建完成！")
print("\n注意: 这些是空文件结构，仅用于测试策略语法。")
print("要获取真实回测数据，请执行: rqalpha download-bundle")

# 4. 测试导入
print("\n4. 测试导入...")
site = next((p for p in sys.path if "venv" in p and "site-packages" in p), None)
if site:
    code = '''
import sys, os
from rqalpha import run_file
print("✅ run_file 导入成功")
'''
    env = {**os.environ}
    env["PYTHONPATH"] = site
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd="/tmp",
        env=env,
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print(result.stdout.strip())
    else:
        print("⚠️  run_file 导入测试失败")

print("\n" + "=" * 60)
print("✅ 初始化完成！")
print("=" * 60)
print("\n下一步:")
print("1. 运行回测: python run_backtest.py strategies/strategy_wentai_demo.py 2024-01-01 2024-06-30")
print("2. 启动 Web 平台: python web_platform.py")
print("3. 查看数据: python test_wentai.py")
