# 让本机 OpenClaw 正常运转（编程 / 分析 newhigh）

## 0. 本机约定：全局 Agent Skills（非 newhigh 项目内）

**`npx skills add addyosmani/agent-skills --global` 后的实际布局：**

| 用途 | 路径 |
|------|------|
| 技能实体（权威） | `~/.agents/skills/<skill-name>/` |
| OpenClaw 加载 | `~/.openclaw/skills/<skill-name>/`（指向 `~/.agents/skills/…` 的符号链接） |
| 你自建的技能（可选） | `~/.openclaw/workspace/skills/`（与 addyosmani 并存） |

**安装 [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills)（推荐一键）：**

```bash
cd /Users/apple/Ahope/newhigh
bash scripts/install_openclaw_addyosmani_skills.sh
```

或手动（需可用 `npx`，且 **PATH 优先 Homebrew Node**，避免 `~/.local/bin/npx` 指向已删的 node）：

```bash
mkdir -p ~/.openclaw/workspace
cd ~/.openclaw/workspace
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
npx --yes skills add addyosmani/agent-skills --yes --global
```

**`npx` 克隆超时**时，可仅用 git：`OPENCLAW_SKILLS_USE_GIT_ONLY=1 bash scripts/install_openclaw_addyosmani_skills.sh`

装完后请 **完整重启 OpenClaw**（见下文 §1.1）。Cursor：**本机全局**规则 `~/.cursor/rules/openclaw-global-agent-skills.mdc`（`alwaysApply: true`）；本仓库内另见 `.cursor/rules/openclaw-global-skills.mdc`。

---

## 当前情况简要

- **Gateway**：127.0.0.1:18789 已跑、Health OK。
- **配置**：已改为**百炼（dashscope）** + 飞书/机器人关闭；API Key 已写在 `~/.openclaw/openclaw.json`。
- **问题**：旧会话仍绑定 **qianfan**（deepseek-v3.2），会报 `401 invalid_iam_token`，且无法用百炼。

---

## 1. 让 OpenClaw 用上百炼并正常回话

### 1.1 重启 OpenClaw（必做一次）

改完 `~/.openclaw/openclaw.json` 后，需要**完整重启**一次，新会话才会用百炼：

- **若用桌面 App**：完全退出 OpenClaw 再重新打开。
- **若用 CLI**：在终端里停掉正在跑的 `openclaw` 进程，再执行一次 `openclaw` 启动网关/服务。

### 1.2 开新会话，不要用旧会话

- 在 Chat 页点 **「New」或「/new」**（或新开一个 Chat session）。
- **不要**在原来那个显示 “agent:main:main” 且卡在 “A...” 的会话里继续问。
- 新会话会按当前配置使用 **dashscope/qwen-plus（百炼）**，回复才会正常。

### 1.3 确认模型

- 在 **Settings → Config** 里确认 `models.providers` 有 **dashscope**，且 `agents.defaults.model.primary` 为 **dashscope/qwen-plus**。
- 若界面上能选模型，选「百炼」或「通义千问 Plus（百炼）」即可。

---

## 2. 让 Agent 能读「ahope/newhigh」下的 .md

- 项目路径在本机是：**`/Users/apple/Ahope/newhigh`**（你提到的「ahope/newhigh」即此目录）。
- 已在配置里打开**可读工作区外路径**：`tools.fs.workspaceOnly: false`，agent 可以读任意绝对路径。
- 在**新会话**里提问时，建议**直接写绝对路径**，例如：
  - “请读并总结 `/Users/apple/Ahope/newhigh/docs` 下所有 .md 文件”
  - “检查 `/Users/apple/Ahope/newhigh` 目录下的各种 .md，掌握这个证券量化管理平台的情况，提出改进建议”

这样 agent 会用百炼并正常访问 newhigh 的文档。

---

## 3. 若仍无回复或报错

1. **看 Debug / Logs**：Settings → Debug 或 Logs，看是否有 4xx/5xx 或 model/dashscope 相关报错。
2. **确认 API Key**：Settings → Config → `models.providers.dashscope.apiKey` 是否为你的百炼专属 Key（sk-sp-...）。
3. **再重启 + 新会话**：再完整退一次 OpenClaw、重新打开、再 New 一个 Chat 试一次。

### 3.1 「All models failed」：超时 + 上下文不足

若报错类似：`dashscope/deepseek: LLM request timed out` 且 `volcengine/doubao-pro-4k`、`moonshot/moonshot-v1-8k` 报 **Model context window too small (4000/8000 tokens). Minimum is 16000**：

- **原因**：主模型与通义/DeepSeek 超时后，后备链里豆包 4K、Kimi 8K 的上下文只有 4k/8k，而心跳等任务常需 16k+ tokens，导致全部失败。
- **处理**：已提供脚本，将 fallbacks 改为仅大上下文模型（≥32k），避免轮到 4k/8k 时必败：
  ```bash
  python scripts/fix_openclaw_fallbacks.py
  ./scripts/restart_newhigh_bot.sh
  ```
