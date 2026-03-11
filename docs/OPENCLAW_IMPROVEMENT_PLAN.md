# Cursor 执行计划：改进红山量化系统并集成 OpenClaw 自我进化

> 本文档为 Cursor（或其他 AI 开发者）提供可执行的改进计划，将现有系统升级为更稳健、可扩展、具备自我进化能力的平台。计划围绕 **OpenClaw 自我进化能力** 的集成展开。  
> **与现有仓库的对应**：路径以本仓库为准（如 `execution-engine/` 即执行层，`gateway/src/gateway/` 即 API；现有 `scripts/openclaw_evolution_cycle.py`、`evolution-engine/`、`strategy-evolution/`、`ai-optimizer/` 可与 OpenClaw 进化引擎合并或扩写）。

---

## 1. 目标概述

在现有项目基础上，完成以下核心改造：

- **架构升级**：从单进程串行调度转为事件驱动 + 任务队列，支持多用户、高并发。
- **数据增强**：多源数据接入、增量更新、缓存加速。
- **回测与策略**：完善回测模型（滑点/手续费/多标的），打通 AI 生成 → 回测 → 策略市场闭环。
- **执行与风控**：实现模拟盘引擎，内置可配置风控规则。
- **前端体验**：移动端适配、状态友好、性能优化。
- **可观测性**：统一日志、链路追踪、健康检查、监控告警。
- **安全合规**：认证鉴权、配置加密、审计日志。
- **核心亮点**：利用 **OpenClaw** 实现策略的**自我进化**，使系统能自动优化策略组合，持续提升收益风险比。

---

## 2. OpenClaw 自我进化能力集成方案

### 2.1 什么是 OpenClaw？

OpenClaw 是本项目设想的一种**开放式进化算法框架**，用于自动发现、组合、优化交易策略。其核心思想：

- 将现有策略（包括 AI 模型输出、经典技术指标、自定义规则）视为 **“基因”**。
- 通过遗传编程、强化学习或贝叶斯优化等方法，对基因进行**交叉、变异、选择**，生成新的策略。
- 新策略经回测评估后，若表现优于现有策略池中的一定比例，则自动加入策略市场，完成自我进化。

### 2.2 集成 OpenClaw 的具体步骤

1. **策略基因表示**：将每个交易策略抽象为一个可序列化的配置对象，包含：
   - 信号生成规则（如 `when(emotion_cycle > 0.8) and (hotmoney_seat in top3)`）
   - 仓位管理规则（如 `固定比例`、`凯利公式`）
   - 止盈止损规则
   - 其他参数（如持仓周期、过滤条件）

2. **进化引擎模块**：新建 `openclaw_engine/` 目录（或扩展现有 `evolution-engine/`、`strategy-evolution/`），包含：
   - `genetic_programming.py`：实现遗传编程，对策略规则树进行交叉、变异。
   - `evaluation.py`：调用回测引擎评估策略个体，返回适应度（如夏普比率、卡玛比率）。
   - `population_manager.py`：管理策略种群（当前策略市场中的策略），负责选择、淘汰。
   - `evolution_orchestrator.py`：协调进化周期，定期触发进化任务。

3. **与现有系统集成**：
   - 在 `strategy-engine` 中，将 `trade_signals` 的来源扩展为：**静态策略** + **动态进化策略**。
   - 将策略市场数据（当前为 `trade_signals` 的 strategy_id 聚合 + 回测结果）作为进化引擎的“基因库”；可新增 `strategy_market` 表存储策略规则、参数、历史表现。
   - 进化引擎生成的优秀策略，经回测验证后，自动写入策略市场并标记为可启用，即可被交易系统使用。
   - 回测结果（可新增 `backtest_results` 表）作为进化选择的依据。

4. **调度与触发**：
   - 在 `system_core` 中增加进化任务，可每日或每周运行一次进化周期（或通过 Celery Beat 调度）。
   - 进化周期流程：加载当前活跃策略 → 遗传操作生成子代 → 回测子代 → 更新策略市场。

### 2.3 关键代码示例（遗传编程核心）

