# Portfolio Manager

多策略组合管理层，统一管理、优化和交易多个策略。

## 功能

- **PortfolioManager**：组合管理核心，支持多策略、权重分配、信号聚合、回测、paper_trading 对接
- **SignalAggregator**：信号整合（多数 BUY→BUY、强 BUY、得分加权、忽略最低分）
- **WeightAllocator**：等权、得分加权、风险平价
- **PerformanceReport**：组合收益曲线、每日净值、最大回撤、夏普比率、各策略贡献

## 使用方式

### 基础示例：等权组合

```python
from portfolio.portfolio_manager import PortfolioManager
from portfolio.base_strategy import StrategyAdapter
from strategies import get_plugin_strategy

# 使用插件策略
ma = get_plugin_strategy("ma_cross")
rsi = get_plugin_strategy("rsi")
strategies = [StrategyAdapter(ma), StrategyAdapter(rsi)]

pm = PortfolioManager(strategies, weight_mode="equal")

# 生成组合信号
import pandas as pd
df = load_kline("000001.XSHE", "2024-01-01", "2024-06-30")
signal = pm.generate_portfolio_signal(df)

# 运行回测
result = pm.run_backtest("2024-01-01", "2024-06-30", stock_code="000001.XSHE")
print(result["summary"])
print(result["performance_report"])
```

### 得分加权

```python
pm = PortfolioManager(strategies, weight_mode="score")
result = pm.run_backtest("2024-01-01", "2024-06-30", stock_code="000001.XSHE")
```

### 风险平价

```python
pm = PortfolioManager(strategies, weight_mode="risk_parity")
# 需要传入各策略波动率以计算权重
```

### paper_trading 模拟执行

```python
result = pm.run_with_paper_trading(
    start_date="2024-01-01",
    end_date="2024-06-30",
    stock_code="000001.XSHE",
    initial_cash=1_000_000,
)
print(result["curve"])
print(result["trades"])
print(result["positions"])
```

### 自定义策略接口

```python
from portfolio.base_strategy import PortfolioStrategyBase, StrategyAdapter

# 方式 1：包装现有策略（有 generate_signals）
adapter = StrategyAdapter(my_strategy)

# 方式 2：实现 PortfolioStrategyBase
class MyStrategy(PortfolioStrategyBase):
    def generate_signal(self, data):
        return pd.Series(...)  # 1=BUY, -1=SELL, 0=HOLD

    def score(self, data):
        return 0.8
```

## 单元测试

```bash
python -m portfolio.tests.test_portfolio_manager
```
