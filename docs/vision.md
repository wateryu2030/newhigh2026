# AI 基金经理 / 红山量化 愿景

> Cursor 接力开发时优先阅读本文，明确系统目标与最终形态。

---

## 目标

构建一个 **AI 基金经理系统**，实现三件事：

1. **AI 基金经理（量化 + 强化学习）**  
   自动策略生成、评估、优化；未来演进为 AI CIO → Macro / Quant / PM / Trader 多 Agent。

2. **交易系统（回测 → 自动交易）**  
   数据 → 扫描 → AI 分析 → 策略信号 → 回测验证 → 风控 → 执行；全链路可运行、可监控。

3. **可视化平台（UI + 移动端）**  
   Dashboard、系统监控、策略排名、资金曲线、AI 决策解释；支持桌面与移动端查看。

---

## 最终形态

- **AI → 生成策略**（因子/技术/融合/RL）
- **AI → 评估策略**（回测、Sharpe、回撤、风险）
- **AI → 自动交易**（信号 → 风控 → 执行）
- **人 → 只做监督**（参数边界、风控阈值、开关策略）

---

## 与本仓库的对应关系

| 愿景块         | 当前模块 |
|----------------|----------|
| 自动数据采集   | data-pipeline, data-engine, system_core (data_orchestrator) |
| 自动策略/信号  | market-scanner, ai-models, strategy-engine, system_core (scan/ai/strategy orchestrator) |
| 回测与风控     | backtest-engine, risk-engine |
| 自动交易       | execution-engine |
| 统一调度       | system_core (system_runner) |
| UI 可视化      | frontend, gateway |

详见 `docs/architecture.md`、`PROJECT_STATUS.md`。