```python
# openclaw_engine/genetic_programming.py（或 strategy_evolution/genetic.py）
import random
from typing import List, Dict

class StrategyGene:
    def __init__(self, rule_tree: dict, params: dict):
        self.rule_tree = rule_tree  # 规则树，如 {'and': [{'>': ('emotion_cycle', 0.8)}, ...]}
        self.params = params        # 参数，如 {'position_pct': 0.1, 'stop_loss': 0.05}

def crossover(parent1: StrategyGene, parent2: StrategyGene) -> StrategyGene:
    """单点交叉：交换规则树的子树"""
    # 实现略
    pass

def mutate(gene: StrategyGene, mutation_rate: float) -> StrategyGene:
    """变异：随机修改规则节点或参数"""
    # 实现略
    pass

def selection(population: List[Dict], fitness_scores: List[float], elite_size: int) -> List[StrategyGene]:
    """锦标赛选择 + 精英保留"""
    # 实现略
    pass
```

---

## 3. 总体任务分解

按 **P0–P2** 优先级分为 4 个阶段。路径与模块以本仓库为准：`gateway` 即 `gateway/src/gateway/`，`execution` 即 `execution-engine/`，`data-pipeline` 即 `data-pipeline/`。

### 阶段 0：基础架构改造（2–3 周）

**目标**：建立任务队列、配置中心、模拟盘基础，为后续进化提供支撑。

| 任务ID | 任务名称 | 详细描述 | 涉及文件/模块 | 依赖 |
|--------|----------|----------|---------------|------|
| 0.1 | **引入 Celery 任务队列** | 安装 Celery+Redis，将 `system_core` 中各 orchestrator 改为异步任务；编写任务调度器（Celery Beat）。 | `system_core/` 拆分为 tasks/；新增 worker 入口；`gateway` 提交回测任务 | 无 |
| 0.2 | **配置中心化** | 创建 `core/config.py`（或 `core/src/core/config.py`），使用 pydantic-settings 加载环境变量；统一各模块配置。 | 各模块配置、`.env.example` | 无 |
| 0.3 | **模拟盘引擎基础** | 在 `execution-engine/` 下实现模拟执行：监听 `trade_signals` 生成模拟订单，维护持仓和资金表。 | `execution-engine/`，新增表：positions, orders, account_snapshots（可放在 DuckDB 或单独库） | 无 |
| 0.4 | **数据源抽象与增量更新** | 重构 `data-pipeline`，支持多数据源插件；实现每日增量更新日K、龙虎榜等。 | `data-pipeline/`，`duckdb_manager.py` | 无 |
| 0.5 | **健康检查与基础监控** | 增强 `/health` 端点；集成 Prometheus 客户端，暴露基本指标。 | `gateway/app.py`，新增 `monitoring/` 或 `gateway/metrics.py` | 无 |

### 阶段 1：核心业务闭环（3–4 周）

**目标**：完善回测、策略市场、风控，并首次集成 OpenClaw 基础进化能力。

| 任务ID | 任务名称 | 详细描述 | 涉及文件/模块 | 依赖 |
|--------|----------|----------|---------------|------|
| 1.1 | **回测引擎增强** | 支持多标的组合回测、滑点/手续费模型；基于 vectorbt 优化性能。 | `backtest-engine/` | 0.1, 0.2 |
| 1.2 | **策略市场数据闭环** | 回测结果写入策略市场存储（如 `strategy_market` 表）；前端策略市场页查询真实数据。 | `backtest-engine/`，`gateway` 策略接口，`frontend` 策略页 | 1.1 |
| 1.3 | **风控模块** | 实现可配置风控规则（单票上限、行业集中度、止损线等）；在信号生成后、执行前调用。 | 新增 `risk-engine/` 或扩展现有，数据库 `risk_rules`，与 `strategy-engine` 集成 | 0.3 |
| 1.4 | **OpenClaw 进化引擎 V1** | 实现策略基因表示、遗传操作基础、与回测引擎的适配。 | 新建 `openclaw_engine/` 或扩展 `evolution-engine/`：gene.py, genetic.py, evaluation.py | 1.1, 1.2 |
| 1.5 | **进化调度与集成** | 将进化任务加入 system_core 或 Celery Beat，定期执行进化周期，优秀策略自动入库。 | `system_core/` 或 tasks/，`openclaw_engine/orchestrator.py` | 1.4 |
| 1.6 | **认证与审计** | 添加 JWT 认证与登录接口；审计日志中间件。 | `gateway` middleware 与 routers，表 users, audit_log | 0.2 |

