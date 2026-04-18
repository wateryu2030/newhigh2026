# OpenClaw → Cursor 交接（按设计迭代）

> 用途：OpenClaw 侧重**调度与提醒**；**改主仓、跑测试、提交**在 **Cursor** 完成。每次 Cron/心跳后，人类或 Agent 先读本文件再动手。

## 主仓路径

`/Users/apple/Ahope/newhigh`

## 必读顺序

1. `docs/OPENCLAW_ORCHESTRATION.md`
2. `tasks/current_task.md`
3. 小程序对齐：`tasks/MINIPROGRAM_DESKTOP_PARITY.md`（若当前做小程序）
4. 飞书 Cron 报错：`docs/OPENCLAW_FEISHU_DELIVERY_TARGET.md`
5. 重启后仍不达预期 / 预期对齐：`docs/OPENCLAW_REALITY_CHECK_AND_IMPROVEMENTS.md`

## 一键本机准备（仓库根）

```bash
make openclaw-iterate-ready
make openclaw-status
# 或：bash scripts/openclaw_iteration_ready.sh
# 或：bash scripts/openclaw_status.sh
```

## 自动化跑一轮迭代（终端，推荐）

内联 `tasks/current_task.md` 与 `docs/OPENCLAW_ORCHESTRATION.md` §2，**不依赖 read 工具**；默认 **`openclaw agent --local`**，避免与 Web 抢同一会话锁。

```bash
cd /Users/apple/Ahope/newhigh
make openclaw-iteration-once
# 或：bash scripts/openclaw_iteration_prompt_once.sh
```

改用 Gateway（易与 Dashboard 争用会话，仅必要时）：`OPENCLAW_ITERATION_LOCAL=0 bash scripts/openclaw_iteration_prompt_once.sh`

## OpenClaw + Cursor CLI 全自动串联

1. 一次性：`cursor agent login`（或配置 `CURSOR_API_KEY`）。  
2. 仓库根执行：`make openclaw-cursor-iterate` 或 `bash scripts/openclaw_cursor_iterate.sh`。  
3. 流程：**OpenClaw（local）** 写出 `evolution/openclaw_cursor_last_plan.md` → **`cursor agent -p -f`** 按该文件在仓库内落地改动。  

仅生成规划、不自动跑 Cursor：`OPENCLAW_CURSOR_PLAN_ONLY=1 bash scripts/openclaw_cursor_iterate.sh`  

说明与安全选项见 **`docs/OPENCLAW_PLUS_CURSOR_LOOP.md`** §C。

**续跑/接力（E2E + pytest 验收后让 OpenClaw 继续完善）**：复制 **`tasks/openclaw_followup_prompt.md`** 全文到会话。

**良性闭环（推荐，避免 Web 里 DeepSeek + read 复读）**：终端执行 **`bash scripts/openclaw_benign_loop.sh`** 或 **`make openclaw-cursor-iterate`**（OpenClaw local 规划 → `cursor agent` 改仓库）。说明见 **`docs/OPENCLAW_PLUS_CURSOR_LOOP.md`** §四。

## 贴给 OpenClaw 会话的短提示（调度用）

```
主仓 /Users/apple/Ahope/newhigh。默认模型 deepseek/deepseek-chat（若 read 工具反复无输出可切通义 Qwen 或粘贴文件正文）。先读 tasks/current_task.md 与 docs/OPENCLAW_ORCHESTRATION.md §2，只选 1 条可验证 P0/P1；写出目标、文件路径、验证命令。禁止仅 HEARTBEAT_OK。Cron 投递：openclaw cron edit <真实UUID> --channel last --to last --best-effort-deliver（见 docs/OPENCLAW_REALITY_CHECK_AND_IMPROVEMENTS.md §五）。
```

## 迭代开发长提示词（贴 Web 会话，一次完整迭代）

```
你是 newhigh 仓库的迭代助手。主仓：/Users/apple/Ahope/newhigh（与 ~/.openclaw/workspace/newhigh 指向一致）。

【必读】按顺序（每个文件最多读一遍；若复读卡住则换通义或粘贴片段）：
1) tasks/current_task.md
2) docs/OPENCLAW_ORCHESTRATION.md（§2 任务选取）
3) 若涉及小程序：tasks/MINIPROGRAM_DESKTOP_PARITY.md

【约束】只做 1 条最小可验证任务；禁止写入 token/密钥；默认不真实下单；改动保持仓库风格。

【产出】用 Markdown 分节：
1. 所选任务（一句话 + 文档引用）
2. 涉及文件路径
3. 建议改动（若不能写仓库则写成给 Cursor 的步骤清单）
4. 验证命令（仓库根可执行的一行或多行）
5. 风险与回滚（各一句）
6. 需 Cursor 接手项（若有）

禁止空洞总结与仅 HEARTBEAT_OK。
```

## 本轮可编辑区（示例）

（由人或 OpenClaw 填写下一行）

- 本轮目标：
- 涉及路径：
- 验证命令：

---

*与 `docs/OPENCLAW_PLUS_CURSOR_LOOP.md` 一致。*
