# 下一步关键升级（建议）

架构已按 **AI Hedge Fund OS** 落地，进化控制层（evolution-engine + ai-fund-manager）已接入。若继续升级，建议优先做以下三块，使系统成为 **真正的 AI Alpha 工厂**：

---

## 1️⃣ LLM Alpha Factory — AI 策略自动生成系统

**目标：** 用 LLM 自动生成可回测的策略（逻辑/参数/规则），而不是只做参数优化。

**可落地点：**
- 在 `ai-lab/strategy_generator` 中接入 LLM（OpenAI/Claude/本地），输入：市场描述、风险偏好、约束；输出：策略类型 + 参数或简单规则描述。
- 输出格式与现有 `strategy-engine`（trend_following / mean_reversion / breakout）或扩展策略 DSL 对接，再交给 backtest-engine 验证。
- 可配合 **Alpha Score** 做生成→回测→评分→只保留高分策略入池。

**产出：** 设计文档 + ai-lab 内 LLM 调用 + 与 evolution-engine 策略池的对接。

---

## 2️⃣ Alpha Score 模型 — 策略评分算法

**目标：** 单一综合分，用于入池决策、排序、资金分配、达尔文淘汰。

**现状：** `evolution-engine/alpha_scoring.py` 已实现基于 Sharpe/Sortino/Drawdown/WinRate/ProfitFactor 的加权 Alpha 分，可入池阈值 `passes_alpha_threshold`。

**可升级方向：**
- 引入实盘表现（live PnL、实盘 Sharpe）与回测指标融合。
- 时间衰减：近期表现权重大于历史。
- 可选：简单 ML 模型（如 XGBoost）用多维度特征预测「未来 Alpha」，替代纯规则加权。
- 与 **Darwin Engine** 的淘汰/进化规则打通（已预留 `should_retire` / `evolve_pool`）。

**产出：** Alpha Score 公式/模型文档 + evolution-engine 内实现迭代。

---

## 3️⃣ Darwin Strategy Evolution — 策略进化算法

**目标：** 自动淘汰劣质策略、保留/进化优质策略，形成闭环。

**现状：** `evolution-engine/darwin_engine.py` 已实现：
- `should_retire`：按 Alpha 分、回撤、实盘时长决定是否淘汰。
- `should_suspend`：按当前回撤暂停。
- `evolve_pool`：一轮进化（BACKTESTED→APPROVED，LIVE→RETIRED），并支持回调 `on_retire` / `on_approve`。

**可升级方向：**
- 策略「进化」：在淘汰前尝试参数微调（Optuna）或规则小改，再回测一次，通过则保留。
- 与 scheduler 打通：定期执行 `evolve_pool`，并将 `on_retire` 与 execution-engine 的「停止该策略下单」、ai-fund-manager 的「从资金分配中移除」联动。
- 策略池持久化：当前为内存；可改为 Postgres/Redis，与 gateway 查询「当前策略列表」一致。

**产出：** 进化策略文档 + evolution-engine/scheduler/ai-fund-manager 的联调与持久化。

---

## 执行顺序建议

1. **Alpha Score** 先固化（含实盘/衰减可选）→ 入池与淘汰标准统一。
2. **Darwin Evolution** 与 scheduler + 执行层联动 → 闭环自动进化。
3. **LLM Alpha Factory** 作为「新策略来源」接入策略池 → 形成「生成→评分→进化」全自动 Alpha 工厂。

Cursor + OpenClaw 可按 `OPENCLAW_TASK_TREE.yaml` 中 `evolution_engine` / `ai_fund_manager` 任务拆模块开发，再按本文三块迭代。
