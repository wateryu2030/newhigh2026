# 机构级组合系统升级说明

本文档描述 newhigh2026 的机构级升级架构、策略逻辑、运行方法与实盘流程。

## 目标

- **资金规模**：100 万+
- **风格**：波段趋势
- **目标年化**：20%～40%
- **最大回撤**：≤15%

## 系统架构

```
newhigh2026/
├── data/                     # 数据层
│   ├── data_loader.py
│   └── stock_pool.py         # 全 A 股列表（不含退市）
├── strategies_pro/          # 策略层（趋势突破、强势回调、ETF 轮动）
│   ├── strategy_manager.py
│   └── market_regime.py     # 市场状态 BULL/NEUTRAL/BEAR
├── portfolio/                # 组合层
│   ├── allocator.py          # 资金分配：等权 / 风险平价 / 波动率目标 / Kelly
│   ├── optimizer.py          # 组合优化：Mean Variance / 最大夏普 / 最小方差
│   ├── position_manager.py   # 仓位约束：单股 10%、行业 30%、最多 10～15 只
│   ├── capital_allocator.py
│   └── portfolio_engine.py
├── risk/                     # 风控层
│   └── risk_engine.py        # 回撤控制、行业/单股风险检查
├── engine/                   # 组合引擎
│   └── portfolio_engine.py   # 数据→策略→分配→风控→指令
├── execution/                # 执行层
│   └── broker_simulator.py   # T+1、滑点 0.1%、手续费 0.03%、涨跌停
├── ai_models/                # AI 选股与评分
├── ai/                       # 市场状态识别
│   └── regime_model.py       # BULL/BEAR/NEUTRAL（均线规则 + 可选 RF）
└── config/
```

## 策略逻辑

- **多策略**：`strategies_pro` 提供趋势突破、强势回调、ETF 轮动，由 `StrategyManager` 按市场状态分配权重并输出合并信号。
- **资金分配**：`portfolio.allocator.allocate(capital, signals)` 支持等权、风险平价、波动率目标、Kelly。
- **仓位约束**：单股最大 10%、单行业最大 30%、最大持仓数 10～15，由 `position_manager` 执行。
- **风控规则**：回撤 ≥10% 降仓 30%，≥15% 清仓；`risk_engine.apply_drawdown_rules()` 返回仓位缩放系数。

## 运行方法

### 1. 数据准备

```bash
python scripts/ensure_ai_data.py --days 400   # 全 A 股 400 天
```

### 2. AI 模型训练（可选）

```bash
python train_ai_model.py
python run_ai_prediction.py
```

### 3. 机构组合引擎单次运行

```python
from engine import InstitutionalPortfolioEngine
from data.data_loader import load_kline

# 加载行情与指数
market_data = {...}  # { symbol: DataFrame }
index_df = load_kline("510300", start, end, source="database")
engine = InstitutionalPortfolioEngine(capital=1_000_000, max_positions=15)
result = engine.run(market_data, index_df=index_df, current_max_drawdown=0.05)
# result["orders"], result["target_positions"], result["risk_scale"]
```

### 4. 执行模拟

```python
from execution import BrokerSimulator
broker = BrokerSimulator(slippage_pct=0.001, commission_pct=0.0003)
filled = broker.fill_orders(result["orders"], prices={...}, prev_closes={...})
```

## 回测验证目标

- 年化收益 > 20%
- 最大回撤 < 15%
- 夏普 > 1.5

可通过现有回测脚本接入 `engine.run()` 与 `execution.BrokerSimulator`，按日推进净值与回撤，统计上述指标。

## 实盘流程建议

1. 每日定时拉取行情与指数。
2. 调用 `InstitutionalPortfolioEngine.run()` 得到目标仓位与订单。
3. 用 `BrokerSimulator` 做成本与涨跌停过滤（或对接真实券商接口）。
4. 根据风控返回的 `risk_scale` 与目标仓位执行下单。
5. 记录净值与最大回撤，供下一日风控输入。

## 依赖

- Python 3.11+
- pandas, numpy, scipy, scikit-learn
- 现有 data / strategies_pro / portfolio / risk 模块
