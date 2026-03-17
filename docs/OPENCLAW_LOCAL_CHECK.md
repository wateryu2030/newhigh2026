# 本机 OpenClaw 安装与配置检查报告

检查时间：按需运行。以下为最近一次检查结论与已做配置。

---

## 一、是否已安装

| 项目 | 状态 |
|------|------|
| **OpenClaw 本体** | ✅ 已安装 |
| **安装方式** | Homebrew（`/opt/homebrew/bin/openclaw`，Node 脚本） |
| **版本** | 2026.3.7（来自 `brew info openclaw`，Cask 名 OpenClaw） |
| **配置目录** | `~/.openclaw/`（存在且含 openclaw.json、.env、agents、skills、workspace 等） |

---

## 二、基础配置是否完整

### 2.1 本机 OpenClaw 配置（~/.openclaw/）

| 配置项 | 状态 |
|--------|------|
| **主配置** | ✅ `openclaw.json` 存在且有效 |
| **环境变量** | ✅ `.env` 存在，含 `OPENROUTER_API_KEY`、`DASHSCOPE_API_KEY`（百炼） |
| **模型提供方** | ✅ 已配置 `qwen-portal`（OAuth）、**已新增 `dashscope`（百炼 API Key）** |
| **网关** | ✅ gateway.port: 18789，mode: local，auth: token |
| **技能 / 插件** | ✅ skills、plugins、cron 等均有配置 |

### 2.2 百炼（DashScope）配置（已补齐）

- **openclaw.json** 的 `models.providers` 中已增加 **dashscope**：
  - **Coding Plan 套餐**：`baseUrl` 使用 `https://coding.dashscope.aliyuncs.com/v1`，Key 用控制台「套餐专属 API Key」。
  - 兼容模式：`baseUrl` 为 `https://dashscope.aliyuncs.com/compatible-mode/v1`。
  - `apiKey`: 使用环境变量 `DASHSCOPE_API_KEY`（在 `.env` 或 LaunchAgent 中配置）。
  - 模型：`qwen-max`、`qwen-plus`、`qwen-turbo`。
- **~/.openclaw/.env** 中已增加 `DASHSCOPE_API_KEY`，供 Gateway 进程使用。

使用 OpenClaw 时，可在模型选择处选用「通义千问 Plus（百炼）」或「通义千问 Turbo（百炼）」以走百炼 API。

### 2.3 红山量化项目（newhigh）中的 OpenClaw 相关配置

| 配置项 | 状态 |
|--------|------|
| **OPENCLAW_*.yaml** | ✅ 多个控制文件存在（AUTONOMOUS_DEV、AI_DEV_AGENT、ALPHA_FACTORY 等） |
| **项目 .env** | ✅ 含 `BAILIAN_API_KEY`、`DASHSCOPE_API_KEY`、`TUSHARE_TOKEN` |
| **Cursor 规则** | ✅ `.cursor/rules/openclaw-bailian.mdc` 约定使用百炼 Key |
| **启动脚本** | ✅ `scripts/open_openclaw.sh` 存在（需在项目根执行） |

---

## 三、如何再次自检

在终端执行（本机 OpenClaw 是否安装、配置目录是否存在）：

```bash
which openclaw
ls -la ~/.openclaw/openclaw.json ~/.openclaw/.env
```

在项目根目录执行（红山 OpenClaw 脚本与配置）：

```bash
cd /Users/apple/Ahope/newhigh
bash scripts/open_openclaw.sh
```

---

## 四、百炼 Coding Plan 与 VPN

- **Coding Plan**：若订阅的是「Coding Plan」，必须使用 Base URL `https://coding.dashscope.aliyuncs.com/v1` 和该套餐页的「套餐专属 API Key」，否则会 401。
- **VPN**：LaunchAgent 已设置 `NO_PROXY=*.aliyuncs.com,*.alibaba.com`，请求阿里云时不走系统代理，避免 VPN 导致超时或连不上。若仍异常，可尝试关闭 VPN 后重试，或在本机网络设置中对 `*.aliyuncs.com` 做分流。
- **验证 Key**：`bash scripts/test_dashscope_key.sh`（脚本默认使用 Coding Plan 的 Base URL）。

