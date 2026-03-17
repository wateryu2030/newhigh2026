# 东方财富网 Skill 集成文档

## 概述

东方财富网新闻采集 Skill，用于从东方财富网采集财经新闻、快讯等资讯数据。

## 文件位置

```
/Users/apple/Ahope/newhigh/skills/eastmoney_news_skill.py
```

## 依赖

```bash
cd /Users/apple/Ahope/newhigh
source .venv/bin/activate
pip install requests beautifulsoup4 feedparser
```

## 使用方法

### 1. 独立运行

```bash
cd /Users/apple/Ahope/newhigh
source .venv/bin/activate
python skills/eastmoney_news_skill.py
```

### 2. 作为模块导入

```python
from skills.eastmoney_news_skill import EastMoneyNewsSkill

skill = EastMoneyNewsSkill()
result = skill.collect_all(limit_per_source=20)

if result['success']:
    print(f"采集成功：{result['count']} 条")
    for news in result['news'][:5]:
        print(f"  - {news['title']}")
```

### 3. 集成到 multi_source_news.py

在 `data-pipeline/src/data_pipeline/collectors/multi_source_news.py` 中添加东财数据源：

```python
# 东方财富号（已修复）
sources['eastmoney_caifuhao'] = NewsSource(
    id='eastmoney_caifuhao',
    name='东方财富号',
    url='https://caifuhao.eastmoney.com/',
    source_type=SourceType.WEB,
    priority=SourcePriority.HIGH,
    category='financial',
    selector='li a[href*="/news/"]',
    enabled=True
)
```

## 输出格式

```json
{
  "success": true,
  "count": 20,
  "news": [
    {
      "id": "abc123...",
      "title": "新闻标题",
      "content": "新闻内容",
      "source": "东方财富号",
      "url": "https://caifuhao.eastmoney.com/news/...",
      "publish_time": "2026-03-17 08:00:00",
      "collected_at": "2026-03-17 08:45:00",
      "category": "financial",
      "keywords": []
    }
  ],
  "stats": {
    "total_collected": 20,
    "by_source": {
      "caifuhao": 20
    },
    "last_update": "2026-03-17 08:45:00"
  }
}
```

## 注意事项

1. **动态内容**: 东财网部分内容为 JavaScript 动态加载，RSS 源已失效
2. **缓存**: 默认 30 分钟缓存，可通过 `no_cache=True` 跳过
3. **频率限制**: 建议采集间隔 >= 5 秒，避免被反爬
4. **浏览器模式**: 如需采集动态内容，可使用 `use_browser=True` 并配合 browser 工具

## 已知问题

- RSS 源全部返回 404（2026-03-17 验证）
- 网页结构可能变化，需定期更新选择器
- 部分内容需要登录或 App 才能访问

## 改进计划

1. [ ] 添加浏览器自动化采集（支持动态内容）
2. [ ] 接入第三方财经 API 作为补充
3. [ ] 添加新闻内容全文抓取
4. [ ] 实现智能去重（基于内容相似度）

## 测试状态

- [x] 模块导入正常
- [x] 依赖安装正常
- [ ] 网页采集正常（需修复选择器）
- [ ] RSS 采集正常（源已失效）
- [ ] 浏览器采集正常（待实现）

---

**创建时间**: 2026-03-17  
**最后更新**: 2026-03-17  
**维护者**: OpenClaw 定时任务系统
