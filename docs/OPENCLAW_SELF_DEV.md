# OpenClaw 自我开发机制说明

本文档说明本机 OpenClaw 如何通过 **Heartbeat** 与 **Cron** 实现「自动读文档、自我迭代开发」的配置与用法。

---

## 一、已完成的配置

| 项目 | 位置 / 说明 |
|------|-------------|
| **HEARTBEAT.md** | `~/.openclaw/workspace/HEARTBEAT.md`：每日量化自我进化任务清单（读 newhigh、写改进计划、实施与学习、输出到 evolution/） |
| **SOUL.md** | `~/.openclaw/workspace/SOUL.md`：含「量化平台自我改进原则」（具体可操作、收益/风险、备份与学习固化） |
| **工作区 newhigh** | 工作区内 `./newhigh` 为符号链接，指向 `/Users/apple/Ahope/newhigh` |
| **evolution/** | `~/.openclaw/workspace/evolution/`：存放 improvement_plan.md、improvement_log.md、LEARNINGS.md、ERRORS.md |
| **Heartbeat** | 每 1 小时执行一次，读取 HEARTBEAT.md，目标 `last`（发到最后使用的 Chat） |
| **Cron「每日量化自我进化」** | 每 24 小时执行一次，isolated 会话，执行 HEARTBEAT.md 中的全套任务 |

---

## 二、Cron 任务详情

- **名称**：每日量化自我进化  
- **ID**：`7f2a9b1c-4d3e-4a5b-8c9d-0e1f2a3b4c5d`  
- **调度**：每 24 小时（every 86400000 ms）  
- **会话**：isolated（独立会话，不占用主会话）  
- **启用**：是  

在 Dashboard **Control → Cron Jobs** 中可查看、启用/禁用或编辑该任务。

---

## 三、如何修改行为

1. **改任务内容**：编辑 `~/.openclaw/workspace/HEARTBEAT.md`，按需增删或细化步骤。  
2. **改原则**：编辑 `~/.openclaw/workspace/SOUL.md` 中的「量化平台自我改进原则」段落。  
3. **改执行频率**：Heartbeat 在 `~/.openclaw/openclaw.json` 的 `agents.defaults.heartbeat.every`（当前 `1h`）；Cron 任务可在 Dashboard → Cron Jobs 中改 schedule，或改 `~/.openclaw/cron/jobs.json`（需先停止 Gateway）。  
4. **改产出路径**：在 HEARTBEAT.md 中约定 evolution/ 下的文件名与路径，与当前一致即可。

---

## 四、相关文档

- **本机设置总览**：[openclawwateryu1.md](openclawwateryu1.md)  
- **运行与排错**：[OPENCLAW_运行说明.md](OPENCLAW_运行说明.md)  
- **A 股 Skill**：[OPENCLAW_SKILLS.md](OPENCLAW_SKILLS.md)  

---

*配置完成后，Gateway 会按 Heartbeat 与 Cron 自动执行；首次 Cron 约在添加后 1 小时内触发，之后每 24 小时执行一次。*