- **超时**：OpenClaw 当前对 LLM 请求的超时可能偏短，若通义/DeepSeek 经常 timeout，可关注上游 [openclaw#46049](https://github.com/openclaw/openclaw/issues/46049) 是否支持配置 `requestTimeout`。

---

## 4. 本机 Gateway 由 LaunchAgent 管理

- **服务**：`ai.openclaw.gateway`（LaunchAgent）
- **plist**：`~/Library/LaunchAgents/ai.openclaw.gateway.plist`
- **环境变量**：`ProgramArguments` 指向 **`~/.openclaw/gateway-launch.sh`**，启动前 `source ~/.openclaw/.env`，使 `openclaw.json` 里 `${DASHSCOPE_API_KEY}` / `${DEEPSEEK_API_KEY}` 等在 Gateway 进程中可用。
- **重载 plist**（改 plist 后）：`launchctl bootout gui/$(id -u)/ai.openclaw.gateway` → `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.openclaw.gateway.plist`
- **启动命令**：`/opt/homebrew/bin/node /Users/apple/ClawdBot/dist/index.js gateway --port 18789`
- **重启**：`launchctl unload ~/Library/LaunchAgents/ai.openclaw.gateway.plist && launchctl load ~/Library/LaunchAgents/ai.openclaw.gateway.plist`
- **注意**：`openclaw.json` 不要加当前版本不认识的键（如 `tools.fs`、`meta.note`），否则会报 Config invalid，Gateway 无法启动。需用 `openclaw doctor --fix` 或手动删除未知键。

## 5. 多模型配置（百炼为主，其余备用）

- **主力**：百炼（dashscope），API Key 直接写在 `openclaw.json` 的 `models.providers.dashscope.apiKey`，确保 LaunchAgent 启动时无需读 .env 即可用。
- **备用链**：`agents.defaults.model.fallbacks` 建议**仅保留上下文 ≥32k 的模型**（如 qwen3.5-plus、qwen3-coder-next、deepseek-chat、deepseek-coder、moonshot-v1-32k、gpt-4o-mini），避免心跳等大上下文任务在 4k/8k 模型上报「Model context window too small」。一键修复：`python scripts/fix_openclaw_fallbacks.py` 后重启 Gateway。
- **备用 Key**：OPENAI、DEEPSEEK、GEMINI 的 Key 写在 `~/.openclaw/.env`，并已注入到 LaunchAgent 的 `EnvironmentVariables`，Gateway 进程能解析 `${OPENAI_API_KEY}` 等。
- **默认模型**：以当前 `openclaw.json` 为准（如 `dashscope/qwen3.5-plus`）。

## 6. 提醒与自主运行（Heartbeat + Cron）

为使 OpenClaw **定时自己干活**、提醒正常运转，已做：

- **Cron 调度**：在 `openclaw.json` 中启用 `cron.enabled: true`，定时任务由 Gateway 管理，任务列表在 **Control → Cron Jobs** 查看/编辑。
- **Heartbeat（心跳）**：`agents.defaults.heartbeat` 已设为每 **1 小时**（`every: "1h"`），目标 `target: "last"`（发到你最后用的 Chat）。Agent 会按点读取工作区里的 **HEARTBEAT.md**，有需要提醒的就发一条，没有就回 HEARTBEAT_OK（不刷屏）。
- **HEARTBEAT.md**：已在 `~/.openclaw/workspace/HEARTBEAT.md` 放了一份简短清单（可选扫一眼 newhigh 项目、按用户交代的定期任务汇报）。你可随时编辑该文件，或对 Agent 说「更新 HEARTBEAT.md，加入每周检查 xxx」，Agent 会按你的要求改。

**如何加定时任务（Cron）**：

- 在 Dashboard 打开 **Control → Cron Jobs**，在界面里添加；或
- 终端执行（需本机已装 `openclaw` CLI 且能连上本机 Gateway）：
  ```bash
  OPENCLAW_HOME=~ openclaw cron add --name "每日项目摘要" --cron "0 9 * * *" --tz "Asia/Shanghai" --session isolated --message "阅读 /Users/apple/Ahope/newhigh 的 README 与 docs 下主要 .md，用 1–2 句话总结状态与可改进点。" --announce --channel webchat --to "last"
  ```
  若没有 `--channel webchat` 可先试 `target: last` 或不加 delivery，按你实际通道调整。

**若心跳/提醒没反应**：到 **Settings → Debug / Logs** 看是否有 `heartbeat skipped`、`cron: scheduler disabled` 等；确认 `cron.enabled` 与 `heartbeat.every` 未被覆盖为 false/0m。

## 7. 配置与路径速查

| 项目 | 值 |
|------|-----|
| 配置文件 | `~/.openclaw/openclaw.json` |
| 环境变量/密钥 | `~/.openclaw/.env` |
| 默认模型 | dashscope/qwen-max（百炼） |
| 工作区 | `~/.openclaw/workspace` |
| 心跳清单 | `~/.openclaw/workspace/HEARTBEAT.md` |
| Cron 任务存储 | `~/.openclaw/cron/jobs.json`（由 Gateway 管理，勿手改） |
| newhigh 项目路径 | `/Users/apple/Ahope/newhigh`（提问时用绝对路径） |

按上述步骤：**重启 OpenClaw → 新开会话 → 用绝对路径问 newhigh 的 .md**；配合 **Heartbeat 每小时 + Cron 定时任务**，即可让 OpenClaw 正常运转并自主提醒、干活。

## 8. `brew update` 报清华镜像 403

若出现 `mirrors.tuna.tsinghua.edu.cn/... returned error: 403`，说明当前 Homebrew 的 `origin` 仍指向清华且镜像侧拒绝；可**临时改回 GitHub 官方**再更新：

```bash
git -C "$(brew --repo)" remote -v
git -C "$(brew --repo)" remote set-url origin https://github.com/Homebrew/brew.git
git -C "$(brew --repo homebrew/core)" remote set-url origin https://github.com/Homebrew/homebrew-core.git 2>/dev/null || true
brew update
```

之后如需再切镜像，以 Homebrew 文档当前推荐方式为准（勿沿用已失效的 tuna git 地址）。
