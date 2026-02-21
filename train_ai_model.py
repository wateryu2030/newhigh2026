#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 选股模型训练脚本：
1. 获取 AKShare/数据库历史数据
2. 生成因子
3. 训练 XGBoost 模型
4. 保存到 models/xgb_model.pkl
"""
from __future__ import annotations
import os
import sys
from datetime import datetime, timedelta

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)


def load_multi_symbols(
    symbols: list[str],
    days: int = 400,
    min_bars: int = 80,
    source: str = "database",
) -> dict[str, "pd.DataFrame"]:
    """从数据库（或 akshare）加载多标的 K 线。"""
    import pandas as pd
    from data.data_loader import load_kline

    end = datetime.now().date()
    start = (end - timedelta(days=days)).strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")
    out = {}
    for s in symbols:
        code = s.split(".")[0] if "." in s else s
        df = load_kline(code, start, end_str, source=source)
        if source == "database" and (df is None or len(df) < min_bars):
            df = load_kline(code, start, end_str, source="akshare")
        if df is not None and len(df) >= min_bars:
            key = s if "." in s else (s + ".XSHG" if s.startswith("6") else s + ".XSHE")
            out[key] = df
    return out


def main() -> None:
    from ai_models.model_manager import ModelManager
    from data.stock_pool import get_a_share_symbols

    # 全 A 股（不含退市），建议先运行: python scripts/ensure_ai_data.py
    print("1. 获取股票池（全 A 股，不含退市）...")
    symbols = []
    try:
        symbols = get_a_share_symbols(exclude_delisted=True)
    except Exception as e:
        print(f"   stock_pool 获取失败: {e}")
    if not symbols:
        try:
            from database.data_fetcher import get_all_a_share_symbols
            symbols = get_all_a_share_symbols()
        except Exception:
            pass
    if not symbols:
        print("   使用示例池（请先运行 scripts/ensure_ai_data.py 或检查 akshare）")
        symbols = [
            "000001", "000002", "000858", "600519", "600036", "600745", "300750",
            "601318", "000333", "002415", "300059", "600276", "000568", "601012",
        ]
    print(f"   共 {len(symbols)} 只，加载 400 天历史...")
    market_data = load_multi_symbols(symbols, days=400, min_bars=80, source="database")
    print(f"   已加载 {len(market_data)} 只标的（≥80 条 K 线）")
    if len(market_data) < 5:
        print("   数据不足，请先运行: python scripts/ensure_ai_data.py")
        sys.exit(1)

    print("2. 构建因子与标签...")
    from ai_models.model_trainer import _xgboost_available
    if not _xgboost_available():
        print("   (XGBoost 不可用，将使用 sklearn GradientBoosting；Mac 可安装: brew install libomp)")
    manager = ModelManager()
    result = manager.train_models(
        market_data,
        label_forward_days=5,
        use_binary=True,
        binary_threshold=0.0,
        eval_frac=0.2,
    )
    if not result.get("ok"):
        print(f"   训练未执行: {result.get('reason', 'unknown')}")
        sys.exit(1)

    metrics = result.get("metrics", {})
    print("3. 评估指标:")
    auc = metrics.get("auc", 0.5)
    ic = metrics.get("ic", 0)
    ret_top = metrics.get("return_top20pct", 0)
    print(f"   AUC: {auc:.4f}")
    print(f"   IC:  {ic:.4f}")
    print(f"   Top20% 平均收益: {ret_top:.4f}")
    if auc < 0.55 and abs(ic) < 0.05:
        print("   (样本较少或信号弱时指标接近 0.5 属正常；可增加标的/历史天数或调整 label_forward_days)")
    print(f"4. 模型已保存: {result.get('model_path', '')}")
    print("完成。")


if __name__ == "__main__":
    main()
