#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型修正闭环入口：用历史 3/4 训练 → 预测后 1/4 → 评估预测与实际 → 记录并可持续循环。

用法：
  python run_correction_loop.py                    # 默认：database 数据，500 天，75% 训练
  python run_correction_loop.py --days 400 --source akshare
  python run_correction_loop.py --train-ratio 0.75 --label-days 5

当有新数据进入数据库或拉取到新 K 线后，再次执行本脚本即可完成「新数据 → 再训练 → 再预测 → 再评估」的修正循环。
"""
from __future__ import annotations
import argparse
import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)


def main() -> None:
    p = argparse.ArgumentParser(description="AI 选股模型修正闭环：训练(3/4)→预测(1/4)→评估→记录")
    p.add_argument("--days", type=int, default=500, help="拉取历史 K 线天数")
    p.add_argument("--source", default="database", choices=("database", "akshare"), help="数据源")
    p.add_argument("--train-ratio", type=float, default=0.75, help="训练集时间比例（如 0.75 表示前 3/4 训练）")
    p.add_argument("--label-days", type=int, default=5, help="标签未来收益天数")
    p.add_argument("--max-symbols", type=int, default=500, help="最多参与标的数（0=不限制）")
    args = p.parse_args()

    from ai_models.correction_loop import run_cycle_with_data_loader

    print("模型修正闭环")
    print("  数据: 前 3/4 训练，后 1/4 前向验证（预测 vs 实际）")
    print("  新数据到来后再次运行本脚本即可持续修正")
    print()

    result = run_cycle_with_data_loader(
        symbols=None,
        days=args.days,
        train_ratio=args.train_ratio,
        label_forward_days=args.label_days,
        source=args.source,
    )

    if not result.get("ok"):
        print("失败:", result.get("error", result.get("reason", "unknown")))
        sys.exit(1)

    print("训练段:", result.get("n_train"), "条 | 前向段:", result.get("n_forward"), "条")
    print("训练日期:", result.get("train_date_range"))
    print("前向日期:", result.get("forward_date_range"))
    print("模型:", result.get("model_path", ""))
    metrics = result.get("metrics", {})
    if metrics:
        print("前向验证指标:")
        print("  IC:         ", metrics.get("ic"))
        print("  Rank IC:    ", metrics.get("rank_ic"))
        print("  Top20% 收益:", metrics.get("return_top20pct"))
    print("预测记录已追加到 models/prediction_log.csv")
    print("指标已写入 models/correction_metrics.json")
    print("完成。新数据到位后再次运行以继续修正。")


if __name__ == "__main__":
    main()
