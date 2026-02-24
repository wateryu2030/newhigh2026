# AI 自进化量化交易系统

自动生成策略、优化参数、回测、评分、保存最佳策略，支持循环进化与实盘反馈。

## 目录结构

| 文件 | 说明 |
|------|------|
| `strategy_generator.py` | 随机生成技术策略（MA/RSI/MACD/突破/动量） |
| `parameter_optimizer.py` | 遗传算法 GA：种群、交叉、变异、选择 |
| `backtest_engine.py` | 回测适配：调用现有 `run_plugin_backtest`，输出 return/sharpe/drawdown |
| `strategy_evaluator.py` | 评分：`0.4*return + 0.3*sharpe - 0.3*drawdown` |
| `strategy_repository.py` | 存储：DuckDB 或 JSON，保存最佳/历史策略 |
| `evolution_manager.py` | 进化流程：生成→优化→回测→评分→保存，支持多轮 |
| `live_feedback.py` | 实盘反馈：记录真实收益、滑点、成本，供再优化 |

## 运行

```bash
# 默认：000001.XSHE，2024-01-01~2024-12-31，3 轮进化
python run_evolution.py

# 自定义标的与区间
python run_evolution.py --stock 600519.XSHG --start 2023-01-01 --end 2024-12-31 --rounds 5

# GA 规模
python run_evolution.py --population 20 --generations 10
```

## 依赖

- 项目已配置 DuckDB 与插件策略（`strategies/`），回测依赖 `run_backtest_plugins.run_plugin_backtest`。
- 需先有日线数据（`data/quant.duckdb`），否则回测会返回无效指标。

## 扩展

- 在 `strategy_generator.py` 的 `PARAM_SPACES` 中增加或修改参数范围。
- 在 `strategy_evaluator.py` 中调整权重或评分公式。
- 实盘对接后通过 `live_feedback.LiveFeedback` 记录成交与日盈亏，再在进化中引入真实收益目标。
