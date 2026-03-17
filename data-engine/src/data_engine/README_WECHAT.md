# 微信公众号采集器集成说明

基于 [WeSpy](https://github.com/tianchangNorth/WeSpy) / [wespy-fetcher](https://github.com/wlzh/skills/tree/main/wespy-fetcher) 整合到 newhigh 数据引擎。

## 功能特性

- ✅ 微信公众号文章抓取（单篇/批量）
- ✅ 专辑系列文章追踪下载
- ✅ Markdown 格式转换（便于 NLP 处理）
- ✅ 元数据提取（标题、作者、发布时间、封面图）
- ✅ DuckDB 持久化存储
- ✅ 可选文件保存（Markdown + JSON + HTML）
- ✅ 降级模式（WeSpy 不可用时使用基础 HTTP 抓取）

## 安装依赖

### 方案 A：安装 WeSpy（推荐，完整功能）

```bash
cd /Users/apple/Ahope/newhigh
source .venv/bin/activate

# 安装 WeSpy
pip install wespy

# 或从源码安装（最新功能）
pip install git+https://github.com/tianchangNorth/WeSpy.git
```

### 方案 B：基础依赖（降级模式）

```bash
# 仅安装基础 HTTP 抓取依赖
pip install requests beautifulsoup4
```

### 验证安装

```bash
python -c "from data_engine.wechat_collector import WeChatCollector; print('✅ 模块加载成功')"
```

## 用法示例

### 1. 抓取单篇文章

```python
from data_engine.wechat_collector import WeChatCollector

collector = WeChatCollector(
    output_dir="~/newhigh/data/wechat_articles",
    save_html=False,
    save_json=True
)

# 抓取单篇
article = collector.fetch_article("https://mp.weixin.qq.com/s/xxxxx")

if article:
    print(f"标题：{article.title}")
    print(f"作者：{article.author}")
    print(f"发布时间：{article.publish_time}")
    print(f"内容长度：{len(article.content_md)} 字符")
    
    # 保存到数据库
    collector.save_to_db([article])
```

### 2. 批量抓取专辑

```python
# 抓取整个专辑（最多 20 篇）
articles = collector.fetch_album(
    "https://mp.weixin.qq.com/mp/appmsgalbum?__biz=xxx&album_id=xxx",
    max_articles=20,
    save_to_file=True
)

print(f"成功抓取 {len(articles)} 篇文章")

# 保存到数据库和文件
collector.save_to_db(articles)
collector.save_to_files(articles)
```

### 3. 便捷函数

```python
from data_engine.wechat_collector import collect_wechat_articles

urls = [
    "https://mp.weixin.qq.com/s/article1",
    "https://mp.weixin.qq.com/mp/appmsgalbum?...",  # 专辑
    "https://mp.weixin.qq.com/s/article2"
]

articles = collect_wechat_articles(
    urls=urls,
    output_dir="~/newhigh/data/wechat_articles",
    save_to_db=True,
    max_articles=20
)
```

### 4. 集成到调度器

```python
# 在 daily_scheduler.py 中添加每日微信采集任务
from data_engine.wechat_collector import WeChatCollector

def collect_daily_wechat():
    """每日微信文章采集"""
    collector = WeChatCollector()
    
    # 配置的监控公众号列表
    monitored_accounts = [
        "https://mp.weixin.qq.com/mp/appmsgalbum?__biz=xxx&album_id=xxx",
        # ... 更多专辑/文章
    ]
    
    all_articles = []
    for url in monitored_accounts:
        if 'appmsgalbum' in url:
            articles = collector.fetch_album(url, max_articles=5)
        else:
            article = collector.fetch_article(url)
            articles = [article] if article else []
        all_articles.extend(articles)
    
    # 持久化
    collector.save_to_db(all_articles)
    return len(all_articles)
```

## 数据库表结构

文章保存到 `quant.duckdb` 的 `wechat_articles` 表：

```sql
CREATE TABLE wechat_articles (
    id VARCHAR PRIMARY KEY,              -- 文章 ID（URL 哈希）
    title VARCHAR,                        -- 标题
    author VARCHAR,                       -- 作者
    publish_time VARCHAR,                 -- 发布时间
    url VARCHAR UNIQUE,                   -- 原始 URL
    content_md TEXT,                      -- Markdown 正文
    content_html TEXT,                    -- 原始 HTML
    summary TEXT,                         -- 摘要
    cover_image VARCHAR,                  -- 封面图 URL
    album_name VARCHAR,                   -- 所属专辑
    tags VARCHAR,                         -- 标签（JSON）
    meta_json TEXT,                       -- 其他元数据（JSON）
    fetched_at TIMESTAMP                  -- 抓取时间
);
```

### 查询示例

```sql
-- 查询最新文章
SELECT title, author, publish_time, url
FROM wechat_articles
ORDER BY fetched_at DESC
LIMIT 10;

-- 按专辑分组
SELECT album_name, COUNT(*) as article_count
FROM wechat_articles
WHERE album_name IS NOT NULL
GROUP BY album_name;

-- 全文搜索（使用 DuckDB 全文搜索）
SELECT title, author
FROM wechat_articles
WHERE content_md LIKE '%量化策略%';
```

## 文件输出结构

```
~/newhigh/data/wechat_articles/
├── 文章标题_abc123.md           # Markdown 正文
├── 文章标题_abc123_meta.json    # 元数据
├── 文章标题_def456.md
├── 文章标题_def456_meta.json
└── album_1234567890/            # 专辑专用目录
    ├── 文章 1_xxx.md
    ├── 文章 1_xxx_meta.json
    ├── 文章 2_yyy.md
    └── album_summary.json       # 专辑汇总
```

## 配置监控列表

在 `config/` 创建 `wechat_monitor.yaml`：

```yaml
# 微信公众号监控列表
# 用于每日自动采集市场情报、政策解读、行业动态

accounts:
  - name: "量化投资与金融科技"
    album_url: "https://mp.weixin.qq.com/mp/appmsgalbum?__biz=xxx&album_id=xxx"
    priority: high
    max_articles: 10
  
  - name: "券商中国"
    album_url: "https://mp.weixin.qq.com/mp/appmsgalbum?__biz=yyy&album_id=yyy"
    priority: normal
    max_articles: 5
  
  - name: "中国基金报"
    album_url: "https://mp.weixin.qq.com/mp/appmsgalbum?__biz=zzz&album_id=zzz"
    priority: normal
    max_articles: 5

# 采集频率
schedule:
  daily_time: "08:00"  # 每日采集时间
  max_requests_per_day: 100  # 频率限制
```

## 调度集成

编辑 `scheduler/src/scheduler/daily_scheduler.py`：

```python
from data_engine.wechat_collector import WeChatCollector

def run_wechat_collection():
    """运行微信文章采集任务"""
    collector = WeChatCollector()
    
    # 从配置读取监控列表
    monitored_urls = load_wechat_monitor_config()
    
    total_articles = 0
    for url in monitored_urls:
        if 'appmsgalbum' in url:
            articles = collector.fetch_album(url, max_articles=10)
        else:
            article = collector.fetch_article(url)
            articles = [article] if article else []
        
        if articles:
            collector.save_to_db(articles)
            total_articles += len(articles)
    
    return total_articles
```

## 注意事项

### 1. 合法合规使用

- 遵守微信公众号 robots.txt
- 尊重内容创作者知识产权
- 不用于商业目的
- 合理控制请求频率（避免对服务器造成压力）

### 2. 速率控制

WeSpy 内置速率控制，但建议：
- 单篇文章间隔 ≥ 0.5 秒
- 每日请求 ≤ 500 次
- 专辑批量下载时设置 `max_articles` 限制

### 3. 图片防盗链

WeSpy 使用 `images.weserv.nl` 代理服务处理图片防盗链，如果图片无法显示：
- 原图片可能已被删除
- 网络问题导致代理失败
- 可考虑本地下载图片（需额外配置）

### 4. 错误处理

```python
article = collector.fetch_article(url)
if not article:
    logger.warning(f"抓取失败：{url}")
    # 降级处理或重试
```

## 故障排除

### 问题：WeSpy 未安装

```bash
# 检查安装
python -c "import wespy; print(wespy.__version__)"

# 重新安装
pip install --upgrade wespy
```

### 问题：抓取失败

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 检查 URL 是否有效
import requests
response = requests.get(url)
print(response.status_code)
```

### 问题：数据库写入失败

```python
# 检查数据库路径
import os
db_path = "~/Ahope/newhigh/data/quant.duckdb"
print(os.path.exists(os.path.expanduser(db_path)))

# 手动创建表
import duckdb
conn = duckdb.connect(db_path)
conn.execute("SELECT * FROM wechat_articles LIMIT 1")
```

## 扩展方向

1. **定时任务** - 集成到 `daily_scheduler.py` 每日自动采集
2. **NLP 分析** - 对抓取内容进行情感分析、关键词提取
3. **信号生成** - 基于政策解读生成交易信号
4. **专辑追踪** - 长期追踪特定专栏，建立知识图谱
5. **多账号监控** - 批量监控多个公众号，建立行业情报库

## 参考资源

- WeSpy 官方文档：https://github.com/tianchangNorth/WeSpy
- wespy-fetcher: https://github.com/wlzh/skills/tree/main/wespy-fetcher
- DuckDB 文档：https://duckdb.org/docs/
