# -*- coding: utf-8 -*-
"""
训练 AI 买卖点预测模型：从 DuckDB 拉取多只股票日线，构建特征与目标（未来 5 日收益>3%=1），训练 LightGBM 并保存到 models/lgb_model.pkl。
用法（在项目根目录）: python -m backend.ai.train
"""
from __future__ import annotations
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from datetime import datetime, timedelta


def main():
    from database.duckdb_backend import get_db_backend
    from backend.ai.feature_engineering import build_features
    from backend.ai.ai_model import train_model, save_model, _get_target

    db = get_db_backend()
    if not getattr(db, "db_path", None) or not os.path.exists(getattr(db, "db_path", "")):
        print("未找到数据库，请先准备 data/quant.duckdb 或启用 DuckDB 并导入日线。")
        return
    stocks = db.get_stocks()
    if not stocks:
        print("数据库无股票列表。")
        return
    # 最多用 300 只股票、每只约 1 年数据，避免内存过大
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    all_feats = []
    for i, row in enumerate(stocks[:300]):
        order_book_id = row[0]
        df = db.get_daily_bars(order_book_id, start_date, end_date)
        if df is None or len(df) < 60:
            continue
        feats = build_features(df)
        if feats is None or len(feats) < 10:
            continue
        all_feats.append(feats)
        if (i + 1) % 50 == 0:
            print(f"已处理 {i + 1} 只股票…")
    if not all_feats:
        print("无有效特征数据，请确保数据库有足够日线。")
        return
    import pandas as pd
    combined = pd.concat(all_feats, axis=0, ignore_index=False)
    # 去掉没有未来 5 日收益的行（每只股票最后 5 天）
    combined = combined.dropna(subset=["forward_return_5d"])
    if len(combined) < 500:
        print("有效样本过少，请扩大股票数或日期范围。")
        return
    print(f"训练样本数: {len(combined)}")
    model = train_model(combined)
    path = save_model(model)
    print(f"模型已保存: {path}")


if __name__ == "__main__":
    main()
