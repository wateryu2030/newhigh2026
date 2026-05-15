# OpenClaw 自主迭代 — 可复制提示词（newhigh 主仓）

给 OpenClaw / Cursor Agent **整段粘贴**，减少幻觉路径（`~/.openclaw/workspace/...`）、错误 Python、以及前端 `.next` 半残状态。

**每次长任务前仍应先读**：`docs/OPENCLAW_ORCHESTRATION.md` → `docs/openclaw/HEARTBEAT_AUTONOMOUS.md`。

---

## 1. 总约束（必带）

```
你在 newhigh  monorepo 中工作，仓库根为唯一源码真源（不要用 ~/.openclaw/workspace 下的脚本路径代替主仓）。
禁止：/usr/bin/python3 直接跑业务脚本（须用 .venv + scripts/*.sh）。
禁止：臆造不存在的文件路径；不确定时用 grep 或读仓库。
改侧栏/小程序菜单：只编辑 config/navigation_manifest.json，然后 make sync-nav。
政策采集：只调用 <repo>/scripts/run_policy_news_collect_retry.sh（见 docs/OPENCLAW_CRON_POLICY_COLLECTOR.md）。
```

把 `<repo>` 换成实际路径，例如 `/Users/apple/Ahope/newhigh`。

---

## 2. 前端 Next.js：构建失败 / pages-manifest ENOENT / rm .next 失败

```
症状：ENOENT .../.next/server/pages-manifest.json，或 rm -rf .next 报 Directory not empty（standalone 嵌套 node_modules）。
处理：
1) cd <repo>/frontend && npm run build:clean
   （内部用 bash scripts/clean-next.sh 再 next build，会先 chmod -R u+w 再删）
2) 开发：不要用「只手写 .next/server/middleware-manifest.json」代替完整构建；需要干净 dev 时用 npm run dev:clean，或从仓库根 bash scripts/restart_gateway_frontend.sh（会删 .next 并写占位 manifest 再 next dev）。
3) EADDRINUSE :3000：说明已有 next dev；先 lsof -i :3000 或再跑 restart_gateway_frontend.sh，不要叠两个 npm run dev。
PATH：优先 /opt/homebrew/bin 的 node/npm。
```

---

## 3. Gateway + 前端一键重启

```
从仓库根执行：bash scripts/restart_gateway_frontend.sh
勿在 frontend/ 子目录里 bash scripts/restart_gateway_frontend.sh（相对路径不存在）。
日志：logs/gateway.out、logs/frontend.out。
```

---

## 4. DuckDB 锁（政策采集 / Gateway 同时开）

```
若政策采集报 quant_system.duckdb Conflicting lock：说明 Gateway 或其它 python 正占用库。
迭代策略：文档说明冲突原因；可选建议用户短时停 Gateway 再采，或接受定时任务在低峰重试；不要建议复制整库双写除非有迁移设计。
详见 docs/OPENCLAW_CRON_POLICY_COLLECTOR.md §5。
```

---

## 5. Heartbeat 与 OpenClaw 工作区同步

```
本机 OpenClaw 读 ~/.openclaw/workspace/HEARTBEAT.md 时，应与仓库 docs/openclaw/HEARTBEAT_AUTONOMOUS.md 一致：
bash scripts/sync_openclaw_heartbeat.sh
导航/编排：docs/OPENCLAW_ORCHESTRATION.md §4.5。
```

---

## 6. 单轮「修一类问题」模板

```
本轮只解决：<具体问题>。
涉及路径：<列 1–3 个文件>。
验证：<一条 pytest 或 npm run build:clean 或 curl health>。
不改无关文件；完成后在 evolution/improvement_log_当日.md 写一行摘要。
```

---

## 7. 聊天里同一段话重复多遍（复读）— 是否正常？怎么修？

**算问题。** 常见原因：

| 原因 | 说明 |
|------|------|
| **单次粘贴过长** | 把整段「总约束 + 多节提示词」每条消息都贴一遍，上下文膨胀，模型容易在「确认理解」上打转。 |
| **模型行为** | 无可用工具时，部分模型会反复输出开场白而不进入下一步。 |
| **会话过长** | 历史轮次太多，摘要异常时出现重复片段（界面看起来像连发同一句）。 |

**修正（按顺序试）**：

1. **开新会话**，本条消息只带 **§6 单轮模板** + 一句路径，不要重复贴 §1–§5 全文。  
2. 在首条或复读出现后追加 **防复读约束**（整段粘贴）：

```
仓库根已固定为 /Users/apple/Ahope/newhigh，无需再说明。禁止在同一条回复里重复同一段话；禁止连续多轮只复述约束。每轮：一句以内确认 + 直接执行具体命令/改文件/给结果。
```

3. **OpenClaw 侧**：检查 **定时任务 / Scheduled Tasks** 是否在短时间内多次注入同一段系统提示（若有，拉长间隔或关掉重复任务）。  
4. **换模型或降温度**（若客户端提供）：部分模型在长 system 下更易复读。  
5. 把长期约束放到 **本机 Skills / 工作区规则**（只加载一次），聊天里只发**当前任务一句**。

---

## 8. 本机路径已写死的短提示词（推荐日常用）

避免每次贴超长 §1–§5；仅在新会话或模型跑偏时用：

```
工作目录：/Users/apple/Ahope/newhigh。详规见该仓库 docs/OPENCLAW_AUTONOMOUS_PROMPTS.md，不要复读文档内容。
当前任务：<一句话描述你要它做的事>
```

---

*与 `docs/CURSOR_OPENCLAW_AGENT_PROMPTS.md` 互补：彼处偏任务模板，此处偏环境纠偏与路径。*
