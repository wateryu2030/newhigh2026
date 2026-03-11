# 产品路线图 / Roadmap

> Cursor 接力开发时结合本文与 `tasks/current_task.md` 确定当前阶段与下一步。

---

## 阶段 1：数据 + 回测 + 基础 UI（当前基础已具备）

- [x] 数据系统：data-pipeline → quant_system.duckdb，system_core 统一调度
- [x] 市场扫描 + AI 模型 + 策略信号：scan / ai / strategy orchestrator
- [x] 基础 UI：Dashboard、数据状态、行情、AI 交易、系统监控、新闻
- [ ] 回测引擎完善：多策略回测、资金曲线、Sharpe/回撤等风险指标
- [ ] 数据层扩展：更多数据源、缓存与时效性

---

## 阶段 2：策略市场 + AI 策略生成

- [ ] 策略市场（Strategy Store）：策略列表、收益/Sharpe/回撤展示、启用/停用
- [ ] AI 策略生成：ai-lab / strategy-engine 生成新策略，回测通过后入库
- [ ] 策略排名与筛选：按收益、风险、标签筛选

---

## 阶段 3：强化学习交易

- [ ] RL Trader：状态、动作、奖励设计；与 backtest-engine / execution-engine 对接
- [ ] 自进化策略：OpenClaw / evolution 与策略池联动
- [ ] 实盘/模拟盘开关与风控硬约束

---

## 阶段 4：AI 基金经理操作系统

- [ ] AI CIO 编排：Macro Analyst / Quant Researcher / PM / Trader 多 Agent
- [ ] 自动调仓与再平衡
- [ ] 移动端核心视图：资金曲线、策略排名、AI 决策解释

---

## 与目录对应

- **阶段 1**：`system_core`、`data-pipeline`、`market-scanner`、`ai-models`、`strategy-engine`、`gateway`、`frontend`、`backtest-engine`
- **阶段 2**：`strategy-engine`、`ai-lab`、`frontend`（策略市场页）
- **阶段 3**：`ai-lab`（rl_trader）、`execution-engine`、`risk-engine`
- **阶段 4**：新模块或现有模块扩展（AI CIO / 多 Agent）
