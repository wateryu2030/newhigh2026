# 本机 OpenClaw 设置情况（wateryu）

> 文档生成时间：2026-03-11  
> 用途：记录当前 Mac 上 OpenClaw 的安装、配置、服务与工作区状态，便于复查与迁移。

---

## 一、安装与版本

| 项目 | 值 |
|------|-----|
| **CLI 路径** | `/opt/homebrew/bin/openclaw` |
| **CLI 来源** | Homebrew（node 包 `openclaw`） |
| **npm 包版本** | 2026.2.19-2（`/opt/homebrew/lib/node_modules/openclaw`） |
| **桌面应用** | `/Applications/OpenClaw.app`（存在） |
| **Gateway 实际进程** | 由 **ClawdBot** 提供：`/Users/apple/ClawdBot/dist/index.js gateway --port 18789` |
| **Gateway 服务版本** | 2026.1.29（LaunchAgent 注释） |

说明：Web 控制台与 Gateway 功能由 ClawdBot 进程提供；CLI 与配置由 Homebrew 安装的 openclaw 包读取。

---

## 二、Gateway 服务

| 项目 | 值 |
|------|-----|
| **服务类型** | LaunchAgent |
| **Label** | `ai.openclaw.gateway` |
| **Plist 路径** | `~/Library/LaunchAgents/ai.openclaw.gateway.plist` |
| **监听地址** | 127.0.0.1:18789（仅本机） |
| **认证** | token，值：`dev-local-token` |
| **Dashboard** | http://127.0.0.1:18789/ |
| **当前状态** | 运行中（Runtime: running, RPC probe: ok） |
| **标准输出** | `~/.openclaw/logs/gateway.log` |
| **标准错误** | `~/.openclaw/logs/gateway.err.log` |

**Plist 中注入的环境变量（键名）**：  
`HOME`, `OPENCLAW_HOME`, `PATH`, `OPENCLAW_GATEWAY_PORT`, `OPENCLAW_GATEWAY_TOKEN`, `OPENCLAW_LAUNCHD_LABEL`, `OPENCLAW_SYSTEMD_UNIT`, `OPENCLAW_SERVICE_MARKER`, `OPENCLAW_SERVICE_KIND`, `OPENCLAW_SERVICE_VERSION`, `DASHSCOPE_API_KEY`, `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, `GEMINI_API_KEY`  
（API Key 等敏感值仅保存在 plist 与 `.env` 中，此处不写出具体值。）

**建议**：若需修复 PATH 或服务配置，可执行 `openclaw doctor --repair`。

---

## 三、主配置文件（openclaw.json）

路径：`~/.openclaw/openclaw.json`。

### 3.1 模型（models）

- **mode**：merge  
- **providers**：  
  - **openai**：baseUrl `https://api.openai.com/v1`，apiKey 来自环境变量 `OPENAI_API_KEY`，模型 `gpt-4o-mini`。  
  - **deepseek**：baseUrl `https://api.deepseek.com`，apiKey 来自 `DEEPSEEK_API_KEY`，模型 `deepseek-chat`。  
  - **dashscope**：baseUrl `https://dashscope.aliyuncs.com/compatible-mode/v1`，apiKey 已直接写在配置中（百炼），模型 `qwen-max`、`qwen-plus`、`qwen-turbo`。

### 3.2 默认 Agent（agents.defaults）

- **主模型**：`dashscope/qwen-max`（百炼 Max）  
- **备用链**：`dashscope/qwen-plus` → `openai/gpt-4o-mini` → `deepseek/deepseek-chat`  
- **工作区**：`/Users/apple/.openclaw/workspace`  
- **心跳（heartbeat）**：  
  - 间隔：`1h`  
  - 目标：`last`（发到最后使用的会话）  
  - 提示：读取 HEARTBEAT.md 并严格遵循，无事则回复 HEARTBEAT_OK  
- **compaction**：safeguard  
- **maxConcurrent**：4；**subagents.maxConcurrent**：8  

### 3.3 通道（channels）

- **feishu**：enabled: false（已关闭）  

### 3.4 定时任务（cron）

- **enabled**：true  
- **store**：`~/.openclaw/cron/jobs.json`  

### 3.5 网关（gateway）

- **port**：18789  
- **mode**：local  
- **bind**：loopback  
- **auth**：mode token，token 见上  
- **tailscale**：mode off  

### 3.6 插件（plugins）

- **feishu**：enabled: false  

### 3.7 其他

- **commands**：native auto, nativeSkills auto, restart true  
- **messages.ackReactionScope**：group-mentions  
- **meta.lastTouchedVersion**：2026.2.19-2  