### 阶段 2：前端与运维优化（3–4 周）

**目标**：提升用户体验，容器化部署，完善可观测性。

| 任务ID | 任务名称 | 详细描述 | 涉及文件/模块 | 依赖 |
|--------|----------|----------|---------------|------|
| 2.1 | **前端移动适配** | Tailwind 响应式、底部导航、PWA 支持。 | `frontend/` | 无 |
| 2.2 | **数据获取层优化** | React Query 统一 API 状态；加载、错误、空状态组件。 | `frontend/` hooks 与 components | 无 |
| 2.3 | **容器化部署** | Dockerfile（Python 后端、Node 前端），docker-compose 整合服务。 | 根目录 Dockerfile, docker-compose.yml | 0.1, 0.2 |
| 2.4 | **监控告警系统** | Prometheus + Grafana；关键指标与告警（数据延迟、回撤超限）。 | `monitoring/`，Grafana dashboard | 0.5 |
| 2.5 | **日志集中化** | 日志格式 JSON，通过 Filebeat 或 Loki 收集。 | 各模块日志配置，`logging_config.py` | 无 |

### 阶段 3：高级进化与实盘准备（持续）

**目标**：增强 OpenClaw，接入实盘接口，完善测试与文档。

| 任务ID | 任务名称 | 详细描述 | 涉及文件/模块 | 依赖 |
|--------|----------|----------|---------------|------|
| 3.1 | **OpenClaw 进化增强** | 引入强化学习（如 Stable-Baselines3）；多目标优化（收益、回撤、换手率）。 | `openclaw_engine/rl/`，multi_objective | 1.4 |
| 3.2 | **实盘接口封装** | 对接券商/模拟 API，统一交易接口；实盘/模拟盘开关。 | `execution-engine/brokers/`，gateway 开关接口 | 1.3, 2.3 |
| 3.3 | **测试体系搭建** | pytest 单测与集成测试，Playwright E2E；CI 集成。 | `tests/`，`.github/workflows/` | 无 |
| 3.4 | **文档自动化** | mkdocs 构建文档；同步更新状态文档。 | `docs/`，`mkdocs.yml` | 无 |

---

## 4. 关键技术决策与注意事项

- **数据库**：DuckDB 保持为分析库；用户、风控规则、审计等事务数据可新增 PostgreSQL，或仍在 DuckDB 内单写者 + WAL 保证写安全。
- **任务队列**：Celery + Redis；后续可扩展为 RabbitMQ。
- **OpenClaw**：初期遗传编程（可选用 `deap`）；后期引入 RL。
- **安全**：JWT 密钥、数据库密码等仅通过环境变量注入，禁止提交代码库。
- **性能**：回测异步执行，支持取消与超时。

---

## 5. 测试与验收标准

- **功能**：相关模块有单测/集成测试覆盖核心逻辑。
- **性能**：策略市场查询 &lt;200ms，回测任务提交 &lt;100ms。
- **可观测**：日志与指标可采集，告警可触发。
- **OpenClaw**：能生成至少 10 个新策略；新策略平均夏普不低于当前策略池中位数。

---

## 6. 风险与应对

| 风险 | 应对 |
|------|------|
| DuckDB 并发写 | 单写者 + 队列串行化，或事务数据迁至 PostgreSQL。 |
| 遗传编程过早收敛 | 多样性保持（如岛屿模型、共享适应度）。 |
| 回测过拟合 | 进化评估使用样本外或交叉验证。 |
| 实盘对接复杂 | 先对接模拟盘 API，再对接真实券商。 |

---

## 7. 开始执行指南

1. 创建分支 `feature/phase0-arch-upgrade`（或按团队规范命名）。
2. 按阶段 0 任务顺序逐个实现并提交。
3. 每完成一阶段运行 `python -m system_core.system_runner --once` 或 `scripts/run_full_cycle.py` 验证整体可用。
4. Phase 1 完成后启动 OpenClaw 进化任务，观察策略市场是否自动更新。
5. 更新 `PROJECT_STATUS.md` 与 `docs/PROJECT_HANDOFF_FOR_AI.md` 反映进展。

**Cursor**：请参照本文档与 `tasks/current_task.md`、`tasks/backlog.md` 逐步推进；优先从阶段 0 中依赖为「无」的任务开始（如 0.2 配置中心、0.5 健康检查与监控）。
