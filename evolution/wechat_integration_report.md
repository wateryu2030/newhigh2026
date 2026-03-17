# 微信公众号采集能力整合报告

**执行时间**: 2026-03-15 22:55  
**任务来源**: 群聊指令 - 研究 wespy-fetcher 并整合到 newhigh 项目  
**执行者**: OpenClaw (Iwork)

---

## 📋 任务概述

整合 [wespy-fetcher](https://github.com/wlzh/skills/tree/main/wespy-fetcher) / [WeSpy](https://github.com/tianchangNorth/WeSpy) 能力到 newhigh 量化平台，用于：
1. 抓取微信公众号文章（市场情报、政策解读、行业动态）
2. 专辑批量下载（系列专题追踪）
3. Markdown 转换（便于 NLP 处理和分析）
4. 元数据提取和持久化存储

---

## ✅ 已完成的工作

### 1. 技术研究

**wespy-fetcher 能力清单**:
- ✅ 微信公众号文章抓取（单篇/批量）
- ✅ 专辑列表获取和批量下载
- ✅ Markdown/HTML/JSON 多格式输出
- ✅ 图片防盗链处理
- ✅ 通用网页文章提取
- ✅ 命令行和 Python API 双模式

**上游项目 WeSpy**:
- GitHub: https://github.com/tianchangNorth/WeSpy
- PyPI: `pip install wespy`
- 功能：专注微信公众号文章提取和转换
- 特性：智能内容识别、专辑批量、速率控制

### 2. 集成模块开发

**文件**: `/Users/apple/Ahope/newhigh/data-engine/src/data_engine/wechat_collector.py`

**核心类**:
- `WeChatCollector` - 主采集器类
- `WeChatArticle` - 文章数据结构

**核心方法**:
| 方法 | 功能 |
|------|------|
| `fetch_article(url)` | 抓取单篇文章 |
| `fetch_album(url, max_articles)` | 批量抓取专辑 |
| `save_to_db(articles)` | 保存到 DuckDB |
| `save_to_files(articles)` | 保存到文件 |

**设计特性**:
- ✅ **可选依赖** - WeSpy 未安装时降级为 HTTP 抓取
- ✅ **统一接口** - 无论是否安装 WeSpy，API 保持一致
- ✅ **数据持久化** - 自动写入 `quant.duckdb`
- ✅ **调度集成** - 可被 `daily_scheduler` 调用
- ✅ **错误处理** - 完善的日志和异常处理

### 3. 文档和配置

**创建的文件**:
| 文件 | 说明 |
|------|------|
| `README_WECHAT.md` | 完整使用说明（6.8KB） |
| `requirements-wechat.txt` | 依赖清单 |
| `wechat_integration_report.md` | 本整合报告 |

**文档内容**:
- 安装指南
- 用法示例（单篇/批量/便捷函数/调度集成）
- 数据库表结构
- 文件输出结构
- 配置监控列表示例
- 故障排除

---

## 📦 安装和验证

### 安装依赖

```bash
cd /Users/apple/Ahope/newhigh
source .venv/bin/activate

# 方案 A：完整功能（推荐）
pip install wespy

# 方案 B：基础功能（降级模式）
pip install requests beautifulsoup4
```

### 验证模块

```bash
python -c "from data_engine.wechat_collector import WeChatCollector; print('✅ 成功')"
```

**当前状态**: ✅ 模块已创建，待安装 WeSpy 后验证完整功能

---

## 🎯 使用示例

### 1. 抓取单篇文章

```python
from data_engine.wechat_collector import WeChatCollector

collector = WeChatCollector()
article = collector.fetch_article("https://mp.weixin.qq.com/s/xxxxx")

if article:
    print(f"标题：{article.title}")
    collector.save_to_db([article])
```

### 2. 批量抓取专辑

```python
articles = collector.fetch_album(
    "https://mp.weixin.qq.com/mp/appmsgalbum?__biz=xxx&album_id=xxx",
    max_articles=20
)
collector.save_to_db(articles)
```

### 3. 集成到每日调度

在 `daily_scheduler.py` 中添加：

```python
def run_wechat_collection():
    """每日微信文章采集"""
    collector = WeChatCollector()
    monitored_urls = [...]  # 从配置读取
    for url in monitored_urls:
        articles = collector.fetch_album(url) if 'album' in url else [collector.fetch_article(url)]
        collector.save_to_db(articles)
```

---

## 🗄️ 数据库集成

### 表结构

```sql
CREATE TABLE wechat_articles (
    id VARCHAR PRIMARY KEY,
    title VARCHAR,
    author VARCHAR,
    publish_time VARCHAR,
    url VARCHAR UNIQUE,
    content_md TEXT,          -- Markdown 正文
    content_html TEXT,
    summary TEXT,
    cover_image VARCHAR,
    album_name VARCHAR,
    tags VARCHAR,             -- JSON
    meta_json TEXT,           -- JSON
    fetched_at TIMESTAMP
);
```

### 查询示例

```sql
-- 最新文章
SELECT title, author, publish_time 
FROM wechat_articles 
ORDER BY fetched_at DESC 
LIMIT 10;

-- 专辑统计
SELECT album_name, COUNT(*) 
FROM wechat_articles 
GROUP BY album_name;
```

---

## 📊 应用场景

### 1. 市场情报监控

监控金融类公众号，自动提取：
- 政策解读（央行、证监会、银保监会）
- 行业动态（券商、基金、保险）
- 市场分析（投资策略、行业研究）

### 2. 量化信号生成

基于文章内容分析：
- 情感分析 → 市场情绪指标
- 关键词提取 → 热点主题追踪
- 政策密度 → 监管风向标

### 3. 知识图谱构建

长期追踪特定专栏：
- 建立行业知识体系
- 追踪专家观点演变
- 发现潜在投资机会

### 4. 自动日报生成

每日采集 + NLP 分析 → 自动生成：
- 政策汇总
- 热点话题
- 市场情绪报告

---

## 🔧 下一步建议

### 短期（本周）

1. **安装 WeSpy**
   ```bash
   pip install wespy
   ```

2. **配置监控列表**
   创建 `config/wechat_monitor.yaml`，列出要监控的公众号/专辑

3. **集成到调度器**
   在 `daily_scheduler.py` 中添加每日采集任务

4. **测试验证**
   抓取测试文章，验证数据库写入和文件保存

### 中期（本月）

1. **NLP 分析集成**
   - 情感分析（正面/负面/中性）
   - 关键词提取
   - 主题分类

2. **信号生成实验**
   - 基于政策关键词生成交易信号
   - 回测信号效果

3. **监控告警**
   - 特定关键词出现时告警
   - 重要政策实时通知

### 长期（下季度）

1. **多源数据融合**
   - 微信文章 + 新闻 API + 研报
   - 建立统一情报库

2. **AI 分析增强**
   - 使用 LLM 进行深度分析
   - 自动生成投资洞察报告

3. **知识图谱**
   - 实体识别（公司、人物、产品）
   - 关系抽取
   - 图谱可视化

---

## ⚠️ 注意事项

### 合法合规

- 遵守微信公众号 robots.txt
- 尊重内容创作者知识产权
- 不用于商业目的
- 合理控制请求频率

### 速率控制

- 单篇文章间隔 ≥ 0.5 秒
- 每日请求 ≤ 500 次
- 专辑批量设置 `max_articles` 限制

### 错误处理

- 网络异常自动重试
- 失败文章记录日志
- 不影响整体采集流程

---

## 📁 文件清单

```
/Users/apple/Ahope/newhigh/
├── data-engine/
│   ├── src/data_engine/
│   │   └── wechat_collector.py        ✅ 17KB 核心采集模块
│   └── requirements-wechat.txt        ✅ 依赖清单
│
├── data-engine/src/data_engine/
│   └── README_WECHAT.md               ✅ 6.8KB 使用说明
│
└── evolution/
    └── wechat_integration_report.md   ✅ 本整合报告
```

---

## 🎉 总结

**整合成果**:
- ✅ 完成 WeSpy/wespy-fetcher 技术研究
- ✅ 创建统一的 `WeChatCollector` 集成模块
- ✅ 支持单篇/批量抓取、数据库持久化
- ✅ 提供完整文档和使用示例
- ✅ 可无缝集成到现有调度系统

**核心价值**:
1. **知识储备增强** - 自动采集微信公众号高质量内容
2. **市场监测能力** - 实时追踪政策、行业、市场动态
3. **NLP 分析基础** - Markdown 格式便于后续处理
4. **可扩展架构** - 易于添加新数据源和分析功能

**后续行动**:
1. 安装 WeSpy 依赖
2. 配置监控列表
3. 集成到每日调度
4. 开展 NLP 分析实验

---

**报告生成**: OpenClaw (Iwork)  
**时间**: 2026-03-15 22:55  
**状态**: ✅ 整合完成，待部署验证
