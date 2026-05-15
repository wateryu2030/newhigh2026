# OpenClaw 定时任务：从「只跑采集」到「红山量化自主迭代」

## 1. 截图里这类结果为什么「不够」

| 现象 | 说明 |
|------|------|
| 只执行 **新闻/政策采集** | 属于**数据管道**中的一环，**不等于**完成 Gateway / 前端 / 策略 / 回测 等平台开发。 |
| 命令 `python3 scripts/news_collector.py` | **主仓根目录没有** `scripts/news_collector.py`（实现位于 `integrations/hongshan/policy-news/news_collector.py`，且须通过包装脚本走 `.venv`）。该命令会失败或误用系统 Python。 |
| `exec` 后台跑一条 shell | 只能做**无人值守脚本**；**完整「自我迭代开发」**需要 Agent 按文档 **读计划 → 改代码 → 跑测试 → 写日志**，单靠一条定时命令无法替代。 |

结论：**定时任务应区分两类**——(A) 运维采集；(B) 提醒 Agent 进入「编排迭代」，而不是指望一条 `python3 ...` 完成全平台开发。

---

## 2. 政策采集（若定时里仍需保留）

**正确入口（唯一）**：

```bash
cd /Users/apple/Ahope/newhigh && /bin/bash scripts/run_policy_news_collect_retry.sh
```

不要用：`python3 scripts/news_collector.py`（路径不存在）、不要用 `/usr/bin/python3` 直跑 `news_collector.py`。

详见：`docs/OPENCLAW_CRON_POLICY_COLLECTOR.md`、`docs/HEARTBEAT.md`。

---

## 3. 自主迭代「红山量化平台」——定时任务里该写什么

平台开发迭代依赖 **HEARTBEAT 循环**（选 1 条 P0/P1 → 读代码 → 实现 → pytest → `evolution/improvement_log_*.md`），见：

- `docs/openclaw/HEARTBEAT_AUTONOMOUS.md`（§B 单次迭代循环）  
- `docs/OPENCLAW_ORCHESTRATION.md`（任务选取与验证）

在 OpenClaw **Scheduled Tasks / 定时任务** 的**文案**里，建议用下面**整段**作为触发内容（让模型按流程工作，而不是只 exec 采集脚本）：

```
【红山量化 · 自主迭代一轮】
仓库根：/Users/apple/Ahope/newhigh（唯一主仓，勿用 ~/.openclaw/workspace 代替）。

本轮目标：完成平台开发闭环的一条最小可验证项，不是只做外网采集。
严格按 docs/openclaw/HEARTBEAT_AUTONOMOUS.md 的 B1→B6：
1）阅读 docs/OPENCLAW_ORCHESTRATION.md 与 docs/OPENCLAW_IMPROVEMENT_PLAN.md（或 tasks/backlog.md），只选 1 条当前阶段 P0/P1；
2）改代码、跑对应 pytest 或 npm run build:clean；
3）在 evolution/improvement_log_当日.md 写一行摘要。

禁止：在同一条回复里重复废话；禁止执行不存在的 python3 scripts/news_collector.py。
若本轮仅需政策入库：只允许 bash /Users/apple/Ahope/newhigh/scripts/run_policy_news_collect_retry.sh。
```

说明：**定时任务**更适合作为「**提醒 + 上述指令**」推给会话；是否真能改代码取决于 OpenClaw 是否对该会话**开启写文件 / 执行仓库命令**权限。若无，则仍需人在 Cursor 里落地提交。

---

## 4. 与「只靠定时 exec」的分工

| 方式 | 适合 |
|------|------|
| `run_policy_news_collect_retry.sh`（cron/launchd） | 每日政策数据入库，**无需**大模型参与。 |
| OpenClaw 定时 **消息** + Agent 遵循 HEARTBEAT | 提醒模型做 **迭代计划内的一条开发任务**（需工具链允许）。 |
| Cursor / 本地开发 | **实际合入代码、跑全量测试**的最终执行面。 |

---

## 5. 同步 HEARTBEAT 到本机 OpenClaw

```bash
bash /Users/apple/Ahope/newhigh/scripts/sync_openclaw_heartbeat.sh
```

使 `~/.openclaw/workspace/HEARTBEAT.md` 与仓库 `docs/openclaw/HEARTBEAT_AUTONOMOUS.md` 一致。

---

*与 `docs/OPENCLAW_AUTONOMOUS_PROMPTS.md`、`docs/OPENCLAW_CRON_POLICY_COLLECTOR.md` 互补。*
