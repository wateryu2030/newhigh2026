# AI 选股系统

在现有策略层之上增加 **AI 选股与信号评分**，实现「规则策略 → AI 增强策略」，提升胜率与收益稳定性。

## 模块概览

| 模块 | 说明 |
|------|------|
| **因子工程** `feature_engineering.py` | 从 K 线生成技术/趋势/动量/风险因子，输出带 `label`（未来 N 日收益）的 DataFrame |
| **数据集构建** `dataset_builder.py` | 滚动窗口、多股票合并，产出 X, y |
| **模型训练** `model_trainer.py` | XGBoost 训练，评估 AUC / IC / 收益模拟，保存 `models/xgb_model.pkl` |
| **预测** `model_predictor.py` | 加载模型，对当前股票打分，输出 `symbol \| score`（0–1） |
| **信号排序** `signal_ranker.py` | 合并 AI 分与策略分：`final_score = 0.6 * ai_score + 0.4 * strategy_score` |
| **模型管理** `model_manager.py` | 统一入口：`train_models()` / `predict()` / `update_models()` |

## 依赖

- Python 3.11+
- pandas, numpy, **scikit-learn**（必须）
- **xgboost**（可选；若不可用会回退到 sklearn.GradientBoosting）

```bash
pip install scikit-learn xgboost
```

**Mac 上 XGBoost 报错 `libomp.dylib` 时**：先安装 OpenMP 再装 xgboost，或直接使用回退（不装 xgboost 也可训练/预测）：

```bash
brew install libomp   # 再用 pip install xgboost
```

## 使用示例

### 0. 完善数据（推荐：全 A 股 + 400 天）

```bash
python scripts/ensure_ai_data.py
```

- 获取全 A 股列表（不含退市），将缺数据的标的补齐至 **400 天** 并写入 `data/astock.db`
- 支持断点续传（默认跳过已有足够数据的标的）
- 测试可加 `--limit 200`；强制重拉可加 `--no-skip`

### 1. 训练模型

```bash
python train_ai_model.py
```

- 使用**全 A 股（不含退市）**、**400 天**历史从数据库加载（建议先运行上方 `ensure_ai_data.py`）
- 构建因子与标签（未来 5 日收益），训练并保存到 `models/xgb_model.pkl`
- 输出 AUC、IC、Top20% 平均收益

### 2. 预测今日推荐

```bash
python run_ai_prediction.py
```

- 加载当前行情与已训练模型  
- 对股票池打分，输出 **今日推荐股票 Top N**（默认 Top 20，可通过环境变量 `AI_TOP_N=30` 修改）

### 3. 与策略层融合

在 `StrategyManager` 中设置 AI 评分后，组合权重会按 AI 分数调整：

```python
from strategies_pro import StrategyManager
from ai_models import ModelManager

manager = StrategyManager()
ai_manager = ModelManager()
market_data = {...}  # 多标的 K 线
ai_scores = ai_manager.predict(market_data)
manager.set_ai_scores(ai_scores)
combined = manager.get_combined_signals(market_data)  # weight *= ai_score
```

### 4. 仅用因子/数据集

```python
from ai_models.feature_engineering import build_features_multi
from ai_models.dataset_builder import build_dataset_from_market_data

feature_df = build_features_multi(market_data, label_forward_days=5)
feature_df, X, y = build_dataset_from_market_data(market_data, label_forward_days=5)
```

## 因子列表（默认）

- **技术**：MA5/10/20/60、日收益、波动率、ATR、RSI、MACD 柱、成交量变化  
- **趋势**：20 日新高距离、均线多头排列  
- **动量**：5/20/60 日收益  
- **风险**：20 日最大回撤  

## 单元测试

```bash
python -m pytest tests/test_ai_models.py -v
# 或
python tests/test_ai_models.py
```

验证：因子生成、数据集 X/y、模型训练与保存、预测输出 `symbol | score`、信号排序 `final_score`。
