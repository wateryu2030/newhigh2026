# AI 基金经理模块

模块化实现：市场判断 → 选股 → 风险评估 → 资金分配 → 交易指令 → 执行。不破坏现有交易代码。

## 目录结构

```
ai_fund_manager/
    manager.py              # 基金经理核心，串联各 Agent
    portfolio_optimizer.py   # 资金分配（等权/风险平价/Kelly/最大夏普）
    execution_engine.py      # 读取 trade_orders.json 并交给执行层
    agents/
        market_agent.py     # 市场趋势与建议仓位
        stock_agent.py      # 股票评分（可扩展 AI）
        risk_agent.py       # 组合风险、最大仓位、止损
```

## 运行示例

### 每日自动运行（仅生成指令）

```bash
# 项目根目录执行
python3 run_fund_manager.py
```

### 指定参数

```bash
python3 run_fund_manager.py --capital 500000 --method equal_weight --top-n 10
python3 run_fund_manager.py --method kelly --top-n 8 --output /path/to/trade_orders.json
```

### 生成并执行（模拟）

```bash
python3 run_fund_manager.py --execute --dry-run
```

### 生成并真实执行

```bash
python3 run_fund_manager.py --execute
```

### Python 调用示例

```python
from ai_fund_manager.manager import AIManager
from ai_fund_manager.execution_engine import execute_with_callback

# 1. 生成交易指令
manager = AIManager(capital=1_000_000, portfolio_method="equal_weight", top_n=10)
result = manager.run()
print("Market:", result["market"])
print("Positions:", result["positions"])
print("Orders file:", result["orders_path"])

# 2. 执行（dry_run 仅模拟）
exec_result = execute_with_callback(orders_path=result["orders_path"], dry_run=True)
print("Planned trades:", exec_result["trades"])
```

### 输出文件 trade_orders.json 示例

```json
{
  "timestamp": "2026-02-23T16:53:22",
  "capital": 1000000,
  "market": {
    "market_trend": "bullish",
    "risk_level": 0.35,
    "recommended_position": 0.65
  },
  "risk": {
    "portfolio_risk": 0.3,
    "max_position": 0.7,
    "stop_loss": 0.08
  },
  "positions": {
    "600519": 0.15,
    "000001": 0.12
  },
  "orders": [
    {"symbol": "600519", "side": "BUY", "weight": 0.15, "target_value": 150000, "stop_loss": 0.08}
  ]
}
```

## 定时任务（每日自动）

```bash
# crontab 示例：每个交易日 9:00 执行
0 9 * * 1-5 cd /path/to/astock && python3 run_fund_manager.py >> logs/fund_manager.log 2>&1
```

## 依赖

- 数据库：DuckDB（或现有 SQLite）中有指数与股票 K 线时，MarketAgent / StockAgent 自动使用。
- 执行层：可选依赖 `backend.trading.order_executor` 或 `backend.execution.order_manager`；未安装时仅生成 JSON，不执行下单。
