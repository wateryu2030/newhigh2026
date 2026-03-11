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
  - `baseUrl`: `https://dashscope.aliyuncs.com/compatible-mode/v1`
  - `apiKey`: 使用你提供的百炼专属 Key（sk-sp-...）
  - 模型：`qwen-plus`（通义千问 Plus）、`qwen-turbo`（通义千问 Turbo）
- **~/.openclaw/.env** 中已增加 `DASHSCOPE_API_KEY=sk-sp-...`，供依赖环境变量的逻辑使用。

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

## 四、小结

- **本机已安装 OpenClaw**，配置目录与主配置完整。
- **百炼 API Key 已接入**：在 `~/.openclaw/openclaw.json` 中增加了 dashscope 提供方，并在 `~/.openclaw/.env` 中设置了 `DASHSCOPE_API_KEY`。
- **红山项目侧**：OPENCLAW 控制文件、项目 .env、Cursor 规则与启动脚本均就绪；在项目根执行 `bash scripts/open_openclaw.sh` 即可加载项目 .env 并检查/启动 Gateway。
