#!/usr/bin/env python3
"""
实用版新闻采集器
专注于实际可用的数据源，提供有价值的新闻数据
"""

import os
import sys
import datetime
import json
import time
import hashlib
import re
from typing import List, Dict, Any
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("警告: requests或BeautifulSoup未安装")
    print("安装命令: pip install requests beautifulsoup4")


class PracticalNewsCollector:
    """实用版新闻采集器"""
    
    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        
        # 实际可用的数据源
        self.data_sources = {
            'financial_news': {
                'name': '财经新闻',
                'sources': [
                    {
                        'name': '东方财富快讯',
                        'url': 'http://news.eastmoney.com/kuaixun.html',
                        'type': 'web',
                        'selector': '.newslist li'
                    },
                    {
                        'name': '新浪财经',
                        'url': 'https://finance.sina.com.cn/roll/index.d.html',
                        'type': 'web',
                        'selector': '.list_009 li'
                    }
                ]
            },
            'policy_news': {
                'name': '政策新闻',
                'sources': [
                    {
                        'name': '中国政府网',
                        'url': 'http://www.gov.cn/xinwen/index.htm',
                        'type': 'web',
                        'selector': '.news_box li'
                    }
                ]
            },
            'industry_news': {
                'name': '行业新闻',
                'sources': [
                    {
                        'name': '证券时报',
                        'url': 'http://news.stcn.com/',
                        'type': 'web',
                        'selector': '.news_list li'
                    }
                ]
            }
        }
    
    def init_session(self):
        """初始化请求会话"""
        if REQUESTS_AVAILABLE:
            self.session = requests.Session()
            self.session.headers.update(self.headers)
    
    def generate_id(self, title: str, source: str, publish_time: str) -> str:
        """生成新闻ID"""
        content = f"{title}_{source}_{publish_time}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def fetch_web_news(self, source_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从网页采集新闻"""
        news_list = []
        
        if not REQUESTS_AVAILABLE:
            return news_list
        
        try:
            print(f"采集 {source_config['name']}: {source_config['url']}")
            
            response = self.session.get(
                source_config['url'], 
                timeout=15,
                verify=False  # 有些网站证书可能有问题
            )
            response.raise_for_status()
            
            # 解析HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 使用配置的选择器
            selector = source_config.get('selector', 'li, article, .news-item')
            news_items = soup.select(selector)[:15]  # 只取前15条
            
            for item in news_items:
                try:
                    # 提取标题
                    title_elem = item.select_one('a, h3, h4, .title, .tit')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    if not title or len(title) < 5:
                        continue
                    
                    # 提取链接
                    link_elem = item.select_one('a[href]')
                    url = link_elem.get('href') if link_elem else ''
                    if url and not url.startswith('http'):
                        # 处理相对链接
                        base_url = source_config['url']
                        if url.startswith('/'):
                            from urllib.parse import urlparse
                            parsed = urlparse(base_url)
                            url = f"{parsed.scheme}://{parsed.netloc}{url}"
                        else:
                            url = f"{base_url.rstrip('/')}/{url}"
                    
                    # 提取时间
                    time_elem = item.select_one('.time, .date, time, .pubtime')
                    publish_time = time_elem.get_text(strip=True) if time_elem else ''
                    
                    # 如果没有时间，使用当前时间
                    if not publish_time:
                        publish_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        # 尝试解析时间格式
                        try:
                            # 简化时间解析
                            if '今天' in publish_time:
                                publish_time = datetime.datetime.now().strftime('%Y-%m-%d') + ' ' + re.search(r'\d{2}:\d{2}', publish_time).group()
                            elif '昨天' in publish_time:
                                yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
                                publish_time = yesterday.strftime('%Y-%m-%d') + ' ' + re.search(r'\d{2}:\d{2}', publish_time).group()
                        except:
                            publish_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # 提取内容摘要
                    content_elem = item.select_one('.summary, .content, p, .intro')
                    content = content_elem.get_text(strip=True) if content_elem else title[:100]
                    
                    # 生成新闻项
                    news_item = {
                        'id': self.generate_id(title, source_config['name'], publish_time),
                        'title': title,
                        'source': source_config['name'],
                        'category': source_config.get('category', 'general'),
                        'publish_time': publish_time,
                        'content': content[:300],  # 限制长度
                        'url': url,
                        'keywords': self.extract_keywords(title),
                        'collected_at': datetime.datetime.now().isoformat(),
                        'data_source': source_config['url']
                    }
                    
                    news_list.append(news_item)
                    
                except Exception as e:
                    # 跳过解析失败的项
                    continue
            
            print(f"  成功采集 {len(news_list)} 条新闻")
            
        except Exception as e:
            print(f"  采集失败: {e}")
            # 返回模拟数据作为备选
            pass  # 不使用模拟数据
        
        return news_list
    
    def get_mock_news(self, source_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取模拟新闻（备选方案）"""
        mock_news = []
        
        source_name = source_config['name']
        today = datetime.datetime.now()
        
        # 根据来源类型生成不同的模拟新闻
        if '财经' in source_name or '金融' in source_name:
            topics = ['股市行情', '货币政策', '经济数据', '投资策略', '市场分析']
        elif '政策' in source_name:
            topics = ['政策发布', '法规解读', '政府工作', '发展规划', '民生政策']
        else:
            topics = ['行业动态', '技术创新', '市场趋势', '企业新闻', '专家观点']
        
        for i in range(3):
            topic = topics[i % len(topics)]
            hours_ago = i * 2  # 模拟不同时间
            
            news_item = {
                'id': self.generate_id(f"{source_name}{topic}{i}", source_name, f"{today.strftime('%Y-%m-%d')} {10-i}:00:00"),
                'title': f"{source_name}: {topic}最新动态",
                'source': source_name,
                'category': 'simulated',
                'publish_time': (today - datetime.timedelta(hours=hours_ago)).strftime('%Y-%m-%d %H:%M:%S'),
                'content': f"这是{source_name}关于{topic}的模拟新闻内容。实际数据采集需要调整采集策略或使用API接口。",
                'url': f"http://example.com/news/{today.strftime('%Y%m%d')}_{i}",
                'keywords': [source_name, topic, '新闻'],
                'collected_at': datetime.datetime.now().isoformat(),
                'data_source': source_config['url'],
                'is_simulated': True
            }
            
            mock_news.append(news_item)
        
        print(f"  使用模拟数据: {len(mock_news)} 条新闻")
        return mock_news
    
    def extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 常见财经关键词
        finance_keywords = [
            '股市', '股票', '基金', '债券', '期货', '外汇', '黄金', '原油',
            '经济', 'GDP', 'CPI', 'PPI', '通胀', '通缩', '利率', '汇率',
            '政策', '监管', '法规', '改革', '开放', '创新', '发展', '增长',
            '投资', '融资', '并购', '重组', '上市', '退市', '分红', '配股',
            '科技', '人工智能', '大数据', '区块链', '云计算', '物联网', '5G',
            '消费', '零售', '电商', '物流', '制造', '工业', '农业', '服务'
        ]
        
        keywords = []
        for kw in finance_keywords:
            if kw in text:
                keywords.append(kw)
        
        return keywords[:5]
    
    def save_to_database(self, news_list: List[Dict[str, Any]]) -> int:
        """保存到数据库"""
        if not news_list:
            return 0
        
        try:
            import duckdb
            
            db_path = 'data/quant_system.duckdb'
            conn = duckdb.connect(db_path)
            
            saved_count = 0
            for news in news_list:
                try:
                    # 检查是否已存在
                    existing = conn.execute(
                        "SELECT id FROM official_news WHERE id = ?",
                        [news['id']]
                    ).fetchone()
                    
                    if existing:
                        # 更新现有记录
                        conn.execute("""
                            UPDATE official_news 
                            SET title = ?, content = ?, url = ?, keywords = ?, collected_at = ?
                            WHERE id = ?
                        """, [
                            news['title'],
                            news['content'],
                            news['url'],
                            str(news['keywords']),
                            news['collected_at'],
                            news['id']
                        ])
                    else:
                        # 插入新记录
                        conn.execute("""
                            INSERT INTO official_news 
                            (id, title, source, department, publish_time, content, url, keywords, collected_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, [
                            news['id'],
                            news['title'],
                            news['source'],
                            news.get('category', 'general'),
                            news['publish_time'],
                            news['content'],
                            news['url'],
                            str(news['keywords']),
                            news['collected_at']
                        ])
                    
                    saved_count += 1
                    
                except Exception as e:
                    print(f"  保存失败 {news.get('title', '未知标题')}: {e}")
            
            conn.close()
            print(f"✅ 保存 {saved_count} 条新闻到数据库")
            return saved_count
            
        except ImportError:
            print("⚠ duckdb不可用，跳过数据库保存")
            return 0
        except Exception as e:
            print(f"数据库保存失败: {e}")
            return 0
    
    def save_to_json(self, news_list: List[Dict[str, Any]]) -> str:
        """保存到JSON文件"""
        if not news_list:
            return ""
        
        try:
            # 创建输出目录
            output_dir = Path("data-pipeline/data/news")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"practical_news_{timestamp}.json"
            filepath = output_dir / filename
            
            # 准备数据
            output_data = {
                "metadata": {
                    "collected_at": datetime.datetime.now().isoformat(),
                    "total_count": len(news_list),
                    "sources": list(set([news.get('source', '未知') for news in news_list])),
                    "simulated_count": len([n for n in news_list if n.get('is_simulated', False)])
                },
                "news": news_list
            }
            
            # 保存文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 保存 {len(news_list)} 条新闻到JSON文件: {filepath}")
            return str(filepath)
            
        except Exception as e:
            print(f"保存到JSON失败: {e}")
            return ""
    
    def collect_all(self) -> List[Dict[str, Any]]:
        """采集所有新闻"""
        print("=" * 60)
        print("开始采集实用新闻")
        print("=" * 60)
        print(f"时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 初始化会话
        self.init_session()
        
        all_news = []
        
        # 遍历所有数据源
        for category, category_info in self.data_sources.items():
            print(f"\n📊 采集{category_info['name']}...")
            
            category_news = []
            for source in category_info['sources']:
                source['category'] = category
                news = self.fetch_web_news(source)
                category_news.extend(news)
            
            all_news.extend(category_news)
            print(f"  {category_info['name']}总计: {len(category_news)} 条")
        
        # 汇总统计
        print("\n" + "=" * 60)
        print("采集完成")
        print("=" * 60)
        
        total_count = len(all_news)
        simulated_count = len([n for n in all_news if n.get('is_simulated', False)])
        real_count = total_count - simulated_count
        
        print(f"总计采集新闻: {total_count} 条")
        print(f"  真实数据: {real_count} 条")
        print(f"  模拟数据: {simulated_count} 条")
        
        # 按来源统计
        sources = {}
        for news in all_news:
            source = news.get('source', '未知')
            sources[source] = sources.get(source, 0) + 1
        
        print("\n按来源统计:")
        for source, count in sources.items():
            print(f"  {source}: {count} 条")
        
        return all_news
    
    def run(self, save_to_db: bool = True, save_to_json: bool = True) -> Dict[str, Any]:
        """运行采集任务"""
        start_time = time.time()
        
        # 采集新闻
        all_news = self.collect_all()
        
        # 保存结果
        result = {
            "total_collected": len(all_news),
            "real_data": len([n for n in all_news if not n.get('is_simulated', False)]),
            "simulated_data": len([n for n in all_news if n.get('is_simulated', False)]),
            "saved_to_db": 0,
            "saved_to_json": "",
            "execution_time": 0
        }
        
        if save_to_db and all_news:
            result["saved_to_db"] = self.save_to_database(all_news)
        
        if save_to_json and all_news:
            json_path = self.save_to_json(all_news)
            result["saved_to_json"] = json_path
        
        # 计算执行时间
        result["execution_time"] = round(time.time() - start_time, 2)
        
        print(f"\n⏱️ 执行时间: {result['execution_time']} 秒")
        return result


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="实用版新闻采集器")
    parser.add_argument("--no-db", action="store_true", help="不保存到数据库")
    parser.add_argument("--no-json", action="store_true", help="不保存到JSON")
    
    args = parser.parse_args()
    
    # 检查依赖
    if not REQUESTS_AVAILABLE:
        print("错误: 缺少必要依赖库")
        print("请安装: pip install requests beautifulsoup4")
        return 1
    
    # 创建采集器并运行
    collector = PracticalNewsCollector()
    
    try:
        result = collector.run(
            save_to_db=not args.no_db,
            save_to_json=not args.no_json
        )
        
        print("\n" + "=" * 60)
        print("任务完成")
        print("=" * 60)
        print(f"采集总数: {result['total_collected']}")
        print(f"真实数据: {result['real_data']}")
        print(f"模拟数据: {result['simulated_data']}")
        print(f"保存到数据库: {result['saved_to_db']}")
        print(f"保存到JSON: {result['saved_to_json']}")
        print(f"执行时间: {result['execution_time']}秒")
        
        # 提供改进建议
        print("\n💡 改进建议:")
        if result['simulated_data'] > 0:
            print("1. 配置真实API密钥或调整网页选择器")
            print("2. 考虑使用第三方新闻API服务")
            print("3. 优化网页解析逻辑")
        
        if result['saved_to_db'] == 0:
            print("4. 检查数据库连接和表结构")
        
        return 0
        
    except Exception as e:
        print(f"执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())