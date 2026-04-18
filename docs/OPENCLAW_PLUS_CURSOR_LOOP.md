# OpenClaw 调度 + Cursor 执行：闭环迭代建议

## 结论（可以直接采用）

**可以**把角色拆成：

| 角色 | 负责 |
|------|------|
| **制定迭代计划** | 人 + 仓库文档（`docs/OPENCLAW_IMPROVEMENT_PLAN.md`、`tasks/current_task.md`、`tasks/backlog.md`） |
| **发起与调度** | OpenClaw（定时任务、Heartbeat、会话提醒） |
| **写代码、跑测试、提交** | **以 Cursor 为主**（本机交互或 CLI/自动化能力允许时再接脚本） |

这样通常比「指望 OpenClaw 单会话自动改完整仓库」**更稳**：调度层轻、执行层工具链成熟。

---

## 推荐闭环（最小可落地）

```
计划文档（仓库内）
    ↑ 更新
OpenClaw 定时 / 心跳 → 只负责「提醒 + 可选写 handoff 文件」
    ↓
人或用脚本打开 Cursor，按 handoff / current_task 执行
    ↓
pytest / npm build、git commit
    ↓
evolution/improvement_log_*.md 记一笔
```

**要点**：OpenClaw **不必**直接具备写满整个 monorepo 的能力；它只要保证**每次迭代有人类或 Cursor 能读到「下一步是什么」**。

---

## 三种落地强度（由浅到深）

### A. 纯人工接力（已可用）

1. 计划写在 `tasks/current_task.md`。  
2. OpenClaw 定时任务文案指向：**读该文件 + OPENCLAW_ORCHESTRATION**（见 `docs/OPENCLAW_SCHEDULED_TASKS.md`、`docs/OPENCLAW_AUTONOMOUS_DEVELOPMENT_SETUP.md` §五）。  
3. 你收到提醒后，在 **Cursor** 里打开 `/Users/apple/Ahope/newhigh` 执行开发。  

**优点**：无额外脚本；**缺点**：依赖人点进 Cursor。

### B. Handoff 文件（推荐加一层）

仓库已提供 **`tasks/openclaw_handoff.md`**（必读顺序 + 贴给 OpenClaw 的短提示 + 一键 `make openclaw-iterate-ready`）。也可由 Cron 只追加一段到 `current_task.md` 顶部「本轮 OpenClaw 要求」：

- OpenClaw **不**直接改业务代码，只 **write** 或 **提醒人去写** 该文件（二选一，视权限而定）。  
- Cursor 侧工作流：**打开仓库 → 先读 handoff → 再动手**。  

**优点**：调度与执行边界清晰；**缺点**：仍需 Cursor 里有人或后续自动化读该文件。

### C. Cursor CLI / 外部自动化（可选、视本机能力）

本机已具备 **`cursor agent`**（无头：`--print`，改仓库：`--force`）时，可用仓库脚本 **串联 OpenClaw 规划 → Cursor 执行**：

```bash
cd /Users/apple/Ahope/newhigh
# 一键：OpenClaw（local）写 evolution/openclaw_cursor_last_plan.md → Cursor Agent 按文件执行
bash scripts/openclaw_cursor_iterate.sh

# 或：make openclaw-cursor-iterate
```

仅生成规划、不自动跑 Cursor（便于审阅后再手动 `cursor agent ...`）：

```bash
OPENCLAW_CURSOR_PLAN_ONLY=1 bash scripts/openclaw_cursor_iterate.sh
```

更保守（不显式 `-f`，可能需人工批准工具）：

```bash
CURSOR_AGENT_FORCE=0 bash scripts/openclaw_cursor_iterate.sh
```

**前置**：`cursor agent login` 或设置 `CURSOR_API_KEY`；详见 `cursor agent --help`。

**注意**：`-f` 会放宽命令执行策略，仅在你信任仓库与规划内容时使用；建议先 **B** 或 **仅规划**，再开 **全自动 C**。

---

## 四、防循环（Web）与良性闭环（终端，推荐）

### 现象

在 **OpenClaw Web** 里用 **DeepSeek**，若提示词要求 **反复 `read` 同一仓库文件**（如 `.github/workflows/ci.yml`），模型容易进入**同一句复读**（「让我查看…」循环），**与任务是否重要无关**。

### 分工（请固定采用）

| 层级 | 工具 | 职责 |
|------|------|------|
| **调度 / 轻量提醒** | OpenClaw Web、Heartbeat、Cron | 提醒「该跑闭环脚本了」；**不要**指望 Web 里读完整个 monorepo |
| **规划（LLM）** | `openclaw agent --local`（脚本已内联 `current_task` + 编排 §2） | 生成 `evolution/openclaw_cursor_last_plan.md`，**不依赖** Web 的 read 工具 |
| **落地改代码** | **`cursor agent -p -f`**（Cursor CLI） | 读规划文件、改仓库、跑命令 |

### 一键良性闭环（调度 → 规划 → Cursor 执行）

在仓库根执行（**不要用 Web 长对话代替这一步**）：

```bash
cd /Users/apple/Ahope/newhigh
chmod +x scripts/openclaw_benign_loop.sh   # 首次
bash scripts/openclaw_benign_loop.sh
# 等价：make openclaw-cursor-iterate
```

仅生成规划、不自动跑 Cursor：

```bash
OPENCLAW_CURSOR_PLAN_ONLY=1 bash scripts/openclaw_benign_loop.sh
```

### Web 会话若仍要用 OpenClaw

- **模型**：优先 **通义 Qwen**，避免 **DeepSeek** 与「读文件」工具链叠加复读。  
- **提示词**：**禁止**要求连续 `read` 多个路径；需要看 CI 时，在**终端**执行  
  `sed -n '1,200p' .github/workflows/ci.yml` **把输出粘贴进聊天**，或只发 **`tasks/openclaw_followup_prompt.md` 的正文**（不要求 agent 再 read）。  
- 详见 **`tasks/openclaw_followup_prompt.md`**（已针对「防循环」修订）。

---

## OpenClaw 侧不要做什么

- 不要依赖 **`python3 scripts/news_collector.py`** 等不存在路径（见 `docs/OPENCLAW_CRON_POLICY_COLLECTOR.md`）。  
- 不要让开发向 Cron **只返回 NO_REPLY** 且无日志（见 `docs/OPENCLAW_DSML_HEARTBEAT_STUCK.md`）。  

---

## 与现有文档的关系

- 编排与任务选取：`docs/OPENCLAW_ORCHESTRATION.md`  
- 自主开发环境（symlink、Skills、提示词）：`docs/OPENCLAW_AUTONOMOUS_DEVELOPMENT_SETUP.md`  
- Cursor 侧提示词模板：`docs/CURSOR_OPENCLAW_AGENT_PROMPTS.md`  

---

*本页描述「理想分工」与可演进路径；落地以本机 Cursor / OpenClaw 版本能力为准。*
