# OpenClaw 提交用：红山量化平台 — 实体证券支持 · 自我迭代开发任务

> **用途**：将本文整体复制到 OpenClaw 会话、或写入 `~/.openclaw/workspace/HEARTBEAT.md` 的「当日任务」、或 Cron 任务描述；与仓库根 `OPENCLAW_HONGSHAN_ENTITY_TRADING.yaml` 配套使用。

---

## 一、任务名称

**hongshan-entity-securities-self-iteration**（红山量化 · 实体证券能力持续迭代与自我修复）

---

## 二、目标（北极星）

在 **安全、合规、可观测** 前提下，让 **红山量化平台**（newhigh 主栈 + `integrations/hongshan` 子栈 + 微信小程序）**更好支持实体证券业务**：从数据、策略、回测、模拟/纸交易到 **与真实经纪通道可对接的执行与持仓闭环**，并保留清晰的 **模拟 ↔ 实盘** 边界。

---

## 三、自主执行原则（自我修复）

1. **先恢复绿再扩功能**：任一环节失败（pytest、导入错误、Gateway `/health` degraded、DuckDB 锁冲突），**优先定位根因并修复**，再进入下一功能点。
2. **最小改动**：单 PR/单次提交只做一条可验证主线；禁止无关大重构。
3. **测试驱动**：改执行层 / Gateway 契约须补或更新测试（`pytest`、`gateway/tests`、相关包 `tests/`）。
4. **记录**：在 `evolution/` 或当日 `improvement_log` 中写清：改了什么、为何、如何验证。
5. **密钥与实盘**：**禁止**将 token、账户密码写入仓库；真实下单能力仅通过环境变量与显式开关启用。

---

## 四、当前仓库上下文（执行前必读）

| 区域 | 说明 |
|------|------|
| **Gateway** | `gateway/` FastAPI，`/api/*` 与 JWT、公开只读白名单（行情/总览等） |
| **执行层** | `execution-engine/`：`brokers/`（Simulated / Live）、`paper_trading`、与 `trade_signals` 消费链 |
| **数据** | `data-pipeline/` + `data/quant_system.duckdb`；Tushare 增量脚本 `scripts/run_tushare_incremental.py` |
| **红山子栈** | `integrations/hongshan/`（8010 API、Vue、政策新闻）；与 8000 Gateway 并行 |
| **小程序** | `integrations/hongshan/wechat-miniprogram/`，`config.publicBrowseMode` 控制上架前开放浏览 |
| **进化与任务** | `openclaw_engine/`、`OPENCLAW_*.yaml`、`scripts/openclaw_*.sh` |

---

## 五、迭代工作流（建议优先级）

### P0 — 稳定性与契约

- Gateway 与 execution-engine **订单/持仓/模拟盘** API 字段名、错误码与前端/文档一致。
- **DuckDB 单写者冲突**：任务编排与文档一致（跑增量前停重复 Gateway 等）。
- 关键路径 **smoke**：`pytest` 相关模块 + 可选 `scripts/check_frontend_backend.sh`。

### P1 — 实体证券「可对接」能力

- **LiveBroker / 经纪适配层**：接口抽象（下单、撤单、查询持仓与资金），实现可插拔；默认仍 **模拟**。
- **对账与快照**：持仓、成交、资金与策略信号时间对齐；缺失数据可告警（对接 `/api/system/*` 已有能力）。
- **A 股规则**：交易时段、代码规范化（沿用 `core/ashare_symbol`）、涨跌停与风险展示（只读亦可）。

### P2 — 红山产品与渠道

- **Hongshan API / Vue** 与主 Gateway 能力 **对齐或显式降级**（避免双栈语义冲突）。
- **微信小程序**：开放浏览期过后，`publicBrowseMode=false` 与 **注册用户权益**（配额、问答、级别）联动测试。

### P3 — 合规与运营

- 文案：风险提示、非投资建议声明已在小程序/关于页；扩展至关键交易入口。
- 审计：关键操作留痕（结构化日志占位即可）。

---

## 六、完成定义（DoD）

- [ ] 选定工作流中至少 **1 条 P0/P1** 闭环可演示（接口 + 测试 + 简短说明）。
- [ ] **无新增未解释的失败测试**；若跳过测试须写明原因与后续项。
- [ ] **evolution/** 或等价日志中有 **一条** 本次迭代摘要。

---

## 七、推荐 OpenClaw Skills / 规则

- 全局：`api-and-interface-design`、`security-and-hardening`、`test-driven-development`
- 本仓：`.cursor/skills/` 下 A 股行情/投研类 skill（与实体证券数据展示协同）

---

## 八、一键参考命令（人类或 Agent 自检）

```bash
cd /Users/apple/Ahope/newhigh && source .venv/bin/activate
PYTHONPATH=gateway/src:core/src:data-pipeline/src python3 -m pytest gateway/tests/ -q
bash scripts/check_frontend_backend.sh   # 需本机 Gateway
```

---

*版本：与仓库同步；任务发布者可根据排期删减 P2/P3。*
