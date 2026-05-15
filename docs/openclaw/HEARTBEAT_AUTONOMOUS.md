# OpenClaw 自主迭代（与 newhigh 仓库绑定）

## 最高优先级（解决「只出现 DSML read HEARTBEAT、迭代无进展」）

本文件同步位置为 **`~/.openclaw/workspace/HEARTBEAT.md`**。OpenClaw 系统常**强制先读此路径**，界面会反复出现类似：

`<|DSML|> … read … HEARTBEAT.md …`

**读完本文件后，本轮不得结束。** 你必须再发起至少一次 **read** 或 **exec**，且目标为**主仓**内文件（见下）。  
**禁止**在仅读完 `HEARTBEAT.md` 后就回复 **`HEARTBEAT_OK`**（除非已同时读完 `current_task.md` 并写出「下一步要改的文件 + 验证命令」，或明确说明无写权限）。

**路径规则（必读）**：工作区根目录是 `~/.openclaw/workspace/`，**不是**主仓根。文中 **`docs/...` 相对路径默认指向工作区根下的 `docs/`，往往不存在。**  
迭代开发请**优先使用绝对路径**，或 **`newhigh/` 前缀**（若已执行 `ln -sf /Users/apple/Ahope/newhigh ~/.openclaw/workspace/newhigh`）：

| 用途 | 正确路径示例 |
|------|----------------|
| 当前任务 | `/Users/apple/Ahope/newhigh/tasks/current_task.md` 或 `newhigh/tasks/current_task.md` |
| 编排 | `/Users/apple/Ahope/newhigh/docs/OPENCLAW_ORCHESTRATION.md` 或 `newhigh/docs/OPENCLAW_ORCHESTRATION.md` |
| 改进计划 | `/Users/apple/Ahope/newhigh/docs/OPENCLAW_IMPROVEMENT_PLAN.md` 或 `newhigh/docs/...` |

**一轮心跳内最低产出**：在回复中写出 **1 条**具体下一步（文件名或命令），或 **1 段**终端/工具输出；仅「已读 HEARTBEAT」不算进展。

---

> **部署位置**：本文件应同步为 `~/.openclaw/workspace/HEARTBEAT.md`（或作为其主体），使 Heartbeat / Cron **按同一套计划**执行。  
> **仓库根**：`/Users/apple/Ahope/newhigh`（若工作区用符号链接 `newhigh`，请先 `cd` 到该路径再操作）。

> **OpenClaw 定时任务**：勿用不存在的 `python3 scripts/news_collector.py`；政策采集见 `scripts/run_policy_news_collect_retry.sh`。若定时只触发「外网采集」，无法替代平台开发闭环，请改用 **`docs/OPENCLAW_SCHEDULED_TASKS.md`** 中的迭代文案。

### 首轮动作（避免只回复 HEARTBEAT_OK）

1. 若系统已要求读 `HEARTBEAT.md`，可略读；**紧接着必须 read**：`/Users/apple/Ahope/newhigh/tasks/current_task.md`（或 `newhigh/tasks/current_task.md`）。  
2. 再 read：`/Users/apple/Ahope/newhigh/docs/OPENCLAW_ORCHESTRATION.md`（勿用无 `newhigh/` 前缀的 `docs/...`）。  
3. 执行 **§B** 中一步（至少给出：选定条目、将改哪些路径、验证命令）；若环境不允许写仓库，**写明**限制，勿只回 OK。  
4. **禁止**：仅读完本 HEARTBEAT、未读 `current_task.md`、未给出任何下一步动作时，就回复 `HEARTBEAT_OK`。

---

## A. 每次运行前必读（严格顺序）

1. `docs/OPENCLAW_ORCHESTRATION.md` — 编排与任务选取规则  
2. `docs/OPENCLAW_TASK_ENTITY_SECURITIES_ITERATION.md` — 实体证券支持 + 自我修复闭环  
3. `docs/OPENCLAW_IMPROVEMENT_PLAN.md` — §3 总体任务分解 / 阶段表（只选 **当前阶段内 1 条** P0/P1）  
4. `OPENCLAW_HONGSHAN_ENTITY_TRADING.yaml` — 工作流与约束速查  

