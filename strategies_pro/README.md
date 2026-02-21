# A股机构级策略模块 strategies_pro

在现有 newhigh2026 项目基础上新增，不破坏原有代码结构。包含：

- **趋势突破**：MA20>MA60、60日新高、放量，仓位 30%–40%
- **强势回调**：30日涨幅>20%、回调 5–15%、MA20 支撑，仓位 20%–30%
- **ETF轮动**：沪深300/500/创业板/红利/黄金 ETF 动量排名，仓位 10%–20%
- **市场环境识别**：BULL/NEUTRAL/BEAR，动态调整策略权重
- **策略评分与动态权重**：与现有组合管理、交易模块兼容

## 要求

- Python 3.11
- pandas / numpy
- 类型注解完整
- 可运行示例与单元测试

## 目录结构

```
strategies_pro/
├── __init__.py
├── base_strategy.py      # 抽象基类
├── trend_breakout.py     # 趋势突破
├── strong_pullback.py    # 强势回调
├── etf_rotation.py       # ETF 轮动
├── market_regime.py      # 市场环境
├── strategy_scorer.py    # 策略评分
├── strategy_manager.py   # 策略管理器
├── README.md
└── tests/
    └── test_strategies_pro.py
```

## 使用示例

### 1. 初始化并运行

```python
from strategies_pro import (
    TrendBreakoutStrategy,
    StrongPullbackStrategy,
    ETFRotationStrategy,
    MarketRegimeDetector,
    StrategyManager,
)

market_data = {"000001.XSHE": df1, "600519.XSHG": df2}  # symbol -> OHLCV DataFrame

manager = StrategyManager()
combined = manager.get_combined_signals(market_data)
print(combined)  # symbol | weight | strategy | signal | stop_loss
```

### 2. 市场环境与权重

```python
from strategies_pro import MarketRegimeDetector

detector = MarketRegimeDetector()
regime = detector.detect(index_df)  # BULL / NEUTRAL / BEAR
tw, sw, ew = detector.get_strategy_weights(regime)  # 趋势、回调、ETF 权重
```

### 3. 运行示例脚本

```bash
python run_strategy_demo.py
```

输出：股票列表、ETF 配置、组合权重、交易信号。

## 单元测试

```bash
python -m strategies_pro.tests.test_strategies_pro
```

## 与现有系统兼容

- 信号格式含 `symbol, signal, weight, stop_loss`，可对接 `portfolio_system`、`paper_trading`
- `StrategyManager.get_combined_signals()` 输出统一 DataFrame，便于组合层使用
