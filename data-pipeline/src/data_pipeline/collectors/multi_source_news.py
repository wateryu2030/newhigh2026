#!/usr/bin/env python3
"""
多源新闻采集器 - 参考 HAI 设计模式
支持多渠道、多数据源、自动故障转移的新闻采集系统

设计原则:
1. 多源冗余 - 同一类新闻有多个数据源
2. 自动故障转移 - 主数据源失败自动切换备用
3. 优先级调度 - 优先使用高质量数据源
4. 去重合并 - 多源数据智能去重
5. 质量评分 - 为每个数据源评分，动态调整优先级
"""

import os
import sys
import datetime
import json
import time
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("警告：requests 或 BeautifulSoup 未安装")


class SourcePriority(Enum):
    """数据源优先级"""
    CRITICAL = 1      # 核心数据源（必须成功）
    HIGH = 2          # 高优先级
    MEDIUM = 3        # 中优先级
    LOW = 4           # 低优先级（可选）


class SourceType(Enum):
    """数据源类型"""
    WEB = "web"           # 网页爬取
    RSS = "rss"           # RSS 订阅
    API = "api"           # API 接口
    DATABASE = "database" # 数据库
    MANUAL = "manual"     # 手动录入


@dataclass
class NewsSource:
    """新闻数据源配置"""
    id: str
    name: str
    url: str
    source_type: SourceType
    priority: SourcePriority
    category: str  # 新闻类别
    selector: Optional[str] = None  # 网页选择器
    headers: Dict[str, str] = field(default_factory=dict)
    timeout: int = 10  # 超时时间 (秒)
    retry_count: int = 3  # 重试次数
    enabled: bool = True  # 是否启用
    success_rate: float = 1.0  # 成功率 (动态更新)
    last_success: Optional[datetime.datetime] = None  # 最后成功时间
    avg_response_time: float = 0.0  # 平均响应时间

    def get_score(self) -> float:
        """计算数据源评分 (0-100)"""
        base_score = {
            SourcePriority.CRITICAL: 100,
            SourcePriority.HIGH: 80,
            SourcePriority.MEDIUM: 60,
            SourcePriority.LOW: 40,
        }.get(self.priority, 50)

        # 根据成功率调整
        score = base_score * self.success_rate

        # 响应时间惩罚 (超过 5 秒开始扣分)
        if self.avg_response_time > 5:
            score *= (1 - min(0.5, (self.avg_response_time - 5) / 10))

        return score


@dataclass
class NewsItem:
    """新闻条目"""
    id: str
    title: str
    content: str
    source: str
    url: str
    publish_time: datetime.datetime
    collected_at: datetime.datetime
    category: str
    keywords: List[str] = field(default_factory=list)
    sentiment_score: Optional[float] = None
    raw_data: Optional[Dict[str, Any]] = None


