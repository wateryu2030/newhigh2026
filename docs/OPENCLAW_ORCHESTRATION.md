# OpenClaw 编排说明（按计划完成设计/开发任务）

本文件定义 **OpenClaw 与本仓库的绑定方式**，确保 Agent **先读计划、再执行、失败自愈、可验证**，与 `docs/OPENCLAW_IMPROVEMENT_PLAN.md`、`docs/OPENCLAW_TASK_ENTITY_SECURITIES_ITERATION.md` 一致。

---

## 1. 权威文档阅读顺序（每次长任务前）

| 顺序 | 文档 | 用途 |
|------|------|------|
| ① | **本文** | 编排与同步方式 |
| ② | `docs/OPENCLAW_TASK_ENTITY_SECURITIES_ITERATION.md` | 实体证券 + 自我修复闭环 |
| ③ | `docs/OPENCLAW_IMPROVEMENT_PLAN.md` | 阶段 0–3 任务分解与模块映射 |
| ④ | `OPENCLAW_HONGSHAN_ENTITY_TRADING.yaml` | 机器可读优先级与工作流 |
| ⑤ | `docs/OPENCLAW_QUANT_ECOSYSTEM_AND_SAFETY.md` | 安全与边界 |

可选：`docs/CURSOR_OPENCLAW_TASKS.md`（命令与 API 触发进化）。  
政策采集 / 定时任务若与 OpenClaw 提示冲突：先看 **`docs/OPENCLAW_CRON_POLICY_COLLECTOR.md`**，并运行 `bash scripts/policy_collect_env_check.sh`。  
自主迭代可复制提示词：**`docs/OPENCLAW_AUTONOMOUS_PROMPTS.md`**（Next `.next`、端口、DuckDB 锁、路径约束）。  
OpenClaw **定时任务**若只跑采集、或误用 `scripts/news_collector.py`：**`docs/OPENCLAW_SCHEDULED_TASKS.md`**（开发迭代文案 + 正确采集命令）。  
要让 OpenClaw **真正具备自主开发条件**（工作区、Skills、会话模式、自检清单）：**`docs/OPENCLAW_AUTONOMOUS_DEVELOPMENT_SETUP.md`**。  
若界面总出现 **DSML `read HEARTBEAT.md`**、迭代像没动：**`docs/OPENCLAW_DSML_HEARTBEAT_STUCK.md`**（路径踩坑 + 已加强的 HEARTBEAT 模板）。  
**OpenClaw 只做调度、开发由 Cursor 落地** 的闭环设计：**`docs/OPENCLAW_PLUS_CURSOR_LOOP.md`**（**§四：防 Web 复读 + `make openclaw-benign-loop`**）。  
**小程序与桌面能力对齐（优先迭代）**：**`tasks/MINIPROGRAM_DESKTOP_PARITY.md`**。  
飞书投递报错 **`Delivering to Feishu requires target`**：**`docs/OPENCLAW_FEISHU_DELIVERY_TARGET.md`**。  
**重启后仍感觉未达预期 / 需对齐预期与排查清单**：**`docs/OPENCLAW_REALITY_CHECK_AND_IMPROVEMENTS.md`**（`make openclaw-status`）。

---

## 2. 任务选取规则（自主安排）

1. **P0 优先**：稳定性、测试绿、Gateway/执行层契约、DuckDB 锁与数据路径一致。  
2. **每次只选 1 条可验证主线**（单模块或单 API），完成后再开下一条。  
3. **与「实体证券」相关时**：优先 `execution-engine/brokers/`、`gateway` 交易与持仓相关路由、`OPENCLAW_TASK_ENTITY_SECURITIES_ITERATION.md` 中的 P1。  
4. **产出**：代码变更 + 测试 + `evolution/` 或当日 `improvement_log` 一条记录。

---

## 3. 与 OpenClaw 工作区 HEARTBEAT 的同步

OpenClaw 默认读 **`~/.openclaw/workspace/HEARTBEAT.md`**（见 `docs/OPENCLAW_SELF_DEV.md`）。

仓库内维护 **可覆盖模板**：`docs/openclaw/HEARTBEAT_AUTONOMOUS.md`。

**一键同步 HEARTBEAT**（会先备份原文件）：

```bash
bash /Users/apple/Ahope/newhigh/scripts/sync_openclaw_heartbeat.sh
```

**工作区 symlink + 同步 HEARTBEAT 一次做完**：

```bash
bash /Users/apple/Ahope/newhigh/scripts/openclaw_workspace_bootstrap.sh
```

**迭代开发前置（bootstrap + skills + 自检 + 交接文件索引）**：

```bash
make openclaw-iterate-ready
```

详见 **`tasks/openclaw_handoff.md`**。

同步后：Heartbeat / Cron 将按模板中步骤驱动「读计划 → 实现 → 测 → 记日志」。

---

## 4. 验证命令（Agent 与人类共用）

```bash
cd /Users/apple/Ahope/newhigh && source .venv/bin/activate
PYTHONPATH=gateway/src:core/src:data-pipeline/src python3 -m pytest gateway/tests/ -q
```

涉及执行层/数据管道时扩展 `PYTHONPATH` 并跑对应包 `tests/`。

---

## 4.5 Web / 小程序导航单源与 Cursor、OpenClaw 工作区对齐

**问题**：Web 与微信小程序若各改各的菜单，会出现路径、顺序、标签不一致。

**单源**：`config/navigation_manifest.json`（字段 `schemaVersion` 用于破坏性变更时的对齐标记）。

| 端 | 消费方式 |
|----|----------|
| Web | `frontend/src/config/menu.ts` 直接 `import` 该 JSON 派生 `menuItems` 等 |
| 小程序 | `python3 scripts/gen_miniprogram_menu.py` 生成 `integrations/hongshan/wechat-miniprogram/config/menu.generated.js`，`config/menu.js` 仅 re-export |

**改菜单后的必做**：

```bash
make sync-nav
# 或：python3 scripts/gen_miniprogram_menu.py
```

将 `menu.generated.js` 与 JSON 一并提交。

**Cursor 与 OpenClaw「版本一致」约定**（自动化迭代不断档）：

1. **同一仓库提交**：本机 OpenClaw 工作区应 `cd` 到与本仓库相同的 clone，并在拉取/合并后执行 `bash scripts/sync_openclaw_heartbeat.sh`，使 Heartbeat 与仓库内 `docs/openclaw/HEARTBEAT_AUTONOMOUS.md` 同源。  
2. **导航类变更**：改 `navigation_manifest.json` 后必须跑 `make sync-nav`，避免 Web 已变、小程序仍为旧 `DESKTOP_SYNC`。  
3. **记录**：在 `evolution/improvement_log_*.md` 中注明 `navigation_manifest.schemaVersion`（若当次有改）。

---

## 5. 运维心跳（与 OpenClaw 开发任务分离）

日常巡检、政策采集、launchd 等仍以仓库 **`docs/HEARTBEAT.md`** 为准；不要求 OpenClaw 每日执行，除非你在 Cron 中合并两段说明。

---

*维护：随 `OPENCLAW_IMPROVEMENT_PLAN` 阶段推进可更新 §2 优先级表述。*
