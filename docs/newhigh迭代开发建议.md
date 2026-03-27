# newhigh 迭代开发建议

> 本文档由仓库内股东策略页、数据栈与发布链路相关讨论整理而成，**供飞书协同修订**：请在飞书上直接增补负责人、时间点、接口契约与验收标准；本文件可定期同步回 Git。

---

## 1. 背景与结论摘要

### 1.1 页面上「像演示」的根因

- 往往不是「纯前端写死」，而是 **接口返回 0、缺字段或库表无数据**（例如持仓市值、PE 曾为 0；日线未回填时气泡图挤在原点附近）。
- 修复路径：**先对齐数据与 API 语义**，再迭代组件与交互。

### 1.2 股东搜索「变笨」

- 根因曾是 **仅子串 `LIKE`**，导致「王士忱」与「王世忱」一类单字差异无法命中。
- 已在 Gateway 增加 **首尾字匹配 + `difflib` 近似名**；与 Cursor「技能 / MCP」无关，全部为 DuckDB + 标准库。

### 1.3 前端 Chunk 加载失败（`Loading chunk … failed`）

- 典型为 **旧 HTML（缓存）引用已删除的 `_next/static/chunks/*.js`**（新版本 content-hash 已变）。
- 工程侧已加强 **`Cache-Control` 策略** 与 **Chunk 失败自动刷新一次**；**运维侧**需控制 **HTML 在 CDN 的缓存**、**发布时 Purge**、尽量 **原子发布**。

### 1.4 股东策略页信息架构（当前状态）

- **Tab**：「筹码池」与「股东画像」分离职责。
- **画像侧**：真实行业雷达（`getIndustryRadarData`）、日线驱动的气泡与持仓估算、持股全景（名称+代码）、点击出 K 线、**协同股东（同榜 Top10 SQL Top N）**。

### 1.5 策略信号闭环（已落地一版）

- **`scripts/push_shareholder_chip_signals.py`**：将反量化/筹码候选写入 `trade_signals`，`strategy_id=shareholder_chip`；仅 `DELETE` 该 id 再插入，与 `ai_fusion` 并存。  
- **`scripts/start_schedulers.py`**：每日 `run_daily` 完成后默认执行上述脚本（可用 **`NEWHIGH_PUSH_SHAREHOLDER_CHIP_SIGNALS=0`** 关闭）。回测仍可用 `signal_source=trade_signals` + `strategy_id` 过滤（见 backtest-engine）。

---

## 2. 下一步开发方向（按价值与依赖排序）

### 方向 A：数据层「填满」

| 建议项 | 说明 |
|--------|------|
| `top_10_shareholders` 覆盖与质量 | 股东搜索、画像、协同股东、反量化池均依赖；关注报告期连续性、名称规范。 |
| `a_stock_basic` / `a_stock_daily` 与重点代码 | 气泡图、持仓估算市值、K 线抽屉；缺日线则功能退化。 |
| 数据质量对外可解释 | 若已有 `/data/quality` 等，可在大屏或股东页展示「为何为空」的运维事实。 |

### 方向 B：策略与执行闭环

| 建议项 | 说明 |
|--------|------|
| 候选池 → `trade_signals` | 定时任务写入、`strategy_id` 约定、失败重试与可观测性。 |
| 与 risk / execution 对齐 | 信号落库前风控、去重、报告期时效。 |

### 方向 C：股东画像产品深化（在 A 稳定后）

| 建议项 | 说明 |
|--------|------|
| 协同股东 | 时间窗可配（如仅最新报告期 vs 近两期）、导出、与对比分析联动。 |
| 行业雷达 | `industry` 与展示轴（申万示例轴）映射治理，必要时独立 mapping。 |
| 对比 / 回测 | 与「点协同股东切画像」形成完整链路。 |

### 方向 D：工程与发布

| 建议项 | 说明 |
|--------|------|
| CDN / 发布流水线 | HTML 短缓存、发布后 Purge；减少 Chunk 错配复发。 |
| 运维手册 | 与 `scripts/restart_gateway_frontend.sh`、`/health` 等固定为团队共识。 |

---

## 3. 建议实施阶段（可在飞书拆解为迭代）

**阶段 1（挡板，优先）**  
- 股东相关表与 API 的 **巡检脚本 + 阈值/告警**（可先 Slack/飞书 webhook）。  
- **日线回填策略**（全市场 vs 白名单、节奏、存储与成本）。  
- **发布 checklist**：build → 部署 → Purge → 抽测关键页与 chunk。

**阶段 2（闭环）**  
- [x] **筹码候选 → `trade_signals`**（脚本 + 调度器）；待办：前端 AI 交易/系统监控明确展示 `shareholder_chip` 条数或与多策略 Tab 联动。

**阶段 3（持续）**  
- 画像深化：协同股东时间窗、双股东对比 API、行业映射表。  
- 与回测/模拟盘的 **策略来源字段** 对齐，便于归因。

---

## 4. 飞书协同时建议补全的字段（模板）

可在飞书文档中逐条补充下表，再择机写回本文件。

| ID | 主题 | 负责人 | 目标日期 | 验收标准 | 依赖 |
|----|------|--------|----------|----------|------|
| T1 | … | … | … | … | … |

---

## 5. 相关代码与脚本索引（便于跳转）

| 用途 | 路径 |
|------|------|
| 股东搜索 / 画像 / 协同股东 API | `gateway/src/gateway/endpoints_api/financial.py` |
| 股东策略前端布局 | `frontend/src/components/shareholder-strategy/ShareholderStrategyLayout.tsx` |
| Chunk 容错与 Providers | `frontend/src/components/ChunkLoadRecovery.tsx`、`ClientProviders.tsx` |
| Next 缓存响应头 | `frontend/next.config.js` |
| 本机重启 Gateway + Next | `scripts/restart_gateway_frontend.sh` |
| 筹码池 → trade_signals | `scripts/push_shareholder_chip_signals.py` |
| Cloudflare / Tunnel 说明 | `docs/NEWHIGH_COM_CLOUDFLARE.md` |

---

*文档版本：随仓库提交更新；飞书侧请以最新磋商为准。*
