# OpenClaw「未达预期」复查与改进清单

> 适用于：重启 Gateway/App 后仍感觉 OpenClaw **没有自动改仓库、没有持续迭代、Cron 失败** 等情况。  
> 原则：**OpenClaw 是调度与对话层**；**主仓合码与长跑测试以 Cursor 为准**（见 `docs/OPENCLAW_PLUS_CURSOR_LOOP.md`）。

---

## 一、先对齐预期（避免「设计目标」与产品能力错位）

| 常见预期 | 实际情况 |
|----------|----------|
| OpenClaw 自动在 `/Users/apple/Ahope/newhigh` 里 **git commit** | **默认做不到**。多数会话无持续写主仓权限；Heartbeat 常止于 **读 HEARTBEAT + HEARTBEAT_OK**。 |
| Cron 跑 7 次 = 7 次代码迭代 | Cron 多为 **isolated 会话 + 通知**；若 **飞书投递失败**，整次会标失败，**与是否改代码无关**。 |
| 同步 HEARTBEAT 后就会「自主开发」 | HEARTBEAT 是 **流程说明**；真正开发需 **工具模式 + 明确工单**（`tasks/current_task.md`、`tasks/openclaw_handoff.md`）。 |

---

## 二、根因清单（按优先级自查）

### P0 — Gateway / 进程不健康

- `openclaw doctor` 报 **Gateway not running**、**required secrets unavailable**（见 `docs/OPENCLAW_LOCAL_CHECK.md` §五）。  
- **改进**：修好 LaunchAgent / `.env` 注入，直到 Dashboard `http://127.0.0.1:18789` 可开、日志无持续报错。

### P1 — 飞书通道与 Cron 投递冲突

- 配置里 **feishu: enabled: false**（见 `docs/openclawwateryu1.md` §3.3），但 **Cron 仍选 Feishu 投递** → **`Delivering to Feishu requires target`**。  
- **改进**（必选其一）：  
  - Cron 改为 **`--channel webchat --to last`**（或界面等价项），见 `docs/OPENCLAW_FEISHU_DELIVERY_TARGET.md`；  
  - 或 **关闭该任务的 Announce**；  
  - 或 **完整配置飞书** open_id / 插件后再启用 Feishu。

### P2 — 会话未开「工具 / Agent」

- 顶栏 **Default (off)** 类模式 → 几乎只有文本，**无写文件/执行**。  
- **改进**：在 OpenClaw Web 中打开 **带工具调用 / Agent** 的模式（名称以当前版本为准）。

### P3 — 路径与工作区

- Agent 只读 `~/.openclaw/workspace/HEARTBEAT.md`，**相对路径 `docs/...` 指错目录**。  
- **改进**：已做 `newhigh` symlink + HEARTBEAT 内 **绝对路径**（见 `docs/openclaw/HEARTBEAT_AUTONOMOUS.md`）；定期执行 `make openclaw-iterate-ready`。

### P4 — 任务文档过「虚」

- `tasks/current_task.md` 若长期写「阶段 2/3 已完成」，Agent **没有下一条可执行工单**。  
- **改进**：在文件顶部增加 **一行具体下一步**（例如「改 `xxx.py` 中某用例通过」），或维护 **`tasks/openclaw_handoff.md`** 底部「本轮目标」。

---

## 三、建议的落地顺序（1 小时内可做）

1. 本机执行：`bash scripts/openclaw_status.sh`（见仓库），看 Gateway / CLI 是否正常。  
2. 打开 Dashboard → **Cron Jobs**：对每个失败任务，**改掉 Feishu 投递** 或 **关掉 Announce**。  
3. 在 **Web 聊天**（非 isolated）里发一条：粘贴 `tasks/openclaw_handoff.md` 中的短提示词，看是否出现 **read + 具体下一步**（而非仅 HEARTBEAT_OK）。  
4. 在 **Cursor** 打开主仓，按 `tasks/current_task.md` 做 **一条**可验证修改并 `git commit`。

---

## 四、仓库内已提供的自动化

| 命令 | 作用 |
|------|------|
| `make openclaw-iterate-ready` | symlink、HEARTBEAT、skills、自检提示 |
| `bash scripts/sync_openclaw_heartbeat.sh` | 仅同步 HEARTBEAT |
| `bash scripts/openclaw_status.sh` | 本机 Gateway/CLI 快速探活（见脚本） |

---

## 五、Cron 投递：终端一键改（飞书 → Web 会话 / 关 Announce）

在终端执行（需已安装 Homebrew 的 `openclaw`，且 Gateway 已运行）：

