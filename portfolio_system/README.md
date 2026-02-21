# portfolio_system — 机构级 A 股组合系统

目标年化 20~40%，面向对象设计，Python 3.11+，类型注解完整，pandas 处理数据，交易信号可接 `paper_trading` 执行。

## 功能

| 模块 | 说明 |
|------|------|
| **多策略组合** | MA / RSI / MACD / KDJ / Breakout 加权聚合 |
| **市场状态识别** | BULL / NEUTRAL / BEAR，用于仓位调节 |
| **风控** | 单股止损 8%、回撤保护、仓位限制 |
| **回测** | Backtester 输出净值曲线、交易记录、绩效 |
| **模拟交易** | PortfolioSimulator 对接 paper_trading |
| **绩效报告** | 总收益、年化、最大回撤、夏普、卡玛 |

## 安装依赖

```bash
pip install pandas numpy
```

项目需包含 `strategies`、`paper_trading`、`data` 等模块。

## 快速开始

### 回测

```python
from portfolio_system import Backtester, PortfolioConfig

config = PortfolioConfig(
    initial_cash=1_000_000.0,
    target_annual_return_min=0.20,
    target_annual_return_max=0.40,
)

bt = Backtester(config)
result = bt.run("000001", "2023-01-01", "2024-12-31")

print(result["summary"])
# {'total_return': 0.15, 'max_drawdown': 0.08, 'sharpe_ratio': 1.2, ...}
print(result["performance_report"])
```

### 模拟交易（对接 paper_trading）

```python
from portfolio_system import PortfolioSimulator, PortfolioConfig

config = PortfolioConfig()
sim = PortfolioSimulator(config)
result = sim.run("000001", "2023-01-01", "2024-12-31")

print(result["curve"])    # 净值曲线
print(result["trades"])   # 交易记录
print(result["positions"]) # 持仓
```

### 自定义数据加载

```python
from portfolio_system import Backtester
from data.data_loader import load_kline

def load_stock(sym: str, start: str, end: str):
    return load_kline(sym, start, end, source="database")

bt = Backtester()
bt.set_data_loaders(load_stock=load_stock)
result = bt.run("600519", "2023-01-01", "2024-12-31")
```

## 运行示例

```bash
cd /path/to/astock
python -m portfolio_system.run_example
```

## 单元测试

```bash
python -m portfolio_system.tests.test_portfolio_system
```

## 配置

| 参数 | 默认 | 说明 |
|------|------|------|
| `target_annual_return_min` | 0.20 | 目标年化下限 |
| `target_annual_return_max` | 0.40 | 目标年化上限 |
| `stop_loss_pct` | 0.08 | 单股止损 8% |
| `max_drawdown_warn` | 0.10 | 回撤预警 10% |
| `max_drawdown_stop` | 0.15 | 回撤止损 15% |
| `position_limit_pct` | 0.25 | 单股最大仓位 25% |
| `index_symbol` | 000300.XSHG | 市场状态指数 |

## 架构

```
portfolio_system/
├── config.py          # 配置
├── market_regime.py   # 市场状态识别
├── risk_control.py    # 风控
├── strategy_pool.py   # 策略池
├── portfolio_engine.py # 组合引擎
├── backtester.py      # 回测
├── simulator.py       # 模拟交易
├── performance.py     # 绩效报告
├── run_example.py     # 示例
├── tests/             # 单元测试
└── README.md
```

## 信号流

1. **策略池**：MA/RSI/MACD/KDJ/Breakout 生成信号
2. **市场状态**：指数 MA 判断 BULL/NEUTRAL/BEAR → 仓位比例
3. **风控**：止损、回撤、市场风险 → 仓位调节
4. **组合引擎**：聚合信号 + 仓位 → 最终 BUY/SELL
5. **回测 / 模拟交易**：执行信号，输出净值与绩效
