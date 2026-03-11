# AI 分析 (ai-models)

A股 AI：情绪周期、游资识别、资金轮动，写 market.duckdb 的 market_emotion_state、hotmoney_signals、sector_strength。

## 模块

| 模块 | 输出表 | 说明 |
|------|--------|------|
| emotion_cycle_model | market_emotion_state | 情绪阶段：启动/主升/高潮/退潮/冰点 |
| hotmoney_detector | hotmoney_signals | 龙虎榜游资信号（占位） |
| sector_rotation_ai | sector_strength | 板块强度（占位） |

## 使用

依赖：`data-pipeline`（同库）。通过 `scripts/run_terminal_loop.py` 与扫描器、策略聚合串联运行。
