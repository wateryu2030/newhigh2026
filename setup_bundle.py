#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动创建 RQAlpha bundle 所需的最小文件结构
"""
import os
import json
import pickle
import numpy as np
import h5py

_root = os.path.dirname(os.path.abspath(__file__))
bundle_path = os.path.join(_root, "bundle")
os.makedirs(bundle_path, exist_ok=True)

print("=" * 60)
print("创建 RQAlpha bundle 文件...")
print("=" * 60)

# JSON 文件
json_files = {
    "future_info.json": {},
    "share_transformation.json": {},
}

for filename, content in json_files.items():
    filepath = os.path.join(bundle_path, filename)
    # 强制覆盖，确保格式正确
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)
    print(f"✅ 创建/更新: {filename}")

# HDF5 文件
h5_files = [
    "yield_curve.h5",
    "suspended_days.h5",
    "st_stock_days.h5",
    "funds.h5",
    "stocks.h5",
    "indexes.h5",
    "futures.h5",
    "dividends.h5",
    "split_factor.h5",
    "ex_cum_factor.h5",
]

for filename in h5_files:
    filepath = os.path.join(bundle_path, filename)
    if not os.path.exists(filepath):
        with h5py.File(filepath, "w") as f:
            pass
        print(f"✅ 创建: {filename}")

# NumPy 文件
npy_files = {
    "trading_dates.npy": np.array([], dtype=np.uint64),
}

for filename, content in npy_files.items():
    filepath = os.path.join(bundle_path, filename)
    if not os.path.exists(filepath):
        np.save(filepath, content)
        print(f"✅ 创建: {filename}")

# Pickle 文件
pk_files = {
    "instruments.pk": {},
}

for filename, content in pk_files.items():
    filepath = os.path.join(bundle_path, filename)
    if not os.path.exists(filepath):
        with open(filepath, "wb") as f:
            pickle.dump(content, f)
        print(f"✅ 创建: {filename}")

print("\n✅ Bundle 文件创建完成！")
print("\n注意: 这些是空文件，仅用于测试。实际回测需要真实数据。")
print("要获取真实数据，请执行: rqalpha download-bundle")