---

## 五、Gateway 无法打开时（required secrets are unavailable）

**现象**：Dashboard 打不开、`openclaw doctor` 报 `Gateway not running`，Last gateway error 为：
```text
Startup failed: required secrets are unavailable.
SecretRefResolutionError: Environment variable "VOLCENGINE_API_KEY" is missing or empty.
```

**原因**：`openclaw.json` 里配置了 `volcengine` / `moonshot` 等 provider，且引用 `${VOLCENGINE_API_KEY}`、`${MOONSHOT_API_KEY}`。LaunchAgent 启动 Gateway 时**不会**自动加载 `~/.openclaw/.env`，导致进程环境中没有这两个变量，Gateway 视为“必需密钥缺失”而拒绝启动。

**修复**：在 LaunchAgent 的 plist 中为这两个变量注入占位值（无需真实 Key，仅用于通过启动校验）：

```bash
# 注入环境变量（若键已存在可改用 Set）
/usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:VOLCENGINE_API_KEY string 'optional'" ~/Library/LaunchAgents/ai.openclaw.gateway.plist 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:VOLCENGINE_API_KEY 'optional'" ~/Library/LaunchAgents/ai.openclaw.gateway.plist
/usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:MOONSHOT_API_KEY string 'optional'" ~/Library/LaunchAgents/ai.openclaw.gateway.plist 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:MOONSHOT_API_KEY 'optional'" ~/Library/LaunchAgents/ai.openclaw.gateway.plist

# 重启 Gateway
launchctl bootout gui/$(id -u)/ai.openclaw.gateway
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.openclaw.gateway.plist
```

完成后 `http://127.0.0.1:18789/` 应返回 200，Dashboard 可正常打开。

---

## 六、小结

- **本机已安装 OpenClaw**，配置目录与主配置完整。
- **百炼**：已按 Coding Plan 配置 `coding.dashscope.aliyuncs.com/v1` 及套餐专属 Key；VPN 环境下通过 NO_PROXY 直连阿里云。
- **红山项目侧**：OPENCLAW 控制文件、项目 .env、Cursor 规则与启动脚本均就绪；在项目根执行 `bash scripts/open_openclaw.sh` 即可加载项目 .env 并检查/启动 Gateway。
- **Gateway 无法启动**：若报 `VOLCENGINE_API_KEY` / `MOONSHOT_API_KEY` 缺失，按第五节在 LaunchAgent 中注入占位值并重启即可。

---

## 七、飞书/机器人报「400 model qwen-plus is not supported」

**现象**：飞书里 newhigh 机器人或 OpenClaw 会话返回 `400 model qwen-plus is not supported`。

**原因**：百炼/Coding Plan 部分套餐或端点已不再支持模型 ID `qwen-plus`，需改用 `qwen-turbo` 或（Coding Plan）`qwen3.5-plus`。

**处理**：

1. **若机器人走 OpenClaw**：  
   编辑 `~/.openclaw/openclaw.json`：
   - 将 `agents.defaults.model.primary` 设为 `dashscope/qwen3.5-plus`（或 `dashscope/qwen-turbo`，视套餐支持而定）。
   - 在 `agents.defaults.model.fallbacks` 中**不要**使用 `dashscope/qwen-plus`，改为 `dashscope/qwen3.5-plus` 或 `dashscope/qwen-turbo`，否则主模型不可用时仍会报 400。  
   保存后**完全退出 OpenClaw 再打开**，或新开一条会话再试。
2. **若走 newhigh 本仓策略**：`strategy-engine` 里 `ai_decision` 已把配置中的 `qwen-plus` 映射为调用 `qwen-turbo`，并带 400 时自动降级，无需改配置。
