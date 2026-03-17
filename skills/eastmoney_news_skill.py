# -*- coding: utf-8 -*-
"""
OpenClaw 东方财富网新闻采集 Skill — 红山量化平台集成
功能：采集东方财富网新闻、快讯、研报等财经资讯
依赖：requests、beautifulsoup4、feedparser
"""

from __future__ import annotations

import os
import json
import hashlib
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass, asdict

# 可选：在独立运行时加载 .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("⚠ 警告：requests 或 BeautifulSoup 未安装，东财 skill 不可用")

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False
    print("⚠ 警告：feedparser 未安装，RSS 采集不可用")


# 缓存配置
CACHE_DIR = Path("/tmp/eastmoney_skill_cache")
CACHE_TTL = 1800  # 30 分钟缓存（新闻更新快）


@dataclass
class NewsItem:
    """新闻条目"""
    id: str
    title: str
    content: str
    source: str
    url: str
    publish_time: str
    collected_at: str
    category: str
    keywords: List[str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _get_cache_key(func_name: str, *args, **kwargs) -> str:
    """生成缓存键"""
    key_str = f"{func_name}:{json.dumps(args, sort_keys=True)}:{json.dumps(kwargs, sort_keys=True)}"
    return hashlib.md5(key_str.encode()).hexdigest()


def _get_from_cache(cache_key: str) -> Optional[Any]:
    """从缓存获取数据"""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = CACHE_DIR / f"{cache_key}.json"
        if cache_file.exists():
            mtime = cache_file.stat().st_mtime
            if datetime.now().timestamp() - mtime < CACHE_TTL:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
    except Exception:
        pass
    return None


def _save_to_cache(cache_key: str, data: Any) -> None:
    """保存数据到缓存"""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = CACHE_DIR / f"{cache_key}.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, default=str)
    except Exception:
        pass


def _with_cache(func):
    """缓存装饰器（跳过 self 参数）"""
    def wrapper(*args, **kwargs):
        if kwargs.get("no_cache", False):
            return func(*args, **kwargs)
        
        # 跳过第一个参数（self）用于缓存键生成
        cache_args = args[1:] if args else ()
        cache_key = _get_cache_key(
            func.__name__, *cache_args, **{k: v for k, v in kwargs.items() if k != "no_cache"}
        )
        cached = _get_from_cache(cache_key)
        if cached is not None:
            return cached
        
        result = func(*args, **kwargs)
        if result and not isinstance(result, dict) or "error" not in result:
            _save_to_cache(cache_key, result)
        return result
    
    return wrapper


class EastMoneyNewsSkill:
    """东方财富网新闻采集 Skill"""
    
    def __init__(self) -> None:
        self.name = "eastmoney_news_skill"
        self.version = "1.0.0"
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://www.eastmoney.com/'
        }
        
        # 数据源配置
        self.sources = {
            'caifuhao': {
                'name': '东方财富号',
                'url': 'https://caifuhao.eastmoney.com/',
                'type': 'web',
                'selector': '.article-list .article-item',
                'category': 'financial'
            },
            'kuaixun_rss': {
                'name': '东方财富快讯 RSS',
                'url': 'https://kuaixun.eastmoney.com/rss.xml',
                'type': 'rss',
                'category': 'financial'
            },
            'news_rss': {
                'name': '东方财富新闻 RSS',
                'url': 'https://www.eastmoney.com/rss.xml',
                'type': 'rss',
                'category': 'financial'
            }
        }
        
        self.stats = {
            'total_collected': 0,
            'by_source': {},
            'last_update': None
        }
        
        if REQUESTS_AVAILABLE:
            self.init_session()
    
    def init_session(self):
        """初始化请求会话"""
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def generate_id(self, title: str, source: str, publish_time: str) -> str:
        """生成新闻唯一 ID"""
        content = f"{title}_{source}_{publish_time}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    @_with_cache
    def fetch_caifuhao_news(self, limit: int = 20) -> List[NewsItem]:
        """采集东方财富号文章"""
        news_list = []
        
        if not REQUESTS_AVAILABLE:
            return news_list
        
        try:
            response = self.session.get(
                self.sources['caifuhao']['url'],
                timeout=10
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 基于实际页面结构的多种选择器
            selectors = [
                'li a[href*="/news/"]',  # 关注 feed 中的新闻链接
                'a[href*="/news/"]',     # 所有新闻链接
                '[class*="feed"] a',     # feed 类中的链接
                '.article-list a',
                '[class*="article"] a',
            ]
            
            seen_urls = set()
            elements = []
            
            for selector in selectors:
                elements = soup.select(selector)
                if len(elements) >= limit:
                    break
            
            for elem in elements[:limit * 2]:  # 多取一些用于过滤
                try:
                    url = elem.get('href', '')
                    if not url or url in seen_urls:
                        continue
                    
                    # 只采集东财号新闻
                    if '/news/' not in url and 'caifuhao' not in url:
                        continue
                    
                    seen_urls.add(url)
                    
                    title = elem.get_text(strip=True)
                    if not title or len(title) < 5 or len(title) > 200:
                        continue
                    
                    # 过滤无效标题
                    if any(kw in title for kw in ['登录', '注册', '关注', '首页', 'APP']):
                        continue
                    
                    # 标准化 URL
                    if url.startswith('//'):
                        url = 'https:' + url
                    elif not url.startswith('http'):
                        url = f"https://caifuhao.eastmoney.com{url}"
                    
                    # 提取时间（从 URL 或页面）
                    publish_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    # 尝试从 URL 提取日期：/news/20260316221321998070900
                    import re
                    date_match = re.search(r'/news/(\d{4}\d{2}\d{2})', url)
                    if date_match:
                        date_str = date_match.group(1)
                        try:
                            parsed = datetime.strptime(date_str, '%Y%m%d')
                            publish_time = parsed.strftime('%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            pass
                    
                    news_item = NewsItem(
                        id=self.generate_id(title, '东方财富号', publish_time),
                        title=title,
                        content=title,  # 简要新闻
                        source='东方财富号',
                        url=url,
                        publish_time=publish_time,
                        collected_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        category='financial'
                    )
                    news_list.append(news_item)
                    
                    if len(news_list) >= limit:
                        break
                    
                except Exception:
                    continue
            
            self.stats['by_source']['caifuhao'] = len(news_list)
            
        except Exception as e:
            print(f"❌ 采集东方财富号失败：{e}")
        
        return news_list
    
    @_with_cache
    def fetch_rss_news(self, source_key: str, limit: int = 20) -> List[NewsItem]:
        """从 RSS 源采集新闻"""
        news_list = []
        
        if not FEEDPARSER_AVAILABLE:
            return news_list
        
        source = self.sources.get(source_key)
        if not source or source['type'] != 'rss':
            return news_list
        
        try:
            feed = feedparser.parse(source['url'])
            
            for entry in feed.entries[:limit]:
                publish_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        publish_time = datetime.fromtimestamp(
                            time.mktime(entry.published_parsed)
                        ).strftime('%Y-%m-%d %H:%M:%S')
                    except Exception:
                        pass
                
                news_item = NewsItem(
                    id=self.generate_id(entry.title, source['name'], publish_time),
                    title=entry.title,
                    content=entry.get('summary', entry.title),
                    source=source['name'],
                    url=entry.get('link', source['url']),
                    publish_time=publish_time,
                    collected_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    category=source['category']
                )
                news_list.append(news_item)
            
            self.stats['by_source'][source_key] = len(news_list)
            
        except Exception as e:
            print(f"❌ 采集 RSS {source['name']} 失败：{e}")
        
        return news_list
    
    def collect_with_browser(self, limit: int = 20) -> List[NewsItem]:
        """使用浏览器工具采集（用于动态内容）"""
        # 这个方法需要被外部调用 browser 工具
        # 返回格式与其他方法一致
        news_list = []
        print("  ⚠ 浏览器采集需要外部调用 browser 工具")
        return news_list
    
    def collect_all(self, limit_per_source: int = 20, use_browser: bool = False) -> Dict[str, Any]:
        """采集所有数据源"""
        all_news = []
        
        print(f"\n📰 开始采集东方财富网新闻...")
        
        if use_browser:
            # 使用浏览器采集动态内容
            browser_news = self.collect_with_browser(limit=limit_per_source)
            all_news.extend(browser_news)
            print(f"  ✅ 浏览器采集：{len(browser_news)} 条")
        else:
            # 采集东财号（静态）
            caifuhao_news = self.fetch_caifuhao_news(limit=limit_per_source)
            if caifuhao_news:
                print(f"  ✅ 东方财富号：{len(caifuhao_news)} 条")
                all_news.extend(caifuhao_news)
            
            # 采集 RSS
            for rss_key in ['kuaixun_rss', 'news_rss']:
                rss_news = self.fetch_rss_news(rss_key, limit=limit_per_source)
                if rss_news:
                    print(f"  ✅ {self.sources[rss_key]['name']}: {len(rss_news)} 条")
                    all_news.extend(rss_news)
        
        # 去重
        seen_ids = set()
        unique_news = []
        for news in all_news:
            if news.id not in seen_ids:
                seen_ids.add(news.id)
                unique_news.append(news)
        
        duplicates_removed = len(all_news) - len(unique_news)
        
        self.stats['total_collected'] = len(unique_news)
        self.stats['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        result_msg = f"📊 采集完成：共 {len(unique_news)} 条"
        if duplicates_removed > 0:
            result_msg += f"（去重 {duplicates_removed} 条）"
        print(result_msg)
        
        return {
            'success': True,
            'count': len(unique_news),
            'news': [n.to_dict() for n in unique_news],
            'stats': self.stats
        }
    
    def to_multi_source_format(self) -> Dict[str, Any]:
        """转换为 multi_source_news.py 兼容格式"""
        return {
            'eastmoney_caifuhao': {
                'id': 'eastmoney_caifuhao',
                'name': '东方财富号',
                'url': 'https://caifuhao.eastmoney.com/',
                'source_type': 'WEB',
                'priority': 'HIGH',
                'category': 'financial',
                'enabled': True
            },
            'eastmoney_kuaixun_rss': {
                'id': 'eastmoney_kuaixun_rss',
                'name': '东方财富快讯 RSS',
                'url': 'https://kuaixun.eastmoney.com/rss.xml',
                'source_type': 'RSS',
                'priority': 'MEDIUM',
                'category': 'financial',
                'enabled': True
            }
        }


# CLI 入口
if __name__ == '__main__':
    skill = EastMoneyNewsSkill()
    result = skill.collect_all(limit_per_source=20)
    
    if result['success']:
        print(f"\n✅ 采集成功！")
        print(f"   总数：{result['count']} 条")
        print(f"   时间：{result['stats']['last_update']}")
        
        # 显示前 5 条
        print(f"\n📰 最新新闻：")
        for i, news in enumerate(result['news'][:5], 1):
            print(f"   {i}. {news['title']}")
            print(f"      来源：{news['source']} | 时间：{news['publish_time']}")
    else:
        print(f"\n❌ 采集失败")
