#!/usr/bin/env python3
"""
X-Twitter 和微信公众号新闻采集器
集成 x-tweet-fetcher 项目，增强舆情采集能力

功能:
- 监控指定 Twitter 账号的推文
- 搜索微信公众号文章
- 输出格式对齐 news_collector_optimized.py
- 支持定时任务调用
"""

import os
import sys
import datetime
import json
import hashlib
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入 x-tweet-fetcher 模块
x_tweet_path = project_root / "tools" / "x-tweet-fetcher" / "scripts"
sys.path.insert(0, str(x_tweet_path))

try:
    from fetch_tweet import fetch_tweet
    from sogou_wechat import sogou_wechat_search
    X_TWEET_AVAILABLE = True
except ImportError as e:
    X_TWEET_AVAILABLE = False
    print(f"警告：x-tweet-fetcher 未正确安装：{e}")

try:
    from data_pipeline.storage.duckdb_manager import get_conn, ensure_tables
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False
    print("警告：duckdb_manager 不可用，数据将保存到文件")


@dataclass
class NewsItem:
    """新闻数据结构 (与 news_collector_optimized.py 对齐)"""
    id: str
    title: str
    content: str
    source: str
    department: str
    url: str
    publish_time: str
    keywords: List[str]
    collected_at: str
    sentiment_score: Optional[float] = None


