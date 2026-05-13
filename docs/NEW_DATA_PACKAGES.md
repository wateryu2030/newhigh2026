# 数据增量包 — 财报、传闻、连跌+回购/收购告警

## 简称 vs 包名 对照

| 简称 | 包路径 | 功能 |
|------|--------|------|
| financial-report | `packages/financial-report/src/financial_report/` | A 股财报下载分析（利润表/资产负债表/现金流量表） |
| rumor-capture | `packages/rumor-capture/src/rumor_capture/` | 公司传闻/澄清类信息采集 |
| buyback-alert | `packages/buyback-alert/src/buyback_alert/` | 连跌检测 + 回购/增持/收购告警 |

## 数据库表（由 `duckdb_manager.ensure_tables()` 自动创建）

- `financial_reports` — 财报数据（stock_code, report_date, statement_type, data_json 等）
- `company_rumors` — 公司传闻（title, content, source, rumor_type=利好/利空/辟谣/中性/其他）
- `buyback_events` — 回购/增持/要约收购事件（event_type=回购/增持/要约收购/溢价收购）
- `alerts` — 连跌+回购/收购交叉告警结果

数据写入位置：`data/quant_system.duckdb`（由 `.env` 内 `QUANT_SYSTEM_DUCKDB_PATH` 控制）

## 采集入口

```bash
# 统一 PYTHONPATH（所有包都需此前置）
export PYTHONPATH="packages/financial-report/src:packages/rumor-capture/src:packages/buyback-alert/src:."

# 1. 财报增量采集（默认跑3张表）
python -m financial_report --symbol 600519
python -m financial_report --symbol 000001,600519,300750
python -m financial_report --batch --limit 50               # 扫描全市场前50只
python -m financial_report --batch --dry-run                 # 预览模式

# 2. 公司传闻采集（雪球+东方财富股吧+现有 news_items）
python -m rumor_capture --source xueqiu --days 3
python -m rumor_capture --source xueqiu,guba --days 7 --dry-run
python -m rumor_capture --source news --days 30              # 从已有 news_items 筛选

# 3. 连跌+回购/收购告警（三步骤合一）
python -m buyback_alert --collect                            # 拉取回购/增持/收购数据
python -m buyback_alert --detect --min-days 3                # 检测连跌
python -m buyback_alert --alert                              # 交叉分析生成告警
python -m buyback_alert --run-all                            # 全流程
```

每个 CLI 均有 `--help` 查看全部参数。

## Gateway API

网关启动后（默认 8000 端口），新增 3 个只读端点：

```bash
# 查询财报
curl 'http://127.0.0.1:8000/api/new-data/financial-reports?stock_code=600519&limit=3'

# 查询传闻
curl 'http://127.0.0.1:8000/api/new-data/rumors?stock_code=600519&days=7&rumor_type=辟谣'

# 查询告警
curl 'http://127.0.0.1:8000/api/new-data/alerts?limit=10&alert_type=连跌+回购'
```

返回格式：`{"ok": true, "data": [...], "count": N}`

## 单元测试

```bash
PYTHONPATH="packages/financial-report/src:packages/rumor-capture/src:packages/buyback-alert/src:." python3 -m pytest packages/financial-report/tests/ -v
PYTHONPATH="packages/financial-report/src:packages/rumor-capture/src:packages/buyback-alert/src:." python3 -m pytest packages/rumor-capture/tests/ -v
PYTHONPATH="packages/financial-report/src:packages/rumor-capture/src:packages/buyback-alert/src:." python3 -m pytest packages/buyback-alert/tests/ -v
```

## 设计假设

1. **A 股 only** — 财报/传闻/回购均限沪深京三地，不扩 H/美（除非零成本扩展开关）
2. **akshare 主源** — 优先使用 akshare 接口；无 akshare 覆盖的走 requests 爬取
3. **Tushare token** — `.env` 中已有 `TUSHARE_TOKEN`，非必需（akshare 不需 token）
4. **无 key 接管的源跳过** — 不报错，日志写明跳过原因
5. **连跌窗口** — 默认 `min_days=3`（可配置），以 close 连续低于前一日为标准
6. **传闻来源** — 雪球热门推文、东方财富股吧热帖、现有 news_items 关键词匹配；不覆盖全量雪球/股吧