```bash
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# 1) 查看任务与 ID、最近错误（JSON）
openclaw cron list --json

# 2) 将「投递」改为当前 Web 控制台最后使用的会话（等价 webchat last）
#    把 JOB_ID 换成上一步里失败那条的 id
openclaw cron edit JOB_ID --channel last --to last --best-effort-deliver

# 3）若只想关掉对外投递（任务仍跑 Agent，但不因投递失败标红）
openclaw cron edit JOB_ID --no-deliver

# 4）可选：投递失败不拖垮任务状态
openclaw cron edit JOB_ID --best-effort-deliver

# 5）立即试跑该任务（调试用）
openclaw cron run JOB_ID
```

**说明**：若 `openclaw cron list --json` 里已是 `"channel":"webchat","to":"last"` 仍 `error` 且 `lastError` 含 **`400`**，多半是 **Agent/上游 API** 问题，不是飞书；可再加长超时并看日志：

```bash
openclaw cron edit JOB_ID --timeout-seconds 600
openclaw logs --limit 120 --plain
```

---

## 六、Web 里贴 handoff 短提示后「一直循环 / 复读读文件」

**现象**：助手反复输出类似「`tasks/openclaw_handoff.md` 文件：现在让我读取…」且没有实质内容（常见于 **会话里选了 DeepSeek Chat** + 工具读文件流式输出）。

**终端侧（推荐）**：

```bash
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# 把默认模型设回通义（避免 UI 记忆成 DeepSeek）
openclaw models set dashscope/qwen-plus
openclaw models status --json   # 确认 defaultModel
```

然后在 **OpenClaw Web**：**新开一条会话**，模型下拉框选 **通义 Qwen-Plus**（或 `qwen-max`），**不要**选 DeepSeek；再贴短提示。

**仍循环时**：

```bash
# 清理孤儿会话碎片（doctor 会提示时）
openclaw doctor --fix

# 可选：会话存储维护
openclaw sessions cleanup
```

**提示词侧**：不要用「先 read A 再 read B」长链；改为 **直接写清主仓绝对路径 + 一条具体任务**（或把 `openclaw_handoff.md` 正文 **粘贴进聊天**而不是强依赖 `read` 工具）。

---

## 七、若仍无效

- 收集：**Dashboard → Debug / Logs** 或与 **`openclaw logs`** 中与 **cron、agent、400** 相关的片段（脱敏后）。  
- 确认：**ClawdBot Gateway 与 Homebrew `openclaw` CLI 版本**是否混用导致行为不一致（见 `docs/openclawwateryu1.md` §一）。  
- **降级策略**：OpenClaw 只做 **每日提醒**；迭代开发 **100% 在 Cursor** 按 `tasks/openclaw_handoff.md` 执行，不再依赖 Cron 改代码。

---

## 八、DeepSeek 为主：官方充值与模型主备（其余仅备份）

**官方链接（DeepSeek API 开放平台，与 [API FAQ](https://api-docs.deepseek.com/faq/) 一致）**：

| 用途 | 链接 |
|------|------|
| **在线充值（Top Up）** | [https://platform.deepseek.com/top_up](https://platform.deepseek.com/top_up) |
| 账单 / 流水（Billing） | [https://platform.deepseek.com/transactions](https://platform.deepseek.com/transactions) |
| 用量导出（Usage） | [https://platform.deepseek.com/usage](https://platform.deepseek.com/usage) |

充值支持 PayPal、银行卡、支付宝、微信等；余额**不过期**（FAQ 说明）。API Key 在平台内创建后，写入本机 **`~/.openclaw/.env`** 的 `DEEPSEEK_API_KEY`，且若 LaunchAgent 注入了该变量需一并更新，再 **`launchctl kickstart -k gui/$(id -u)/ai.openclaw.gateway`**（label 以本机为准）。

**OpenClaw CLI：主模型 DeepSeek，其余仅作 fallback 顺序**（示例；可按你本机已开通的模型增删）：

```bash
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# 主模型：对话用 deepseek-chat（编码任务可改用 deepseek/deepseek-coder）
openclaw models set deepseek/deepseek-chat

# 清空后按优先级添加备份（先写的先尝试）
openclaw models fallbacks clear
openclaw models fallbacks add dashscope/qwen-plus
openclaw models fallbacks add openai/gpt-4o-mini

openclaw models status --json
```

**定时任务单独指定模型**（与全局默认一致，避免 Cron 走别的默认）：

```bash
openclaw cron edit 09a23adf-7b0b-45b3-ba1a-6e601b08f6f2 --model deepseek/deepseek-chat
```

逻辑约定：**优先 DeepSeek**；仅当 DeepSeek 报错（欠费、限流等）时再按 fallback 列表尝试通义 / OpenAI，保证主备一致、可预期。

---

*与 `docs/OPENCLAW_DSML_HEARTBEAT_STUCK.md`、`docs/OPENCLAW_ORCHESTRATION.md` 互补。*
