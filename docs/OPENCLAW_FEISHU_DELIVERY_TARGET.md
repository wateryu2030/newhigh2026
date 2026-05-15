# OpenClaw：`Delivering to Feishu requires target` 排障

## 含义

OpenClaw 在执行 **Cron / 自主迭代 / announce** 时，若配置了 **向飞书（Feishu）通道投递**，但未提供 **投递目标**（用户 `open_id`、会话 `last`、或 WebChat 等），Gateway 会报错：

**`Delivering to Feishu requires target`**

任务本体（读 HEARTBEAT、跑 B1–B6 提示）**可能已执行**，但**最后一步「通知」失败**，界面会显示整次任务失败。

---

## 处理思路（三选一即可）

### 1）改 Cron / 定时任务：不用飞书，改发到当前 Web 聊天

在 OpenClaw **Control → Scheduled Tasks / Cron Jobs** 里编辑对应任务：

- 将投递通道从 **feishu** 改为 **webchat**（或界面等价选项），并设置 **`to: last`** / **发到上次会话**（与 `docs/OPENCLAW_运行说明.md` §6 示例一致）。

CLI 示例（以你本机 `openclaw cron` 子命令为准）：

```bash
# 关键：--channel webchat --to last，避免无 target 的 feishu
openclaw cron add ... --announce --channel webchat --to "last"
```

### 2）坚持用飞书：在 OpenClaw 里配好飞书与默认目标

- 打开 **`~/.openclaw/openclaw.json`**（及官方文档中的 **channels / plugins → feishu** 说明），为飞书通道配置：
  - 应用 **App ID / Secret**（或机器人 webhook，视版本而定）
  - **默认接收方**：用户 `open_id` 或群，使 **`openclaw message send --channel feishu`** 不必每次缺 `--target`

- 本机历史说明见 **`personal_assistant/FEISHU_SETUP.md`**、`docs/openclawwateryu1.md`（其中曾记录 **feishu: enabled: false**，若一直关闭飞书却仍选 Feishu 投递，也会出问题）。

### 3）关闭该任务的「对外播报」

若不需要每次迭代都推送：

- 在 Cron 配置里关闭 **Announce / 飞书通知**（仅保留会话内执行或日志）。

---

## 与政策采集脚本的关系（另一路）

仓库内 **`integrations/hongshan/policy-news/news_collector.py`** 使用：

```bash
openclaw message send --channel feishu --target "user:${FEISHU_TARGET}" ...
```

其中 **`FEISHU_TARGET`** 来自环境变量 **`FEISHU_POLICY_NOTIFY_OPEN_ID`**（见脚本内注释）。若未设置且默认值无效，也可能导致飞书发送失败，但报错文案可能不同；请在 **`.env`** 中设置：

```bash
FEISHU_POLICY_NOTIFY_OPEN_ID=你的飞书用户_open_id
```

---

## 验证

1. 修改 Cron 后**重启 OpenClaw Gateway**，等待下一次触发，或手动 **Run once**。  
2. **Settings → Debug / Logs** 中确认不再出现 `requires target`。  
3. 自主迭代若以 **Cursor 改主仓** 为主，即使飞书失败，仍可到 **`/Users/apple/Ahope/newhigh`** 执行 `git status` / 看 `evolution/` 是否有记录。

---

*与 `docs/OPENCLAW_运行说明.md` §6、`docs/OPENCLAW_ORCHESTRATION.md` 互补。*
