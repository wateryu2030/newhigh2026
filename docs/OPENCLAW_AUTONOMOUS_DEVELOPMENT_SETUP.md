# OpenClaw 自主开发任务：详细配置与排障

目标：让 OpenClaw 不仅能读 `HEARTBEAT.md`，还能在**允许范围内**对 **`/Users/apple/Ahope/newhigh`** 做「选任务 → 读代码 → 改文件 → 跑命令 → 记日志」。  
若某步在本机不可行，文末说明如何用 **Cursor 兜底**。

---

## 一、先建立正确预期

| 能力 | 说明 |
|------|------|
| **自主开发**在工程上 = 能 **读/写仓库文件**、**执行终端**（pytest、npm build 等）、必要时 **git**。 |
| OpenClaw **后台任务**若只触发 `cron` 且返回 **`NO_REPLY`**，聊天窗口里**看不到**改代码过程，容易误以为「没执行」。 |
| 系统若注入「无事则 **HEARTBEAT_OK**」类规则，模型会**跳过**具体开发；需用 **§四** 的 HEARTBEAT 与 **§五** 的提示词约束。 |
| **沙箱**：若工作区不允许写主仓路径，Agent **无法**真正提交代码——必须在 OpenClaw / 节点设置里放行。 |

---

## 二、工作区：让 Agent 能「看见」主仓

OpenClaw 默认读 **`~/.openclaw/workspace/HEARTBEAT.md`**，但文档里的路径多为 **`docs/...`**（相对主仓）。若工作区根目录**不是** newhigh，相对路径会失效。

**推荐（与 `docs/OPENCLAW_SELF_DEV.md` 一致）**：

```bash
# 一键：创建 ~/.openclaw/workspace、symlink、同步 HEARTBEAT
bash /Users/apple/Ahope/newhigh/scripts/openclaw_workspace_bootstrap.sh
```

或手动：

```bash
mkdir -p ~/.openclaw/workspace
ln -sf /Users/apple/Ahope/newhigh ~/.openclaw/workspace/newhigh
bash /Users/apple/Ahope/newhigh/scripts/sync_openclaw_heartbeat.sh
```

之后在提示词或 HEARTBEAT 中可同时写：

- 绝对路径：`/Users/apple/Ahope/newhigh/tasks/current_task.md`
- 或工作区相对路径：`newhigh/tasks/current_task.md`（通过 symlink）

**验证**：在 OpenClaw 里让模型 `read` 上述路径之一，应能返回内容而非 ENOENT。

---

## 三、同步「可执行」的 HEARTBEAT（避免只回 HEARTBEAT_OK）

主仓模板含 **首轮动作**（先读 `tasks/current_task.md`、禁止空回复）：

```bash
cd /Users/apple/Ahope/newhigh
bash scripts/sync_openclaw_heartbeat.sh
```

确认：`~/.openclaw/workspace/HEARTBEAT.md` 已更新，且含 **「首轮动作」** 与 **§G**（见 `docs/openclaw/HEARTBEAT_AUTONOMOUS.md`）。

---

## 四、Skills / 工具 / 会话模式（界面侧）

以下名称以 OpenClaw Web UI 为准（CLI 版本见 `openclaw --version`）；**原则**是：**打开能读写文件与执行命令的能力**。

### 4.1 已在终端可完成的步骤（本机执行）

**一键（工作区 + HEARTBEAT + 本脚本中的 skills 安装）**：

```bash
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
bash /Users/apple/Ahope/newhigh/scripts/openclaw_dev_environment_setup.sh
```

**仅重装 addyosmani skills**：

```bash
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
bash /Users/apple/Ahope/newhigh/scripts/install_openclaw_addyosmani_skills.sh
```

- 会把 **addyosmani/agent-skills** 装到 `~/.agents/skills/`，并处理 `~/.openclaw/skills` 下重复 symlink（与 **`.cursor/rules/openclaw-global-agent-skills.mdc`** 一致：OpenClaw 仍可从 `~/.agents/skills` 直接加载）。  
- 装完后请 **完整重启 OpenClaw Gateway / 本机 OpenClaw App**（见 `docs/OPENCLAW_运行说明.md`），新会话才稳定看到技能。  
- 当前 CLI（如 `openclaw 2026.4.14`）**可能没有** `openclaw skills enable --all`；是否启用某技能以 **Web UI → Skills** 或 `openclaw skills list` 的 `ready` 状态为准。

### 4.2 必须在 OpenClaw 界面手动完成（无法脚本代劳）

1. **Skills（技能）**  
   - 在 **Proxy → Skills**（或 **Settings → Skills**，以你版本为准）中确认 **git-workflow-and-versioning、frontend-ui-engineering、test-driven-development** 等与开发相关的条目为 **ready / 已启用**。  
   - 仓库自定义 A 股/投研技能说明见 **`.cursor/skills/README.md`**（与 ClawHub 包并存）。

