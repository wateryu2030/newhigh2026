# 情绪周期 + 龙虎榜 自动执行说明书

供 **Cursor** 与 **OpenClaw** 自动执行：每日刷新情绪周期与龙虎榜游资共振，并写入 JSON，供仓位纪律与选股使用。

---

## 一、执行内容

| 步骤 | 说明 | 输出 |
|------|------|------|
| 1 | 拉取当日涨停池/炸板/成交额（AKShare） | 情绪分、周期、建议仓位 |
| 2 | 拉取当日龙虎榜明细（AKShare） | 游资得分、共振龙头列表 |
| 3 | 写入 `data/daily_emotion.json` | 供 OpenClaw/策略 读取仓位建议 |
| 4 | 写入 `data/dragon_lhb_pool.json` | 供 OpenClaw/策略 仅在启动·加速期使用共振股 |

---

## 二、执行方式

### 方式 A：HTTP 接口（推荐，平台已启动时）

```bash
# 项目根目录，确保 web 已启动（如 python web_platform.py）
curl -X POST http://127.0.0.1:5050/api/emotion/refresh -H "Content-Type: application/json" -d '{}'
```

成功返回示例：`{"success": true, "daily_emotion": "data/daily_emotion.json", "dragon_lhb_pool": "data/dragon_lhb_pool.json", "emotion_cycle": "启动"}`

### 方式 B：命令行脚本（无需启动 Web）

```bash
# 项目根目录，激活 venv 后执行
python3 scripts/run_emotion_lhb_daily.py
# 或
.venv/bin/python scripts/run_emotion_lhb_daily.py
```

### 方式 C：定时任务（每日收盘后）

- **crontab**（工作日 15:35 执行，需先启动 Web 则用方式 B 更简单）：
  ```cron
  35 15 * * 1-5 cd /path/to/astock && .venv/bin/python scripts/run_emotion_lhb_daily.py
  ```
- 或由 **Cursor / OpenClaw** 按下方「自动执行任务文本」每日触发。

---

## 三、读取结果

- **仓位纪律**：读 `data/daily_emotion.json` 的 `emotion_cycle`、`suggested_position_pct`，按说明书仓位表执行（冰点≤20%、启动 30–50%、加速 60%、高潮减仓、退潮清仓）。
- **龙虎榜选股**：仅当 `emotion_cycle` 为 **启动** 或 **加速** 时，读 `data/dragon_lhb_pool.json` 的 `resonance_list` 作为游资共振龙头池；否则不做龙虎榜共振股。

---

## 四、Cursor 自动执行任务文本（复制即用）

将下面整段交给 Cursor，让其**自动执行**一次情绪+龙虎榜刷新并检查结果：

```
任务名称：情绪周期与龙虎榜自动执行（单次）

要求：
1. 在项目根目录执行情绪+龙虎榜刷新（优先调用 POST /api/emotion/refresh；若 Web 未启动则运行 scripts/run_emotion_lhb_daily.py）。
2. 检查 data/daily_emotion.json 是否存在且含 emotion_cycle、suggested_position_pct、emotion_score。
3. 检查 data/dragon_lhb_pool.json 是否存在且含 resonance_list、lhb_score、emotion_ok。
4. 若任一文件缺失或接口报错，根据 docs/EMOTION_LHB_AUTO_EXEC.md 排查并修复后重试。

参考文档：docs/EMOTION_LHB_AUTO_EXEC.md
接口文档：POST /api/emotion/refresh；GET /api/emotion_dashboard；GET /api/dragon_lhb_pool。
```

---

## 五、OpenClaw 自动执行任务文本（复制即用）

将下面整段复制到 OpenClaw 作为任务描述，用于**自动执行**情绪+龙虎榜每日流程：

```
你是量化运维助手。

任务：执行「情绪周期 + 龙虎榜」每日刷新。

步骤：
1. 进入项目根目录（astock）。
2. 若 Web 已运行在 5050 端口：调用 POST http://127.0.0.1:5050/api/emotion/refresh，Content-Type: application/json，body 为空对象。
3. 若 Web 未运行：在项目根目录执行 python scripts/run_emotion_lhb_daily.py（或 .venv/bin/python scripts/run_emotion_lhb_daily.py）。
4. 验证 data/daily_emotion.json 和 data/dragon_lhb_pool.json 已更新，且 daily_emotion 中有 emotion_cycle、suggested_position_pct。
5. 若失败：根据 docs/EMOTION_LHB_AUTO_EXEC.md 排查（网络、akshare、路径）。

成功标准：两个 JSON 文件存在且可读，接口或脚本无报错。
参考：docs/EMOTION_LHB_AUTO_EXEC.md
```

---

## 六、模块与接口速查

| 模块 | 路径 | 说明 |
|------|------|------|
| 情绪引擎 | `core/sentiment_engine.py` | `get_emotion_state()`, `save_daily_emotion_json()` |
| 龙虎榜引擎 | `core/lhb_engine.py` | `get_dragon_lhb_pool()`, `save_dragon_lhb_pool_json()` |
| 情绪 API | `GET /api/emotion_dashboard` | 返回周期、仓位、情绪分、涨停数、连板高、炸板率 |
| 龙虎榜 API | `GET /api/dragon_lhb_pool` | 返回游资得分、共振列表（依情绪过滤） |
| 刷新并写 JSON | `POST /api/emotion/refresh` | 刷新并写入 daily_emotion.json、dragon_lhb_pool.json |

---

## 七、故障排查

- **akshare 报错 / 无数据**：检查网络与 akshare 版本；非交易日或盘中可能无当日涨停/龙虎榜，属正常，引擎会回退默认值。
- **404 / 500**：确认 API 路由已注册（`api/routes.py` 中 `emotion_dashboard`、`dragon_lhb_pool`、`emotion/refresh`），且主应用已挂载 `register_routes(app)`。
- **JSON 未生成**：检查 `data/` 目录可写；若用接口刷新，确认返回 `success: true` 再查文件。
