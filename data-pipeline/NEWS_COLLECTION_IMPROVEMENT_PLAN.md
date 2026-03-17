# 新闻采集系统改进方案

**版本**: v2.0  
**设计日期**: 2026-03-15  
**参考设计**: HAI (Human-Agent Interaction) 多渠道模式

---

## 📋 改进目标

基于当前新闻采集系统的问题，参考 HAI 设计模式，实现：

1. **多源冗余** - 同类新闻至少 3 个数据源
2. **自动故障转移** - 主数据源失败自动切换备用
3. **智能调度** - 根据数据源评分动态调整采集顺序
4. **去重合并** - 多源数据智能去重
5. **质量监控** - 实时监控数据源健康状态

---

## 🎯 当前问题分析

### 现有采集器状态 (2026-03-15)

| 采集器 | 数据源 | 状态 | 成功率 |
|--------|--------|------|--------|
| practical_news_collector.py | 证券时报 | ✅ 正常 | 100% |
| practical_news_collector.py | 东方财富快讯 | ❌ 失败 | 0% |
| practical_news_collector.py | 新浪财经 | ❌ 失败 | 0% |
| practical_news_collector.py | 中国政府网 | ❌ 失败 | 0% |
| improved_official_news_collector.py | 新华社 RSS | ❌ 失败 | 0% |
| improved_official_news_collector.py | 国务院网站 | ❌ 失败 | 0% |
| improved_official_news_collector.py | 商务部 | ⚠️ 模拟 | - |
| improved_official_news_collector.py | 住建部 | ⚠️ 模拟 | - |

### 主要问题

1. **单点故障** - 证券时报是唯一稳定数据源
2. **无故障转移** - 数据源失败后无备用方案
3. **选择器脆弱** - 网页结构变化导致采集失败
4. **缺乏监控** - 不知道数据源何时失效
5. **数据源单一** - 缺少替代数据源

---

## 🏗️ 新架构设计

### 核心类结构

```
MultiSourceNewsCollector
├── NewsSource (数据源配置)
│   ├── id: 唯一标识
│   ├── name: 显示名称
│   ├── url: 采集地址
│   ├── source_type: 类型 (WEB/RSS/API)
│   ├── priority: 优先级 (CRITICAL/HIGH/MEDIUM/LOW)
│   ├── category: 类别 (financial/policy/ministry/regulatory)
│   ├── selector: 网页选择器
│   ├── success_rate: 成功率 (动态)
│   └── avg_response_time: 平均响应时间 (动态)
│
├── NewsItem (新闻条目)
│   ├── id: 唯一 ID (MD5 去重)
│   ├── title: 标题
│   ├── content: 内容
│   ├── source: 来源
│   ├── url: 链接
│   ├── publish_time: 发布时间
│   └── category: 类别
│
└── 采集方法
    ├── fetch_web_news() - 网页采集
    ├── fetch_rss_news() - RSS 采集
    ├── collect_by_category() - 按类别采集
    ├── deduplicate_news() - 智能去重
    └── collect_all() - 全量采集
```

### 数据源优先级设计

#### 财经新闻 (financial)
| 优先级 | 数据源 | URL | 状态 |
|--------|--------|-----|------|
| CRITICAL | 证券时报 | http://news.stcn.com/ | ✅ 稳定 |
| HIGH | 东方财富快讯 | http://news.eastmoney.com/kuaixun.html | ⚠️ 待修复 |
| HIGH | 新浪财经 | https://finance.sina.com.cn/roll/index.d.html | ⚠️ 待修复 |
| MEDIUM | 财联社 | https://www.cls.cn/ | 🆕 新增 |
| MEDIUM | 界面新闻 | https://www.jiemian.com/ | 🆕 新增 |

#### 政策新闻 (policy)
| 优先级 | 数据源 | URL | 状态 |
|--------|--------|-----|------|
| CRITICAL | 中国政府网 | http://www.gov.cn/xinwen/index.htm | ⚠️ 待修复 |
| HIGH | 新华社 | http://www.news.cn/ | ⚠️ 待修复 |
| HIGH | 人民日报 | http://paper.people.com.cn/rmrb/paper/index.htm | 🆕 新增 |

#### 部委新闻 (ministry)
| 优先级 | 数据源 | URL | 状态 |
|--------|--------|-----|------|
| HIGH | 央行 | http://www.pbc.gov.cn/ | 🆕 新增 |
| MEDIUM | 商务部 | http://www.mofcom.gov.cn/ | ⚠️ 模拟 |
| MEDIUM | 发改委 | http://www.ndrc.gov.cn/ | ⚠️ 待修复 |
| MEDIUM | 住建部 | http://www.mohurd.gov.cn/ | ⚠️ 模拟 |

#### 监管新闻 (regulatory)
| 优先级 | 数据源 | URL | 状态 |
|--------|--------|-----|------|
| HIGH | 证监会 | http://www.csrc.gov.cn/ | 🆕 新增 |
| HIGH | 银保监会 | http://www.cbirc.gov.cn/ | 🆕 新增 |

---

## 🔧 实施计划