class XTweetNewsCollector:
    """X-Twitter 和微信公众号新闻采集器"""
    
    def __init__(self, accounts_file: str = None):
        """
        初始化采集器
        
        Args:
            accounts_file: Twitter 监控账号列表文件路径
        """
        self.accounts = []
        self.load_accounts(accounts_file)
    
    def load_accounts(self, accounts_file: str = None):
        """加载 Twitter 监控账号列表"""
        if accounts_file is None:
            # 默认路径
            accounts_file = project_root / "x_tweet_accounts.txt"
        
        if Path(accounts_file).exists():
            with open(accounts_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # 移除 @ 符号
                        username = line.lstrip('@')
                        self.accounts.append(username)
            print(f"已加载 {len(self.accounts)} 个 Twitter 监控账号")
        else:
            # 使用默认账号列表
            self.accounts = [
                'elonmusk',
                'OpenAI',
                'AnthropicAI',
                'FinancialTimes',
                'BloombergNews',
                'Reuters',
                'WSJ',
                'CNBC',
            ]
            print(f"使用默认 {len(self.accounts)} 个 Twitter 监控账号")
    
    def generate_id(self, title: str, source: str, publish_time: str) -> str:
        """生成新闻 ID（去重）"""
        content = f"{title}_{source}_{publish_time}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def fetch_twitter_timeline(self, username: str, limit: int = 10) -> List[NewsItem]:
        """
        获取指定用户的推文时间线
        
        Args:
            username: Twitter 用户名 (不含 @)
            limit: 最大推文数量
            
        Returns:
            NewsItem 列表
        """
        news_list = []
        
        if not X_TWEET_AVAILABLE:
            return news_list
        
        try:
            # 调用 x-tweet-fetcher 的 fetch_tweet 模块
            # 注意：fetch_tweet 主要用于单条推文，时间线需要其他方法
            # 这里使用 x_discover 模块进行关键词搜索
            from x_discover import discover_tweets
            
            result = discover_tweets([username], max_results=limit)
            
            if result and 'tweets' in result:
                for tweet in result['tweets']:
                    publish_time = tweet.get('created_at', '')
                    text = tweet.get('text', '')
                    
                    if text:
                        news_list.append(NewsItem(
                            id=self.generate_id(text[:50], f'Twitter:@{username}', publish_time),
                            title=text[:100],
                            content=text,
                            source=f'Twitter:@{username}',
                            department='x_tweet',
                            url=f"https://x.com/{username}/status/{tweet.get('id', '')}",
                            publish_time=publish_time,
                            keywords=[],
                            collected_at=datetime.datetime.now().isoformat()
                        ))
            
            print(f"  Twitter @{username}: {len(news_list)} 条推文")
            
        except Exception as e:
            print(f"  Twitter @{username} 采集失败：{e}")
        
        return news_list
    
    def fetch_wechat_search(self, keyword: str, limit: int = 10) -> List[NewsItem]:
        """
        搜索微信公众号文章
        
        Args:
            keyword: 搜索关键词
            limit: 最大结果数量
            
        Returns:
            NewsItem 列表
        """
        news_list = []
        
        if not X_TWEET_AVAILABLE:
            return news_list
        
        try:
            results = sogou_wechat_search(keyword, max_results=limit)
            
            if results:
                for article in results:
                    title = article.get('title', '')
                    url = article.get('url', '')
                    date = article.get('date', '')
                    snippet = article.get('snippet', '')
                    
                    if title:
                        news_list.append(NewsItem(
                            id=self.generate_id(title, '微信公众号', date),
                            title=title,
                            content=snippet if snippet else title,
                            source='微信公众号',
                            department='wechat',
                            url=url,
                            publish_time=date,
                            keywords=[keyword],
                            collected_at=datetime.datetime.now().isoformat()
                        ))
            
            print(f"  微信公众号搜索 '{keyword}': {len(news_list)} 篇文章")
            
        except Exception as e:
            print(f"  微信公众号搜索失败：{e}")
        
        return news_list
    
    def collect_all(self, keywords: List[str] = None, twitter_limit: int = 5, wechat_limit: int = 10) -> List[NewsItem]:
        """
        执行完整采集
        
        Args:
            keywords: 微信公众号搜索关键词列表
            twitter_limit: 每个 Twitter 账号获取的推文数量
            wechat_limit: 每个关键词获取的文章数量
            
        Returns:
            所有采集的新闻列表
        """
        all_news = []
        
        print("\n=== 开始 X-Twitter 和微信公众号采集 ===")
        
        # 1. 采集 Twitter 账号
        print("\n【Twitter 监控】")
        for username in self.accounts[:10]:  # 限制账号数量避免超时
            news = self.fetch_twitter_timeline(username, limit=twitter_limit)
            all_news.extend(news)
        
        # 2. 采集微信公众号
        print("\n【微信公众号搜索】")
        if keywords is None:
            keywords = ['量化交易', 'AI Agent', '金融科技', '宏观经济']
        
        for keyword in keywords:
            news = self.fetch_wechat_search(keyword, limit=wechat_limit)
            all_news.extend(news)
        
        print(f"\n总计采集：{len(all_news)} 条新闻")
        
        return all_news
    
    def save_to_database(self, news_list: List[NewsItem]) -> int:
        """保存新闻到数据库"""
        if not news_list:
            return 0
        
        if not DUCKDB_AVAILABLE:
            print("数据库不可用，跳过保存")
            return 0
        
        try:
            conn = get_conn(read_only=False)
            ensure_tables(conn)
            
            import pandas as pd
            df = pd.DataFrame([asdict(n) for n in news_list])
            
            conn.register('tmp_news', df)
            
            result = conn.execute("""
                INSERT INTO news_items 
                (symbol, source_site, source, title, content, url, publish_time, sentiment_score)
                SELECT 
                    '' as symbol,
                    department as source_site,
                    source,
                    title,
                    content,
                    url,
                    publish_time,
                    sentiment_score
                FROM tmp_news
                WHERE NOT EXISTS (
                    SELECT 1 FROM news_items n 
                    WHERE n.title = tmp_news.title 
                    AND n.publish_time = tmp_news.publish_time
                )
            """)
            
            saved_count = result.rowcount
            print(f"  保存到数据库：{saved_count} 条")
            
            conn.close()
            return saved_count
            
        except Exception as e:
            print(f"  数据库保存失败：{e}")
            return 0
    
    def save_to_json(self, news_list: List[NewsItem], output_file: str = None):
        """保存新闻到 JSON 文件"""
        if not output_file:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"x_tweet_news_{timestamp}.json"
        
        output_path = project_root / output_file
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump([asdict(n) for n in news_list], f, ensure_ascii=False, indent=2)
        
        print(f"  保存到 JSON: {output_path}")
        return str(output_path)


def main():
    """主函数 - 支持命令行调用"""
    import argparse
    
    parser = argparse.ArgumentParser(description='X-Twitter 和微信公众号新闻采集器')
    parser.add_argument('--accounts', '-a', type=str, help='Twitter 账号列表文件')
    parser.add_argument('--keywords', '-k', type=str, nargs='+', 
                        default=['量化交易', 'AI Agent', '金融科技'],
                        help='微信公众号搜索关键词')
    parser.add_argument('--twitter-limit', type=int, default=5, help='每个 Twitter 账号获取的推文数')
    parser.add_argument('--wechat-limit', type=int, default=10, help='每个关键词获取的文章数')
    parser.add_argument('--output', '-o', type=str, help='输出 JSON 文件路径')
    parser.add_argument('--no-db', action='store_true', help='不保存到数据库')
    
    args = parser.parse_args()
    
    collector = XTweetNewsCollector(accounts_file=args.accounts)
    
    # 执行采集
    news_list = collector.collect_all(
        keywords=args.keywords,
        twitter_limit=args.twitter_limit,
        wechat_limit=args.wechat_limit
    )
    
    # 保存
    if not args.no_db:
        collector.save_to_database(news_list)
    
    collector.save_to_json(news_list, args.output)
    
    print("\n✅ 采集完成!")
    return news_list


if __name__ == '__main__':
    main()