2. **聊天顶栏模式（如 `Default (off)`）**  
   - 若表示 **关闭 Agent / 工具调用**，则模型只会「说话」、不会执行 `exec`/`write`。  
   - 请改为 **开启**带 **工具调用 / Agent / Automation** 的模式（以你当前版本下拉菜单为准），否则无法自主开发。

3. **节点 / Nodes / 代理**  
   - 若开发任务在远程节点跑，确认该节点对 **`/Users/apple/Ahope/newhigh`** 有 **读写** 权限（或挂载同一路径）。

4. **定时任务（Scheduled Tasks / Cron）**  
   - **不要**只配置「后台执行、NO_REPLY」且无任何日志落盘——你看不到进度。  
   - 建议：Cron 正文使用 **`docs/OPENCLAW_SCHEDULED_TASKS.md` §3** 的文案，并优先发到 **主会话** 或 **可查看日志的 isolated 会话**；若产品支持「任务输出写入文件」，把路径指到 `newhigh/logs/openclaw-cron.log`。

---

## 五、会话里用的「自主开发」提示词（直接粘贴）

**首条（建立约束 + 绑定路径）**：

```
主仓绝对路径：/Users/apple/Ahope/newhigh（工作区内也可通过 newhigh/ 访问若已做 symlink）。

你必须使用工具：先 read /Users/apple/Ahope/newhigh/tasks/current_task.md，再 read /Users/apple/Ahope/newhigh/docs/OPENCLAW_ORCHESTRATION.md。从编排文档选 1 条最小 P0/P1，列出将修改的文件路径与验证命令（pytest 或 cd frontend && npm run build:clean），并实际执行（若环境允许）。

禁止：仅读完 HEARTBEAT 就回复 HEARTBEAT_OK；禁止同一段话重复多遍。若无法写仓库，明确说明缺少的权限或路径。
```

**若仍只读文档不动手**，追加：

```
本轮必须产出之一：(1) 对具体文件的 patch 或完整文件内容；(2) 或终端命令输出（pytest/npm）。仅摘要文档不算完成。
```

---

## 六、任务来源（避免「没有具体工单」）

| 来源 | 路径 |
|------|------|
| 当前焦点 | `tasks/current_task.md` |
|  backlog | `tasks/backlog.md` |
| 阶段计划 | `docs/OPENCLAW_IMPROVEMENT_PLAN.md` |

人工可定期把 **下一小步**（例如「修 gateway/tests/test_x.py 中某用例」）写进 `current_task.md` 顶栏，OpenClaw 更容易执行**可验证**动作。

---

## 七、后台 `cron` 与 `NO_REPLY` 的用法

- **适合无人值守**：政策采集脚本、`heartbeat_check.sh` 等 **shell**，不依赖大模型写代码。  
- **不适合**指望「cron 一句话 = 全自动改完平台」：开发迭代需要 **多轮工具调用**，应在 **可交互会话** 中完成，或用 **CI（GitHub Actions）** 跑测试。

若 Cron 必须触发「开发向」行为：让 Cron **向会话投递上述 §五 提示词**，并关闭 **仅 NO_REPLY**（或同时写日志到 `newhigh/logs/`）。

---

## 八、与 Cursor 分工（推荐）

| 环节 | 建议 |
|------|------|
| OpenClaw | 读计划、拆任务、试跑命令、草稿 patch |
| Cursor | 审查 diff、`git commit`、复杂重构、全量测试 |
| 合码 | 以本机仓库 `git status` 为准，不以聊天为准 |

---

## 九、自检清单（打勾即过关）

- [ ] `~/.openclaw/workspace/newhigh` → 主仓 symlink 存在（可重复执行 `bash scripts/openclaw_workspace_bootstrap.sh`）  
- [ ] `bash scripts/sync_openclaw_heartbeat.sh` 已执行，HEARTBEAT 含「首轮动作」  
- [ ] OpenClaw 会话 **非**「纯聊天关闭工具」模式（**须在本机 OpenClaw Web/App 中手动打开**，脚本无法代劳）  
- [ ] Skills 含终端/文件（或等价能力）  
- [ ] 在会话中 `read /Users/apple/Ahope/newhigh/tasks/current_task.md` **成功**  
- [ ] 定时任务不是「只 NO_REPLY」且路径不是 `scripts/news_collector.py`（见 `docs/OPENCLAW_CRON_POLICY_COLLECTOR.md`）

---

## 十、相关文档索引

| 文档 | 用途 |
|------|------|
| `docs/openclaw/HEARTBEAT_AUTONOMOUS.md` | B1–B6、§G 为何不执行开发 |
| `docs/OPENCLAW_ORCHESTRATION.md` | 编排顺序、导航单源 |
| `docs/OPENCLAW_SCHEDULED_TASKS.md` | 定时任务文案、政策采集正确命令 |
| `docs/OPENCLAW_AUTONOMOUS_PROMPTS.md` | 防复读、环境纠偏 |
| `docs/OPENCLAW_SELF_DEV.md` | 本机 Heartbeat/Cron 历史说明 |

---

*版本与菜单以本机 OpenClaw 为准；若 UI 与本文不一致，以「工具可用 + 主仓可写」为原则自行映射到对应开关。*