### 阶段 1: 核心功能 (本周)

#### 1.1 部署多源采集器
- [x] 创建 `multi_source_news.py`
- [ ] 测试所有数据源连接
- [ ] 更新网页选择器
- [ ] 集成到定时任务

#### 1.2 故障转移机制
- [ ] 实现数据源评分系统
- [ ] 自动切换低评分数据源
- [ ] 添加重试逻辑

#### 1.3 去重与合并
- [ ] 实现基于标题 + 时间 + 来源的去重
- [ ] 合并同一新闻的多源报道
- [ ] 保留最佳数据源版本

### 阶段 2: 监控与告警 (下周)

#### 2.1 健康监控
- [ ] 数据源成功率统计
- [ ] 响应时间监控
- [ ] 采集失败告警

#### 2.2 质量报告
- [ ] 每日数据质量报告
- [ ] 数据源评分排行榜
- [ ] 自动识别失效数据源

### 阶段 3: API 集成 (下月)

#### 3.1 第三方 API
- [ ] 聚合数据 API
- [ ] 阿里云市场 API
- [ ] 百度智能云 API

#### 3.2 混合采集
- [ ] 网页 + API 混合模式
- [ ] API 优先，网页兜底
- [ ] 成本优化策略

---

## 📊 预期效果

### 采集成功率提升

| 指标 | 当前 | 目标 | 提升 |
|------|------|------|------|
| 财经新闻 | 33% (1/3) | 100% (5/5) | +200% |
| 政策新闻 | 0% (0/3) | 100% (3/3) | +∞ |
| 部委新闻 | 0% (0/4) | 75% (3/4) | +∞ |
| 监管新闻 | 0% (0/0) | 100% (2/2) | +∞ |
| **总体** | **11%** | **90%+** | **+700%** |

### 数据质量提升

| 指标 | 当前 | 目标 |
|------|------|------|
| 真实数据占比 | 62.5% | 95%+ |
| 模拟数据占比 | 37.5% | <5% |
| 数据源数量 | 2 个 | 12+ 个 |
| 故障恢复时间 | 手动 | 自动 (<1 分钟) |

---

## 🔍 使用示例

### 基础使用

```python
from data_pipeline.collectors.multi_source_news import MultiSourceNewsCollector

# 初始化采集器
collector = MultiSourceNewsCollector()
collector.init_session()

# 采集所有类别
news_list = collector.collect_all()

# 保存到 JSON
collector.save_to_json(news_list, 'news.json')
```

### 按类别采集

```python
# 只采集财经新闻
financial_news = collector.collect_by_category('financial')

# 只采集政策新闻
policy_news = collector.collect_by_category('policy')
```

### 查看数据源状态

```python
# 查看所有数据源评分
for source in collector.sources.values():
    print(f"{source.name}: {source.get_score():.1f}分")

# 查看失败数据源
print(collector.stats['failed_sources'])
```

---

## 📝 配置文件

### 数据源配置 (news_sources.yaml)

```yaml
sources:
  financial:
    - id: stcn
      name: 证券时报
      url: http://news.stcn.com/
      priority: CRITICAL
      selector: '.news_list li'
      
    - id: eastmoney
      name: 东方财富
      url: http://news.eastmoney.com/kuaixun.html
      priority: HIGH
      selector: '.newslist li'
  
  policy:
    - id: govcn
      name: 中国政府网
      url: http://www.gov.cn/xinwen/index.htm
      priority: CRITICAL
      selector: '.news_box li'
      
    - id: xinhua
      name: 新华社
      url: http://www.news.cn/
      priority: HIGH
      selector: '.list li'

settings:
  timeout: 10
  retry_count: 3
  limit_per_source: 20
  dedup_enabled: true
```

---

## 🎯 验收标准

### 功能验收
- [ ] 12+ 数据源正常采集
- [ ] 故障自动转移 <1 分钟
- [ ] 去重准确率 >99%
- [ ] 采集速度 <30 秒 (全量)

### 质量验收
- [ ] 真实数据占比 >95%
- [ ] 数据源成功率 >80%
- [ ] 无重复新闻
- [ ] 新闻时效性 <1 小时

### 监控验收
- [ ] 数据源评分实时更新
- [ ] 失败告警及时发送
- [ ] 日报自动生成
- [ ] 历史数据可追溯

---

## 📞 维护说明

### 添加新数据源

1. 在 `_init_sources()` 中添加 NewsSource 配置
2. 设置合适的优先级和类别
3. 添加网页选择器 (如果是 WEB 类型)
4. 测试采集效果
5. 更新文档

### 修复失效数据源

1. 检查失败原因 (选择器变化？URL 变化？)
2. 更新配置中的 selector 或 url
3. 重置成功率：`source.success_rate = 1.0`
4. 重新测试

### 性能优化

1. 调整 `timeout` 和 `retry_count`
2. 限制 `limit_per_source`
3. 使用并发采集 (待实现)
4. 添加缓存机制 (待实现)

---

**文档维护者**: OpenClaw 系统  
**最后更新**: 2026-03-15  
**下次审查**: 2026-03-22
