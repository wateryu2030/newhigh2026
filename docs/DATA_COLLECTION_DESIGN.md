# 数据采集机制整体设计（新闻 / 行情 / 股东）

本文档约定 **如何避免 DuckDB 写锁冲突**、**任务如何错峰**、**与 Gateway 如何共存**，与现有实现（`data-pipeline`、`scripts/start_schedulers.py`、`scripts/run_shareholder_collect.py`、`gateway`）对齐，作为运维与迭代的单一依据。

---

## 1. 核心约束（必须先接受的事实）

| 约束 | 含义 |
|------|------|
| **单库文件** | 生产事实源多为 `data/quant_system.duckdb`（由 `QUANT_*` / `NEWHIGH_*` 环境变量统一，见 `duckdb_manager`）。 |
| **DuckDB 并发模型** | **同一文件上不能多个进程同时持有「写模式」连接**；长时间批量写入会独占锁，Gateway、其它采集脚本再连即 `Could not set lock`。 |
| **Gateway** | 请求内可能 `get_conn(read_only=False)`（审计、部分路由），属于 **短连接**；与 **数小时级股东采集** 同库时必冲突。 |

**结论**：不是「多线程调优」能彻底解决的，而是 **写者串行化 + 读尽量短、尽量只读**。

---

## 2. 数据域划分与写入职责

### 2.1 新闻域

| 来源 | 典型入口 | 写入表（示例） | 特征 |
|------|-----------|----------------|------|
| RSS 宏观 | `rss_macro_news.update_rss_macro_news` | 新闻/快讯相关表 | 批量 INSERT，耗时分钟级 |
| 财新等 | `caixin_news` | 同上 | 可选 |
| 东财个股新闻 | `em_stock_news`（日内调度） | 新闻 + 关联 code | 按标的限流，与日内刷新绑定 |
| 政策/管道 | `policy_news_duckdb` 等 | 依模块 | 独立脚本时注意错峰 |

**设计原则**：新闻写入与 **大盘日 K 全量**、**股东大批量** 不要同一时刻启动；优先放在 **日内槽位**（08:30 / 12:00 / 22:00）或 **日终 18:00 批次内顺序执行**，避免与 02:00 股东长任务重叠。

### 2.2 行情 / 股票域（池、K 线、资金、涨停、龙虎榜等）

| 类型 | 典型入口 | 说明 |
|------|-----------|------|
| 股票池、资金流、龙虎榜 | `daily_scheduler.run_daily` | 每日主批次的一部分 |
| Tushare 日 K | `tushare_daily.update_all_tushare_daily` | 可全市场或限量，写 `a_stock_daily` |
| AkShare 日 K | `daily_kline` / ashare 管线 | 备用或补数 |
| 实时快照 | `realtime_scheduler`（约 30s） | 写 `a_stock_realtime` 等，**持续占用连接**时需与批量写错峰 |

**设计原则**：

- **Tushare / AkShare 大批量日 K** 与 **股东采集** 不要并行。
- **实时调度**若与 **日终全量 K** 并行，优先保证 **单写者**：可停实时 10–30 分钟或把实时改为「只读上游 + 低频写」。

### 2.3 股东域（十大股东等）

| 入口 | 说明 |
|------|------|
| `scripts/run_shareholder_collect.py` | **长任务、持续写库**，是锁冲突的主要来源 |
| `run_nightly_shareholder_coverage.py` | 晚间巡检，可能 **再起子进程补采** |

**设计原则**：股东任务必须落在 **低峰窗口**，且 **全局只能跑一个** 写库实例（见第 4 节互斥）。

---

## 3. 现有调度时间轴（`start_schedulers.py` 默认）

以下时间为 **本地时钟**，已做 **分钟级错峰**：

| 时刻 | 任务 | 风险 |
|------|------|------|
| **02:00** | 十大股东采集 | **高**：长时间写锁 |
| **02:05** | 数据质量巡检 | 中：短写 |
| **08:30 / 12:00 / 22:00** | 日内刷新（RSS、Tushare 增量、东财新闻、优先标的 K 线等） | 中：多段写，宜与股东错开 |
| **18:00** | 每日调度（股票池、资金流、龙虎榜 + 可选新闻 + Tushare） | 中高 |
| **22:15** | 股东覆盖巡检（可触发补采子进程） | 高（若补采则同股东采集） |
| **每 30s** | 实时行情循环 | 持续写，与 **02:00 长任务** 冲突风险大 |

**建议**：