若路径不存在，说明工作区未链到主仓：在 `~/.openclaw/workspace/` 下检查 `newhigh` 是否指向本仓库。

---

## B. 单次迭代循环（重复直到本段任务完成或超时）

| 步骤 | 动作 |
|------|------|
| B0 | **若改 Web/小程序导航**：只编辑 `config/navigation_manifest.json`，在仓库根执行 `make sync-nav`，并提交 `menu.generated.js`（与 `docs/OPENCLAW_ORCHESTRATION.md` §4.5 一致）。 |
| B1 | **选 1 条任务**：从编排文档的 P0/P1 中选最小可验证项，写入会话首条回复。 |
| B2 | **读代码**：定位涉及文件（`gateway/`、`execution-engine/`、`data-pipeline/` 等），不无关重构。 |
| B3 | **实现**：小步提交；Python 类型与现有风格一致。 |
| B4 | **验证**：运行 `pytest` 相关测试；必要时 `bash scripts/check_frontend_backend.sh`（需 Gateway）。 |
| B5 | **失败自愈**：红则修实现或测试，**不**扩大范围；仍失败则记录阻塞原因到 `evolution/`。 |
| B6 | **记录**：在 `evolution/improvement_log_YYYY-MM-DD.md`（或当日日志）追加一节：任务 ID、变更摘要、验证命令与结果。 |

---

## C. 硬约束

- **禁止**将 token、账户密码、私钥写入仓库；仅用 `.env` 本地配置。  
- **默认不启用真实下单**；经纪/实盘开关须显式环境变量。  
- **合并前**确认无未解释的失败测试。

---

## D. 快速验证（仓库根执行）

```bash
cd /Users/apple/Ahope/newhigh && source .venv/bin/activate
PYTHONPATH=gateway/src:core/src:data-pipeline/src python3 -m pytest gateway/tests/ -q
```

---

## E. 与运维心跳的关系

**政策采集、Gateway 巡检、launchd** 等人肉运维见仓库 **`docs/HEARTBEAT.md`**。本文件专注 **代码迭代**；若需合并到同一 Cron，可在 Cron 正文先执行 §D 再执行运维脚本（见 `scripts/heartbeat_check.sh`）。

---

## F. 红山 / 小程序（可选支线）

- `integrations/hongshan/README.md` — 子栈端口与 Docker  
- `integrations/hongshan/wechat-miniprogram/` — `config.publicBrowseMode` 与上架后权益  

仅在任务明确涉及 Hongshan/小程序时打开，避免喧宾夺主。

---

## G. OpenClaw 为何「一直不执行开发任务」（只读 HEARTBEAT / HEARTBEAT_OK）

OpenClaw 常注入类似规则：**读 `~/.openclaw/workspace/HEARTBEAT.md`，若无事项则回复 `HEARTBEAT_OK`**。而本文件 **§A–F 是方法与约束**，不是「今日必改文件列表」。模型读完容易判断为「无紧急项」→ **直接 `HEARTBEAT_OK`** → 看起来像在空转。

另：**开发需要写仓库**。若 Agent 对 `/Users/apple/Ahope/newhigh` **无写权限**、或工作区里 **没有** 主仓目录，则无法真正改代码，只能读文档。

**建议（任选）**：

1. **首轮必读锚点**：在触发心跳的会话里，系统或用户明确要求：**先读** `/Users/apple/Ahope/newhigh/tasks/current_task.md`，再读 `docs/OPENCLAW_ORCHESTRATION.md`，**禁止**在未读取 `current_task.md` 时回复 `HEARTBEAT_OK`。  
2. **同步后自检**：执行 `bash /Users/apple/Ahope/newhigh/scripts/sync_openclaw_heartbeat.sh` 后，确认 `~/.openclaw/workspace/` 下能访问主仓（符号链接 `newhigh` → 主仓，或把本文件内容复制进 HEARTBEAT 并保留绝对路径）。  
3. **落地开发仍以 Cursor 为主**：OpenClaw 适合提醒与轻量命令；合码、跑全量测试、PR 以本机 Cursor 为准。

**一句话**：不是 B1–B6 没用，而是 **系统规则 + 缺具体工单 + 可能无写权限** 叠在一起，表现为「不执行开发」。
