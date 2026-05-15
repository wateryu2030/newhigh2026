# OpenClaw 提示「定时任务 / news_collector」时的纠正说明

部分 Agent 会给出**通用占位路径**（如 `~/.openclaw/workspace/scripts/news_collector.py`、`/usr/bin/python3 ...`）。在 **newhigh 主仓** 中请以本文为准，避免定时任务指向不存在文件或用系统 Python 缺依赖执行。

---

## 1. 权威入口（唯一）

| 用途 | 路径 |
|------|------|
| **日常/定时应调用的包装脚本** | `<repo>/scripts/run_policy_news_collect_retry.sh`（DNS 探活 + 重试，**推荐**） |
| 不重试时 | `<repo>/scripts/run_policy_news_collect.sh` |
| **实际 Python 采集实现** | `<repo>/integrations/hongshan/policy-news/news_collector.py`（勿用系统 Python 直接跑） |

包装脚本会：`cd` 仓库根、`source .env`、设置 `PYTHONPATH`、使用 **`.venv/bin/python`** 调用 `news_collector.py`。详见 `docs/HEARTBEAT.md` §一、§四。

---

## 2. 不推荐的做法

| 误区 | 原因 |
|------|------|
| `~/.openclaw/workspace/scripts/news_collector.py` | OpenClaw 工作区**不一定**含该文件或与主仓**版本不一致**；政策采集以主仓 `integrations/hongshan/policy-news/` 为准 |
| `cd ~/.openclaw/workspace && python3 scripts/news_collector.py` | 同上 + 可能未加载 `.venv` / `.env` |
| `/usr/bin/python3 .../news_collector.py` | 系统 Python 通常**没有**项目依赖；`docs/HEARTBEAT.md` 已明确禁止 |
| 与 Cursor 项目 `diff -r ~/.openclaw/workspace ./newhigh` | 两套目录**不必**文件级完全一致；以 **git 主仓** 为唯一源码真源，OpenClaw 侧只同步 HEARTBEAT 等文档（`scripts/sync_openclaw_heartbeat.sh`） |

---

## 3. 本机一键自检

在仓库根执行：

```bash
chmod +x scripts/policy_collect_env_check.sh
bash scripts/policy_collect_env_check.sh
```

将打印：`.venv`、脚本是否存在、**推荐的 crontab 示例行**、launchd plist 路径说明。

---

## 4. 定时任务怎么配

- **macOS 推荐**：`launchd` + `integrations/hongshan/policy-news/com.newhigh.policy-collector.plist.example`（把 `REPLACE_WITH_NEWHIGH_ROOT` 换成你的主仓绝对路径）。说明见 `docs/HEARTBEAT.md` §三、§「示例 plist」。
- **crontab**：使用 **bash 包装脚本** 整行，例如（路径换成你的机器）：

```cron
30 8 * * * cd /Users/apple/Ahope/newhigh && /bin/bash scripts/run_policy_news_collect_retry.sh >> logs/policy_cron.log 2>&1
```

日志亦可使用 `logs/policy-collector.launchd.out.log`（若用 plist 内路径）。

---

## 5. DuckDB 写入失败（Conflicting lock / 文件正被其他进程占用）

`quant_system.duckdb` **同一时刻只允许一个进程以写模式打开**（或持锁）。若 **Gateway**、**调度脚本**、**政策采集**、其它终端里的 `python` 同时访问，会出现：

`Could not set lock on file ... Conflicting lock is held ...`

**处理**：

1. 试采前短暂停 Gateway：`bash scripts/restart_gateway_frontend.sh` 前先手动停占用库的进程，或先 `kill` 日志里提示的 PID（确认不是关键任务）。  
2. **08:30 定时采集**尽量与低峰一致；若仍冲突，可把采集改到 Gateway 不常驻的时段，或接受「偶发 0 写入 + 飞书仍成功」的提示。  
3. 不要用「另拷一份 DuckDB」双写，除非你有明确迁移方案。

---

## 6. OpenClaw Agent 建议提示词（可贴进会话）

> 政策采集请以 newhigh 主仓库为准：只调用 `<repo>/scripts/run_policy_news_collect_retry.sh`，不要假设 `~/.openclaw/workspace/scripts/news_collector.py`。若无法执行 shell，请让用户运行 `bash scripts/policy_collect_env_check.sh` 并把输出贴回。

---

*与 `docs/HEARTBEAT.md`、`integrations/hongshan/policy-news/README.md` 一致；冲突时以主仓脚本与 HEARTBEAT 为准。更全的自主迭代提示词见 `docs/OPENCLAW_AUTONOMOUS_PROMPTS.md`。*