- **02:00 股东采集进行时**：将 `INTRADAY_REFRESH_ENABLE=0` 或暂停实时调度线程（若可配置），或把股东改到 **01:00–03:00 以外** 的单独维护窗。
- **手动执行** `run_shareholder_collect.py` / `ensure_ashare_data_completeness.py`：先 `lsof data/quant_system.duckdb`，无其它写者再跑。

---

## 4. 全局互斥与串行策略（推荐落地）

### 4.1 单写令牌（已实现：flock）

批量写入口使用 **`lib/duckdb_write_lock.py`**：在 **与 `quant_system.duckdb` 同目录** 创建 `quant_system.duckdb.writer.lock`，`fcntl.flock` 独占写锁；阻塞等待默认最长 **7200s**，轮询间隔 3s。应急：**`NEWHIGH_SKIP_DUCKDB_FLOCK=1`** 跳过加锁。

已接入脚本：`scripts/run_shareholder_collect.py`、`scripts/ensure_market_data.py`、`scripts/ensure_ashare_data_completeness.py`。

Gateway **不参与** 该文件锁；仅 **批处理脚本** 使用。

### 4.2 进程级「不要并行」清单（运维强制执行）

**同一时刻只允许其一**：

- `run_shareholder_collect.py`（任意参数）
- `ensure_ashare_data_completeness.py`（全量/大范围）
- `ensure_market_data.py`（若写同一库）
- 手工 `run_pipeline_daily` 全量 K 线

**可与 Gateway 并行** 的前提：Gateway 以 **只读** 打开统计类路由；若仍出现锁错误，说明某路由或中间件使用了 **写连接**，需按路由收紧为只读或缩短连接时间。

### 4.3 读路径优化（降低冲突概率）

- 系统概览、只读报表：**`read_only=True`** 连接（DuckDB 允许多读单写，但勿与写进程混用 **同一进程内** 读写配置混接 —— 见 `duckdb_manager` 注释）。
- 审计写：短连接、请求结束即关。

---

## 5. 新闻 vs 行情 vs 股东：推荐执行顺序（单批次内）

在 **18:00 日批次** 或 **手动一键跑数** 时，建议顺序：

1. **股票池 / 基础元数据**（`update_stock_list`）  
2. **资金流、涨停、龙虎榜**（体量相对可控）  
3. **新闻**（RSS / 财新 / 东财，可并行子步骤但同一进程内串行即可）  
4. **日 K 增量**（Tushare 优先，AkShare 补洞）  
5. **股东**（仅当本批次 **无其它写任务**；或单独维护窗跑）

**不要**在顺序中把「股东」和「全市场 Tushare 日 K」交叉并行两个进程。

---

## 6. 监控与自愈

| 项 | 说明 |
|----|------|
| 锁冲突日志 | 采集脚本统一打 `[duckdb][write]` 前缀；Gateway 捕获后返回 503 时记 `path` + `pid`。 |
| 健康检查 | `GET /api/health/detailed`、数据新鲜度探针；**锁冲突时** 概览页会「未就绪」——先查 `lsof quant_system.duckdb`。 |
| 调度器 | `scripts/start_schedulers.py monitor` 日志：`logs/scheduler/scheduler_system.log`。 |

---

## 7. 配置开关速查（减少冲突）

| 变量 | 作用 |
|------|------|
| `INTRADAY_REFRESH_ENABLE` | 关则跳过 08:30/12:00/22:00 日内刷新 |
| `SCHEDULER_INTRADAY_TIMES` | 调整日内槽位，避开手动大任务 |
| `TUSHARE_DAILY_CODES_LIMIT` 等 | 限制日 K 批量范围，缩短写锁时间 |
| `INTRADAY_*` | 控制东财新闻条数、优先标的数量 |

---

## 8. 演进方向（可选）

1. **任务表 + 单 Worker 进程**：所有写请求入 `pipeline_jobs` 表，由 **唯一 worker** 顺序执行（适合未来上 Redis/Celery）。  
2. **从库只读**：DuckDB 定期导出 Parquet 或复制只读副本供重查询（成本较高）。  
3. **股东采集拆分为小事务**：按 code 批次提交并释放连接（需改脚本，减少单次持锁时间）。

---

## 9. 小结

- **稳定运行的关键**是：**同一 `quant_system.duckdb` 上同一时刻只有一个重度写者**；调度器已通过 **时间点错峰** 降低概率，**手动脚本与长驻实时任务**仍是主要风险源。  
- **新闻、行情、股东**三类任务应在 **时间轴与进程级** 上分层，并在文档与运维上固定 **互斥清单** 与 **推荐顺序**。  
- 出现锁错误时，优先 **`lsof` 查占用 PID**，结束冲突进程或等待批处理结束，再访问 Gateway。
