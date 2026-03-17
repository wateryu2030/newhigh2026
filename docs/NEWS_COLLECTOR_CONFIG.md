# 新闻采集器配置说明

## 优化版采集器

**文件**: `news_collector_optimized.py`

### 数据源

| 数据源 | 状态 | 说明 |
|--------|------|------|
| 东方财富快讯 | 🟡 API 限流 | 财经快讯，实时性强 |
| 新浪财经 | ✅ 正常 | 财经新闻，20 条/次 |
| 金十数据 | 🟡 需解析 JS | 全球财经快讯 |
| RSS 订阅 | ✅ 正常 | 可自定义订阅源 |
| 本地文件 | ✅ 正常 | 手动添加重要新闻 |

### 使用方法

```bash
# 采集所有数据源
.venv/bin/python3 news_collector_optimized.py

# 只采集特定数据源
.venv/bin/python3 news_collector_optimized.py --sources sina eastmoney

# 不保存到数据库
.venv/bin/python3 news_collector_optimized.py --no-db

# 使用自定义配置
.venv/bin/python3 news_collector_optimized.py --config news_config.json
```

### 自定义配置

创建 `news_config.json`:

```json
{
  "rss_feeds": {
    "feeds": [
      "https://feeds.feedburner.com/pancaitan",
      "https://your-custom-rss-url.com/feed.xml"
    ]
  },
  "local_sources": {
    "files": [
      "data/manual_news.json"
    ]
  }
}
```

### 数据库表结构

```sql
news_items (
    ts TIMESTAMP,
    symbol VARCHAR,
    source_site VARCHAR,  -- 数据来源：sina, eastmoney, caixin 等
    source VARCHAR,
    title VARCHAR,
    content VARCHAR,
    url VARCHAR,
    keyword VARCHAR,
    tag VARCHAR,
    publish_time VARCHAR,
    sentiment_score DOUBLE,
    sentiment_label VARCHAR
)
```

### 定时任务

建议每 30 分钟采集一次：

```bash
# 添加到 crontab
*/30 * * * * cd /Users/apple/Ahope/newhigh && .venv/bin/python3 news_collector_optimized.py --sources sina --no-json
```

## 旧版采集器

**文件**: `improved_official_news_collector.py`

- 采集新华社、国务院、住建部等官方新闻
- 因网站反爬保护，目前采集效果不佳
- 建议作为备用数据源

## 数据源优先级

1. **新浪财经** - 稳定、易采集
2. **RSS 订阅** - 可自定义、无反爬
3. **东方财富** - 需处理限流
4. **本地文件** - 手动补充

## 监控与维护

- 检查采集日志：`news_collection_*.json`
- 数据库查询：`SELECT COUNT(*) FROM news_items WHERE source_site = 'sina'`
- 定期更新 RSS 订阅源
