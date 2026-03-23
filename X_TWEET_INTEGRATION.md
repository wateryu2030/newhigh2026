# X-Twitter/微信公众号新闻采集集成

## 📦 集成内容

已将 [x-tweet-fetcher](https://github.com/ythx-101/x-tweet-fetcher) 集成到 newhigh 量化平台，增强新闻和舆情采集能力。

### 文件结构

```
newhigh/
├── news_collector_x_tweet.py          # 主采集器脚本
├── x_tweet_accounts.txt               # Twitter 监控账号列表
├── tools/
│   └── x-tweet-fetcher/               # x-tweet-fetcher 项目
└── scripts/schedule/
    ├── com.redmountain.newhigh.x-tweet.plist       # Twitter 定时任务 (30 分钟)
    ├── com.redmountain.newhigh.wechat-daily.plist  # 微信定时任务 (每日)
    ├── run_x_tweet_collector.sh       # 运行包装脚本
    └── install_x_tweet_schedule.sh    # 安装脚本
```

## 🚀 功能特性

### 1. Twitter 监控
- **监控账号**: 21 个财经/政策/科技类账号
  - 科技领袖：@elonmusk, @SamAltman, @darioamodei
  - 金融机构：@FinancialTimes, @BloombergNews, @Reuters, @WSJ
  - 政策监管：@SecPress, @federalreserve, @IMFNews
  - AI 公司：@OpenAI, @AnthropicAI, @StabilityAI
  - 等等...

- **采集频率**: 每 30 分钟检查一次
- **输出格式**: 与现有 news_collector_optimized.py 对齐

### 2. 微信公众号搜索
- **关键词**: 量化交易、AI Agent、金融科技、宏观经济
- **采集频率**: 每天上午 9:00
- **数据源**: 搜狗微信搜索 (无需 API key)

## 📋 安装步骤

### 1. 安装定时任务

```bash
cd /Users/apple/Ahope/newhigh/scripts/schedule
./install_x_tweet_schedule.sh
```

### 2. 手动测试

```bash
cd /Users/apple/Ahope/newhigh
python3 news_collector_x_tweet.py --no-db
```

### 3. 自定义监控账号

编辑 `x_tweet_accounts.txt`:

```bash
# 添加新账号 (每行一个，@ 符号可选)
@YourFavoriteAccount
```

## 🔧 命令行参数

```bash
python3 news_collector_x_tweet.py [选项]

选项:
  -a, --accounts FILE      Twitter 账号列表文件 (默认：x_tweet_accounts.txt)
  -k, --keywords KEYWORDS  微信公众号搜索关键词 (默认：量化交易 AI Agent 金融科技)
  --twitter-limit NUM      每个 Twitter 账号获取的推文数 (默认：5)
  --wechat-limit NUM       每个关键词获取的文章数 (默认：10)
  -o, --output FILE        输出 JSON 文件路径
  --no-db                  不保存到数据库
```

### 示例

```bash
# 仅采集 Twitter (不保存数据库)
python3 news_collector_x_tweet.py --wechat-limit 0 --no-db

# 仅采集微信公众号
python3 news_collector_x_tweet.py --twitter-limit 0 --keywords "量化交易" "人工智能"

# 自定义输出文件
python3 news_collector_x_tweet.py -o my_news.json
```

## 📊 数据输出

### JSON 格式

```json
[
  {
    "id": "7b273fff49434f5642fabe640b1cecd0",
    "title": "4 月 7 日新政落地：量化交易的"分仓铠甲"与"速度利刃"被同时卸下",
    "content": "...",
    "source": "微信公众号",
    "department": "wechat",
    "url": "https://weixin.sogou.com/...",
    "publish_time": "2026-03-19",
    "keywords": ["量化交易"],
    "collected_at": "2026-03-19T23:22:11.056727",
    "sentiment_score": null
  }
]
```

### 数据库表

数据写入 `news_items` 表，字段:
- `symbol`: 股票代码 (空)
- `source_site`: 来源站点 (wechat/x_tweet)
- `source`: 来源名称
- `title`: 标题
- `content`: 内容
- `url`: 链接
- `publish_time`: 发布时间
- `sentiment_score`: 情感分数

## ⚠️ 注意事项

### Twitter 采集限制
- **基础功能** (单条推文): 无需额外配置，直接可用
- **高级功能** (时间线、回复): 需要 Camofox 浏览器代理
- **当前状态**: Twitter 时间线采集返回 0 条 (需要 Camofox)

### 微信公众号
- ✅ 完全可用，无需额外配置
- 使用搜狗微信搜索，无 API key 需求
- 搜索结果包含标题、链接、日期

## 🔍 故障排查

### 查看日志

```bash
# X-Twitter 日志
tail -f /Users/apple/Ahope/newhigh/logs/x_tweet_stdout.log
tail -f /Users/apple/Ahope/newhigh/logs/x_tweet_stderr.log

# 微信公众号日志
tail -f /Users/apple/Ahope/newhigh/logs/wechat_daily_stdout.log
```

### 检查定时任务状态

```bash
launchctl list | grep newhigh
```

### 卸载定时任务

```bash
launchctl unload /Users/apple/Ahope/newhigh/scripts/schedule/com.redmountain.newhigh.x-tweet.plist
launchctl unload /Users/apple/Ahope/newhigh/scripts/schedule/com.redmountain.newhigh.wechat-daily.plist
```

## 📈 性能优化建议

1. **减少 Twitter 账号数量**: 如果采集时间过长，减少监控账号
2. **调整采集频率**: 编辑 plist 文件的 StartCalendarInterval
3. **启用数据库保存**: 移除 `--no-db` 参数，数据自动去重

## 🛠️ 进阶使用

### 添加新的数据源

编辑 `news_collector_x_tweet.py`,在 `XTweetNewsCollector` 类中添加新方法:

```python
def fetch_new_source(self, ...) -> List[NewsItem]:
    news_list = []
    # 实现采集逻辑
    return news_list
```

### 集成到现有流程

在现有的新闻采集流程中调用:

```python
from news_collector_x_tweet import XTweetNewsCollector

collector = XTweetNewsCollector()
news_list = collector.collect_all()
collector.save_to_database(news_list)
```

## 📝 更新日志

- **2026-03-19**: 初始集成
  - ✅ 克隆 x-tweet-fetcher 项目
  - ✅ 创建 news_collector_x_tweet.py
  - ✅ 配置 21 个监控账号
  - ✅ 设置定时任务 (Twitter 30 分钟，微信每日)
  - ✅ 测试验证 (微信公众号搜索正常)

## 🔗 相关资源

- [x-tweet-fetcher 原项目](https://github.com/ythx-101/x-tweet-fetcher)
- [x-tweet-fetcher 文档](https://github.com/ythx-101/x-tweet-fetcher/blob/main/README.md)
- [newhigh 新闻采集器](./news_collector_optimized.py)
