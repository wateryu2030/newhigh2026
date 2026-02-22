#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 自进化交易系统入口：加载数据（train/val/test 划分）→ 进化引擎生成策略 → 评估 → 策略池。
可配置 rounds、标的、数据路径；支持无 OPENAI_API_KEY 时使用随机/模板策略做流程验证。
"""
from __future__ import annotations
import os
import sys
from datetime import datetime, timedelta

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)


def load_evolution_data(symbol: str = "000001", days: int = 400):
    """加载单标的 K 线，优先 data/evolution/*.csv，否则用 data_loader。"""
    from data.data_loader import load_kline
    from evolution.data_split import ensure_ohlcv, split_train_val_test

    end = datetime.now().date()
    start = (end - timedelta(days=days + 50)).strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    csv_path = os.path.join(_ROOT, "data", "evolution", f"{symbol}.csv")
    if os.path.exists(csv_path):
        import pandas as pd
        df = pd.read_csv(csv_path)
        if "date" not in df.columns and len(df.columns) > 0:
            df["date"] = df.iloc[:, 0].astype(str)
        df = ensure_ohlcv(df)
    else:
        df = load_kline(symbol, start, end_str, source="database")
        if df is None or len(df) < 200:
            df = load_kline(symbol, start, end_str, source="akshare")
        df = ensure_ohlcv(df) if df is not None else None

    if df is None or len(df) < 100:
        return None, None, None
    train, val, test = split_train_val_test(df, train_ratio=0.6, val_ratio=0.2, test_ratio=0.2)
    return train, val, test


def main():
    import argparse
    p = argparse.ArgumentParser(description="AI 自进化交易系统")
    p.add_argument("--symbol", default="000001", help="标的代码")
    p.add_argument("--rounds", type=int, default=5, help="进化轮数")
    p.add_argument("--idea", default="双均线金叉死叉：短期均线上穿长期均线买入，下穿卖出", help="策略思想")
    p.add_argument("--pool-path", default="data/evolution/strategy_pool.json", help="策略池持久化路径")
    p.add_argument("--no-llm", action="store_true", help="不使用 LLM，仅跑流程（模板策略）")
    args = p.parse_args()

    print("加载数据（train/val/test）...")
    train, val, test = load_evolution_data(args.symbol)
    if train is None or len(train) < 50:
        print("数据不足，请先运行: python scripts/ensure_evolution_data.py")
        sys.exit(1)
    print(f"  训练 {len(train)} 验证 {len(val)} 测试 {len(test)} 条")

    from evolution.strategy_runner import StrategyRunner
    from evolution.strategy_evaluator import StrategyEvaluator
    from evolution.evolution_engine import EvolutionEngine
    from evolution.strategy_generator import StrategyGenerator
    from evolution.strategy_pool import StrategyPool

    runner = StrategyRunner()
    evaluator = StrategyEvaluator()
    pool_path = os.path.join(_ROOT, args.pool_path)
    os.makedirs(os.path.dirname(pool_path) or ".", exist_ok=True)
    pool = StrategyPool(min_sharpe=0.5, max_drawdown=0.25, min_score=0.0, persist_path=pool_path)
    pool.load()

    if args.no_llm:
        # 模板策略验证流程
        code_tpl = """
import pandas as pd
import numpy as np
def strategy(df):
    out = df.copy()
    out['ma5'] = out['close'].rolling(5).mean()
    out['ma20'] = out['close'].rolling(20).mean()
    out['signal'] = 0
    out.loc[out['ma5'] > out['ma20'], 'signal'] = 1
    out.loc[out['ma5'] <= out['ma20'], 'signal'] = -1
    out['signal'] = out['signal'].fillna(0)
    return out
"""
        result = runner.run(code_tpl, train)
        if result.get("error"):
            print("模板策略运行失败:", result["error"])
            sys.exit(1)
        metrics = evaluator.evaluate(result["equity"], result.get("df"))
        print("模板策略指标:", metrics)
        if metrics["score"] > 0:
            pool.add(code_tpl, metrics)
            print("已加入策略池（--no-llm 模式）")
        return

    try:
        generator = StrategyGenerator()
        engine = EvolutionEngine(generator=generator, runner=runner, evaluator=evaluator)
        print("开始进化（LLM 生成策略）...")
        best = engine.evolve(args.idea, train, rounds=args.rounds)
        if not best:
            print("本轮未产生有效策略，可检查 OPENAI_API_KEY 或增加 rounds")
            return
        print("本轮最优策略（按 score）:")
        for i, (code, m) in enumerate(best[:3], 1):
            print(f"  {i}. score={m['score']} sharpe={m['sharpe']} max_dd={m['max_dd']}")
            if pool.add(code, m):
                print("    已加入策略池")
        pool._save()
    except RuntimeError as e:
        if "OPENAI_API_KEY" in str(e):
            print("未设置 OPENAI_API_KEY，请设置或使用 --no-llm 验证流程")
            sys.exit(1)
        raise
    print("完成。")


if __name__ == "__main__":
    main()