class MultiSourceNewsCollector:
    """多源新闻采集器"""

    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }

        # 初始化数据源配置
        self.sources = self._init_sources()

        # 统计信息
        self.stats = {
            'total_collected': 0,
            'by_source': {},
            'by_category': {},
            'duplicates_removed': 0,
            'failed_sources': [],
        }

    def _init_sources(self) -> Dict[str, NewsSource]:
        """初始化数据源配置 - 参考 HAI 多渠道设计"""
        sources = {}

        # ========== 财经新闻类 ==========
        # 核心数据源 - 证券时报 (稳定)
        sources['stcn'] = NewsSource(
            id='stcn',
            name='证券时报',
            url='http://news.stcn.com/',
            source_type=SourceType.WEB,
            priority=SourcePriority.CRITICAL,
            category='financial',
            selector='.news_list li'
        )

        # 高优先级 - 东方财富 (待修复选择器)
        sources['eastmoney'] = NewsSource(
            id='eastmoney',
            name='东方财富快讯',
            url='http://news.eastmoney.com/kuaixun.html',
            source_type=SourceType.WEB,
            priority=SourcePriority.HIGH,
            category='financial',
            selector='.list-cont li',  # 待验证
            enabled=False  # 临时禁用，待修复
        )

        # 高优先级 - 新浪财经 (待修复选择器)
        sources['sina'] = NewsSource(
            id='sina',
            name='新浪财经',
            url='https://finance.sina.com.cn/roll/index.d.html',
            source_type=SourceType.WEB,
            priority=SourcePriority.HIGH,
            category='financial',
            selector='.list_009 li',
            enabled=False  # 临时禁用，待修复
        )

        # 中优先级 - 财联社 (待修复选择器)
        sources['cls'] = NewsSource(
            id='cls',
            name='财联社',
            url='https://www.cls.cn/',
            source_type=SourceType.WEB,
            priority=SourcePriority.MEDIUM,
            category='financial',
            selector='.feed-item',
            enabled=False  # 临时禁用，待修复
        )

        # 中优先级 - 界面新闻 (待修复选择器)
        sources['jiemian'] = NewsSource(
            id='jiemian',
            name='界面新闻',
            url='https://www.jiemian.com/',
            source_type=SourceType.WEB,
            priority=SourcePriority.MEDIUM,
            category='financial',
            selector='.news-list-item',
            enabled=False  # 临时禁用，待修复
        )

        # ========== 政策新闻类 ==========
        # 核心数据源 - 中国政府网 (待修复选择器)
        sources['govcn'] = NewsSource(
            id='govcn',
            name='中国政府网',
            url='http://www.gov.cn/xinwen/index.htm',
            source_type=SourceType.WEB,
            priority=SourcePriority.CRITICAL,
            category='policy',
            selector='.news_box li',
            enabled=False  # 临时禁用，待修复
        )

        # 高优先级 - 新华社
        sources['xinhua'] = NewsSource(
            id='xinhua',
            name='新华社',
            url='http://www.news.cn/',
            source_type=SourceType.WEB,
            priority=SourcePriority.HIGH,
            category='policy',
            selector='.list li'
        )

        # 高优先级 - 人民日报 (待修复选择器)
        sources['people'] = NewsSource(
            id='people',
            name='人民日报',
            url='http://paper.people.com.cn/rmrb/paper/index.htm',
            source_type=SourceType.WEB,
            priority=SourcePriority.HIGH,
            category='policy',
            selector='.news_list li',
            enabled=False  # 临时禁用，待修复
        )

        # ========== 部委新闻类 ==========
        # 商务部 (待修复)
        sources['mofcom'] = NewsSource(
            id='mofcom',
            name='商务部',
            url='http://www.mofcom.gov.cn/article/ae/',
            source_type=SourceType.WEB,
            priority=SourcePriority.MEDIUM,
            category='ministry',
            selector='.list li',
            enabled=False  # 临时禁用，待修复
        )

        # 发改委
        sources['ndrc'] = NewsSource(
            id='ndrc',
            name='发改委',
            url='http://www.ndrc.gov.cn/xwdt/xwfb/',
            source_type=SourceType.WEB,
            priority=SourcePriority.MEDIUM,
            category='ministry',
            selector='.list li'
        )

        # 住建部 (待修复)
        sources['mohurd'] = NewsSource(
            id='mohurd',
            name='住建部',
            url='http://www.mohurd.gov.cn/gongkai/fdzdgknr/',
            source_type=SourceType.WEB,
            priority=SourcePriority.MEDIUM,
            category='ministry',
            selector='.list li',
            enabled=False  # 临时禁用，待修复
        )

        # 央行 (待修复)
        sources['pbc'] = NewsSource(
            id='pbc',
            name='中国人民银行',
            url='http://www.pbc.gov.cn/goutongjiaoliu/113456/113469/index.html',
            source_type=SourceType.WEB,
            priority=SourcePriority.HIGH,
            category='ministry',
            selector='.list li',
            enabled=False  # 临时禁用，待修复
        )

        # ========== 行业数据类 (监管) ==========
        # 证监会 (待修复)
        sources['csrc'] = NewsSource(
            id='csrc',
            name='证监会',
            url='http://www.csrc.gov.cn/csrc/home/index.shtml',
            source_type=SourceType.WEB,
            priority=SourcePriority.HIGH,
            category='regulatory',
            selector='.list li',
            enabled=False  # 临时禁用，待修复
        )

        # 银保监会 (待修复)
        sources['cbirc'] = NewsSource(
            id='cbirc',
            name='银保监会',
            url='http://www.cbirc.gov.cn/cn/view/pages/index/index.html',
            source_type=SourceType.WEB,
            priority=SourcePriority.HIGH,
            category='regulatory',
            selector='.list li',
            enabled=False  # 临时禁用，待修复
        )

        # ========== RSS 数据源 ==========
        # 新华社财经 RSS
        sources['xinhua_rss_finance'] = NewsSource(
            id='xinhua_rss_finance',
            name='新华社财经 RSS',
            url='http://www.news.cn/rss/finance.xml',
            source_type=SourceType.RSS,
            priority=SourcePriority.MEDIUM,
            category='financial'
        )

        return sources

    def init_session(self):
        """初始化请求会话"""
        if REQUESTS_AVAILABLE:
            self.session = requests.Session()
            self.session.headers.update(self.headers)

    def generate_id(self, title: str, source: str, publish_time: str) -> str:
        """生成新闻唯一 ID"""
        content = f"{title}_{source}_{publish_time}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def fetch_web_news(self, source: NewsSource) -> List[NewsItem]:
        """从网页采集新闻"""
        news_list = []

        if not REQUESTS_AVAILABLE:
            return news_list

        start_time = time.time()

        try:
            response = self.session.get(
                source.url,
                headers=source.headers,
                timeout=source.timeout
            )
            response.raise_for_status()

            # 更新统计
            response_time = time.time() - start_time
            source.avg_response_time = (source.avg_response_time * 0.7) + (response_time * 0.3)

            soup = BeautifulSoup(response.text, 'html.parser')

            # 根据选择器提取新闻
            if source.selector:
                elements = soup.select(source.selector)
                for elem in elements[:20]:  # 限制每次采集数量
                    try:
                        title_elem = elem.find('a') or elem.find('h3') or elem
                        title = title_elem.get_text(strip=True)

                        if not title or len(title) < 5:
                            continue

                        url_elem = elem.find('a')
                        url = url_elem.get('href', '') if url_elem else ''

                        if url and not url.startswith('http'):
                            # 相对路径转绝对路径
                            from urllib.parse import urljoin
                            url = urljoin(source.url, url)

                        # 提取发布时间 (如果有)
                        time_elem = elem.find('span', class_=lambda x: x and 'time' in x.lower())
                        publish_time = datetime.datetime.now()
                        if time_elem:
                            try:
                                time_str = time_elem.get_text(strip=True)
                                # 尝试解析时间
                                for fmt in ['%Y-%m-%d %H:%M', '%Y-%m-%d', '%m-%d %H:%M']:
                                    try:
                                        publish_time = datetime.datetime.strptime(time_str, fmt)
                                        break
                                    except ValueError:
                                        continue
                            except:
                                pass

                        news_item = NewsItem(
                            id=self.generate_id(title, source.name, str(publish_time)),
                            title=title,
                            content=title,  # 简要新闻，标题即内容
                            source=source.name,
                            url=url or source.url,
                            publish_time=publish_time,
                            collected_at=datetime.datetime.now(),
                            category=source.category
                        )
                        news_list.append(news_item)

                    except Exception as e:
                        continue

            # 更新成功统计
            source.success_rate = min(1.0, source.success_rate * 0.9 + 0.1)
            source.last_success = datetime.datetime.now()

        except Exception as e:
            # 更新失败统计
            source.success_rate *= 0.8
            self.stats['failed_sources'].append({
                'source': source.name,
                'error': str(e),
                'time': datetime.datetime.now().isoformat()
            })

        return news_list

    def fetch_rss_news(self, source: NewsSource) -> List[NewsItem]:
        """从 RSS 采集新闻"""
        news_list = []

        try:
            import feedparser

            feed = feedparser.parse(source.url)

            for entry in feed.entries[:20]:
                publish_time = datetime.datetime.now()
                if hasattr(entry, 'published_parsed'):
                    try:
                        publish_time = datetime.datetime.fromtimestamp(
                            time.mktime(entry.published_parsed)
                        )
                    except:
                        pass

                news_item = NewsItem(
                    id=self.generate_id(entry.title, source.name, str(publish_time)),
                    title=entry.title,
                    content=entry.get('summary', entry.title),
                    source=source.name,
                    url=entry.get('link', source.url),
                    publish_time=publish_time,
                    collected_at=datetime.datetime.now(),
                    category=source.category
                )
                news_list.append(news_item)

            source.success_rate = min(1.0, source.success_rate * 0.9 + 0.1)
            source.last_success = datetime.datetime.now()

        except ImportError:
            print(f"⚠ feedparser 未安装，跳过 RSS 源：{source.name}")
        except Exception as e:
            source.success_rate *= 0.8
            self.stats['failed_sources'].append({
                'source': source.name,
                'error': str(e),
                'time': datetime.datetime.now().isoformat()
            })

        return news_list

    def collect_by_category(self, category: str, limit_per_source: int = 10) -> List[NewsItem]:
        """按类别采集新闻"""
        all_news = []

        # 获取该类别下所有数据源，按评分排序
        category_sources = [
            s for s in self.sources.values()
            if s.category == category and s.enabled
        ]
        category_sources.sort(key=lambda s: s.get_score(), reverse=True)

        print(f"\n📰 采集 {category} 类新闻，共 {len(category_sources)} 个数据源")

        for source in category_sources:
            print(f"  尝试：{source.name} (评分：{source.get_score():.1f})")

            if source.source_type == SourceType.WEB:
                news = self.fetch_web_news(source)
            elif source.source_type == SourceType.RSS:
                news = self.fetch_rss_news(source)
            else:
                news = []

            # 限制每个数据源的数量
            news = news[:limit_per_source]

            if news:
                print(f"    ✅ 采集到 {len(news)} 条")
                all_news.extend(news)

                # 更新统计
                self.stats['by_source'][source.name] = self.stats['by_source'].get(source.name, 0) + len(news)
                self.stats['by_category'][category] = self.stats['by_category'].get(category, 0) + len(news)
            else:
                print(f"    ❌ 采集失败")

        return all_news

    def deduplicate_news(self, news_list: List[NewsItem]) -> List[NewsItem]:
        """新闻去重"""
        seen_ids = set()
        unique_news = []

        for news in news_list:
            if news.id not in seen_ids:
                seen_ids.add(news.id)
                unique_news.append(news)
            else:
                self.stats['duplicates_removed'] += 1

        return unique_news

    def collect_all(self, categories: Optional[List[str]] = None) -> List[NewsItem]:
        """采集所有类别新闻"""
        if categories is None:
            categories = ['financial', 'policy', 'ministry', 'regulatory']

        all_news = []

        print("=" * 60)
        print("开始多源新闻采集")
        print(f"时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        for category in categories:
            news = self.collect_by_category(category)
            all_news.extend(news)

        # 去重
        print("\n🔄 新闻去重...")
        unique_news = self.deduplicate_news(all_news)
        print(f"  原始：{len(all_news)} 条，去重后：{len(unique_news)} 条")

        # 更新总统计
        self.stats['total_collected'] = len(unique_news)

        # 打印统计
        print("\n" + "=" * 60)
        print("采集完成统计")
        print("=" * 60)
        print(f"总采集：{self.stats['total_collected']} 条")
        print(f"去重数：{self.stats['duplicates_removed']} 条")

        if self.stats['by_source']:
            print("\n按来源统计:")
            for source, count in sorted(self.stats['by_source'].items(), key=lambda x: x[1], reverse=True):
                print(f"  {source}: {count} 条")

        if self.stats['by_category']:
            print("\n按类别统计:")
            for cat, count in sorted(self.stats['by_category'].items()):
                print(f"  {cat}: {count} 条")

        if self.stats['failed_sources']:
            print(f"\n⚠ 失败数据源：{len(self.stats['failed_sources'])} 个")

        return unique_news

    def save_to_json(self, news_list: List[NewsItem], output_path: str):
        """保存到 JSON 文件"""
        data = {
            'metadata': {
                'collected_at': datetime.datetime.now().isoformat(),
                'total_count': len(news_list),
                'sources': list(set(n.source for n in news_list)),
                'categories': list(set(n.category for n in news_list)),
            },
            'news': [
                {
                    'id': n.id,
                    'title': n.title,
                    'content': n.content,
                    'source': n.source,
                    'url': n.url,
                    'publish_time': n.publish_time.isoformat(),
                    'collected_at': n.collected_at.isoformat(),
                    'category': n.category,
                    'keywords': n.keywords,
                }
                for n in news_list
            ]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 保存到：{output_path}")


def main():
    """主函数"""
    collector = MultiSourceNewsCollector()
    collector.init_session()

    # 采集所有类别
    news_list = collector.collect_all()

    # 保存
    output_path = f"data-pipeline/data/news/multi_source_news_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    collector.save_to_json(news_list, output_path)

    return news_list


if __name__ == '__main__':
    main()