---

## 四、环境变量（.env）

路径：`~/.openclaw/.env`。

已配置的**变量名**（具体值不在此列出）：  
`OPENAI_API_KEY`, `OPENAI_MODEL`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL`, `DASHSCOPE_API_KEY`, `BAILIAN_API_KEY`, `TUSHARE_TOKEN`, `OPENROUTER_API_KEY`。

说明：LaunchAgent 不自动加载 .env，故 API Key 已同时写入 plist 的 EnvironmentVariables，供 Gateway 进程使用。

---

## 五、工作区（workspace）

路径：`/Users/apple/.openclaw/workspace`。

| 项目 | 说明 |
|------|------|
| **HEARTBEAT.md** | 存在；内容为「每日量化平台自我进化任务」清单（读 newhigh、改进计划、实施与学习、输出到 evolution/） |
| **SOUL.md** | 存在；含通用原则与「量化平台自我改进原则」 |
| **newhigh** | 符号链接，指向 `/Users/apple/Ahope/newhigh`（本机量化项目） |
| **evolution/** | 目录存在，用于存放 improvement_plan.md、improvement_log.md、LEARNINGS.md、ERRORS.md |

Agent 可通过工作区内 `./newhigh` 或绝对路径 `/Users/apple/Ahope/newhigh` 访问量化项目。

---

## 六、Cron 任务列表

存储文件：`~/.openclaw/cron/jobs.json`。

| 名称 | 启用 | 调度 | 会话 | 说明 |
|------|------|------|------|------|
| 霍尔木兹海峡进展自动汇总 | 否 | at（一次性） | isolated | 原飞书/群组相关，已关 |
| 外部信息采集 | 是 | 每 21600000 ms（6h） | main | systemEvent：采集新华社、国务院、住建部等外部信息 |
| 新闻摘要生成 | 是 | 每 86400000 ms（24h） | main | systemEvent：生成新闻摘要报告 |
| **每日量化自我进化** | **是** | **每 86400000 ms（24h）** | **isolated** | **执行 HEARTBEAT.md 全套任务，产出写入 workspace/evolution/** |

说明：每日「量化自我进化」已通过直接写入 `jobs.json` 添加；也可在 Dashboard → Control → Cron Jobs 中查看或编辑。详见 [OPENCLAW_SELF_DEV.md](OPENCLAW_SELF_DEV.md)。

---

## 七、Skills 概览

命令：`openclaw skills list`。

- **就绪（ready）**：1password、apple-notes、apple-reminders 等（14/50 ready）。  
- **缺失（missing）**：bear-notes、blogwatcher、blucli、bluebubbles 等（依赖对应 CLI 或环境）。  

与量化项目直接相关的 A 股 Skill 由项目侧 Gateway API（如 `/api/skill/ashare/*`）提供，不在此列表内。

---

## 八、配置备份与日志

- **配置备份**：`~/.openclaw/` 下存在多个 `openclaw.json.bak*` 及 `openclaw.json.before-restore`，便于回滚。  
- **权限**：`.openclaw` 目录已 chmod 700，`openclaw.json` 已 chmod 600（doctor 建议）。  
- **Gateway 日志**：`~/.openclaw/logs/gateway.log`、`gateway.err.log`。  
- **临时日志**：`/tmp/openclaw/openclaw-*.log`。  

---

## 九、已知提示与注意事项

1. **Config warnings**：plugins.entries.feishu 存在 duplicate plugin id 提示，可忽略（飞书已关闭）。  
2. **Service config**：Gateway 服务 PATH 缺少部分用户级 bin 目录，不影响当前使用；可选执行 `openclaw doctor --repair`。  
3. **配置版本**：openclaw.json 由较新版本（2026.2.19-2）写入，当前 Gateway 为 2026.1.29，可能仅出现版本提示，一般不影响运行。  
4. **新会话**：修改模型或配置后，建议在 Chat 中「New session」再使用，避免旧会话仍用旧模型或 401。  

---

## 十、快捷命令

```bash
# 查看 Gateway 状态
openclaw gateway status

# 重启 Gateway（LaunchAgent）
launchctl unload ~/Library/LaunchAgents/ai.openclaw.gateway.plist
launchctl load ~/Library/LaunchAgents/ai.openclaw.gateway.plist

# 打开网页控制台
open "http://127.0.0.1:18789"

# 查看技能列表
openclaw skills list
```

---

*本文档仅描述本机 OpenClaw 设置情况，不包含 API Key、Token 等敏感值。*
