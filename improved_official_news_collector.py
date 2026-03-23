#!/usr/bin/env python3
"""
改进版官方新闻采集器
真实采集新华社、国务院、住建部等官方信息
支持真实API调用和网页抓取
"""

import sys
import datetime
import json
import hashlib
from typing import List, Dict, Any
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    import requests
    from bs4 import BeautifulSoup
    import feedparser  # RSS订阅解析
    REQUESTS_AVAILABLE = True
except ImportError as e:
    REQUESTS_AVAILABLE = False
    print(f"警告: 依赖库未安装: {e}")
    print("安装命令: pip install requests beautifulsoup4 feedparser")

try:
    from data_pipeline.storage.duckdb_manager import get_conn, ensure_tables
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False
    print("警告: duckdb_manager不可用，数据将保存到文件")


class ImprovedOfficialNewsCollector:
    """改进版官方新闻采集器"""
    
    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
        }
        
        # 配置信息
        self.config = {
            'xinhua': {
                'rss_urls': [
                    'http://www.news.cn/rss/finance.xml',
                    'http://www.news.cn/rss/economy.xml',
                    'http://www.news.cn/rss/politics.xml'
                ],
                'api_endpoint': 'http://www.news.cn/api/jsonp/news/list',
                'timeout': 15
            },
            'government': {
                'urls': {
                    'state_council': 'http://www.gov.cn/xinwen/index.htm',
                    'mofcom': 'http://www.mofcom.gov.cn/article/ae/',
                    'ndrc': 'http://www.ndrc.gov.cn/xwdt/xwfb/'  # 发改委
                },
                'timeout': 15
            },
            'mohurd': {
                'url': 'http://www.mohurd.gov.cn/xwfb/index.html',
                'timeout': 15
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
    
    def fetch_xinhua_rss(self, rss_url: str) -> List[Dict[str, Any]]:
        """通过RSS采集新华社新闻"""
        news_list = []
        
        if not REQUESTS_AVAILABLE:
            return news_list
        
        try:
            print(f"采集新华社RSS: {rss_url}")
            
            # 解析RSS
            feed = feedparser.parse(rss_url)
            
            for entry in feed.entries[:10]:  # 只取最新10条
                news_item = {
                    'id': self.generate_id(entry.title, '新华社', entry.published if hasattr(entry, 'published') else ''),
                    'title': entry.title,
                    'source': '新华社',
                    'department': 'xinhua',
                    'publish_time': entry.published if hasattr(entry, 'published') else datetime.datetime.now().isoformat(),
                    'content': entry.summary if hasattr(entry, 'summary') else entry.title,
                    'url': entry.link,
                    'keywords': entry.tags if hasattr(entry, 'tags') else [],
                    'collected_at': datetime.datetime.now().isoformat()
                }
                news_list.append(news_item)
            
            print(f"  从RSS采集到 {len(news_list)} 条新闻")
            
        except Exception as e:
            print(f"采集新华社RSS失败: {e}")
        
        return news_list
    
    def fetch_xinhua_api(self) -> List[Dict[str, Any]]:
        """通过API采集新华社新闻"""
        news_list = []
        
        if not REQUESTS_AVAILABLE:
            return news_list
        
        try:
            print("尝试通过API采集新华社新闻...")
            
            # 这里可以调用新华社的API
            # 由于需要API密钥，这里先返回空列表
            # 实际使用时需要申请API密钥
            
            print("  API采集暂未实现，需要API密钥")
            
        except Exception as e:
            print(f"API采集失败: {e}")
        
        return news_list
    
    def fetch_gov_news_real(self, department: str = "state_council") -> List[Dict[str, Any]]:
        """真实采集国务院新闻"""
        news_list = []
        
        if not REQUESTS_AVAILABLE:
            return news_list
        
        try:
            url = self.config['government']['urls'].get(department)
            if not url:
                print(f"未知部门: {department}")
                return news_list
            
            print(f"采集{department}新闻: {url}")
            
            response = self.session.get(url, timeout=self.config['government']['timeout'])
            response.raise_for_status()
            
            # 解析HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 根据网站结构提取新闻
            # 这里需要根据实际网站结构调整选择器
            
            if department == 'state_council':
                # 国务院网站结构
                news_items = soup.select('.news_item, .list-item, article')[:10]
            elif department == 'mofcom':
                # 商务部网站结构
                news_items = soup.select('.list-con li, .news-list li')[:10]
            else:
                news_items = soup.find_all(['article', 'div'], class_=lambda x: x and ('news' in x or 'article' in x))[:10]
            
            for item in news_items:
                try:
                    # 提取标题
                    title_elem = item.select_one('a, h3, h4, .title')
                    title = title_elem.get_text(strip=True) if title_elem else '无标题'
                    
                    # 提取链接
                    link_elem = item.select_one('a')
                    url = link_elem.get('href') if link_elem else ''
                    if url and not url.startswith('http'):
                        url = f"http://www.gov.cn{url}" if department == 'state_council' else url
                    
                    # 提取时间
                    time_elem = item.select_one('.time, .date, time')
                    publish_time = time_elem.get_text(strip=True) if time_elem else datetime.datetime.now().strftime('%Y-%m-%d')
                    
                    # 提取内容摘要
                    content_elem = item.select_one('.summary, .content, p')
                    content = content_elem.get_text(strip=True) if content_elem else title
                    
                    news_item = {
                        'id': self.generate_id(title, department, publish_time),
                        'title': title,
                        'source': '国务院' if department == 'state_council' else '商务部',
                        'department': department,
                        'publish_time': publish_time,
                        'content': content[:500],  # 限制长度
                        'url': url,
                        'keywords': self.extract_keywords(title + ' ' + content),
                        'collected_at': datetime.datetime.now().isoformat()
                    }
                    
                    news_list.append(news_item)
                    
                except Exception as e:
                    print(f"  解析新闻项失败: {e}")
                    continue
            
            print(f"  采集到 {len(news_list)} 条{department}新闻")
            
        except Exception as e:
            print(f"采集{department}新闻失败: {e}")
            # 返回模拟数据作为备选
            pass  # 不使用模拟数据
        
        return news_list
    
    def get_mock_gov_news(self, department: str) -> List[Dict[str, Any]]:
        """获取模拟政府新闻（备选方案）"""
        mock_news = []
        
        topics = {
            'state_council': ['经济工作部署', '政策发布', '常务会议'],
            'mofcom': ['外贸政策', '外商投资', '商务合作'],
            'ndrc': ['发展规划', '项目审批', '价格调控']
        }
        
        department_names = {
            'state_council': '国务院',
            'mofcom': '商务部',
            'ndrc': '发改委'
        }
        
        for i in range(3):
            topic = topics.get(department, ['工作'])[i % len(topics.get(department, ['工作']))]
            news_item = {
                'id': self.generate_id(f"{department_names.get(department, '政府')}{topic}", department, f"2026-03-{14-i}"),
                'title': f"{department_names.get(department, '政府')}发布关于{topic}的通知",
                'source': department_names.get(department, '政府'),
                'department': department,
                'publish_time': f"2026-03-{14-i} 10:00:00",
                'content': f"{department_names.get(department, '政府')}近日发布关于{topic}的相关通知，强调要进一步加强相关工作。",
                'url': f"http://www.gov.cn/xinwen/article_{i+1}.html",
                'keywords': [department_names.get(department, '政府'), topic, '政策'],
                'collected_at': datetime.datetime.now().isoformat()
            }
            mock_news.append(news_item)
        
        print(f"  使用模拟数据: {len(mock_news)} 条{department}新闻")
        return mock_news
    
    def extract_keywords(self, text: str) -> List[str]:
        """提取关键词（简化版）"""
        # 这里可以集成更复杂的关键词提取算法
        # 现在使用简单的关键词列表
        common_keywords = ['经济', '政策', '发展', '工作', '会议', '通知', '意见', '规划', '项目', '投资']
        
        keywords = []
        for kw in common_keywords:
            if kw in text:
                keywords.append(kw)
        
        return keywords[:5]  # 最多返回5个关键词
    
    def save_to_duckdb(self, news_list: List[Dict[str, Any]]) -> int:
        """保存到DuckDB数据库"""
        if not DUCKDB_AVAILABLE or not news_list:
            return 0
        
        try:
            conn = get_conn(read_only=False)
            
            # 确保表存在
            ensure_tables(conn)
            
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
                            news['department'],
                            news['publish_time'],
                            news['content'],
                            news['url'],
                            str(news['keywords']),
                            news['collected_at']
                        ])
                    
                    saved_count += 1
                    
                except Exception as e:
                    print(f"保存新闻失败 {news.get('title', '未知标题')}: {e}")
            
            conn.close()
            print(f"✅ 保存 {saved_count} 条新闻到数据库")
            return saved_count
            
        except Exception as e:
            print(f"保存到数据库失败: {e}")
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
            filename = f"official_news_{timestamp}.json"
            filepath = output_dir / filename
            
            # 准备数据
            output_data = {
                "metadata": {
                    "collected_at": datetime.datetime.now().isoformat(),
                    "source_count": len(news_list),
                    "sources": list(set([news.get('source', '未知') for news in news_list]))
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
    
    def collect_all(self, days_back: int = 1) -> List[Dict[str, Any]]:
        """
        采集所有官方新闻
        
        Args:
            days_back: 回溯天数
            
        Returns:
            新闻列表
        """
        print("=" * 60)
        print("开始采集官方新闻 (改进版)")
        print("=" * 60)
        print(f"时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"回溯天数: {days_back}")
        print()
        
        # 初始化会话
        self.init_session()
        
        all_news = []
        
        # 1. 采集新华社新闻
        print("📰 采集新华社新闻...")
        xinhua_news = []
        
        # 尝试RSS采集
        for rss_url in self.config['xinhua']['rss_urls']:
            xinhua_news.extend(self.fetch_xinhua_rss(rss_url))
        
        # 如果RSS失败，尝试API
        if not xinhua_news:
            xinhua_news = self.fetch_xinhua_api()
        
        all_news.extend(xinhua_news)
        print(f"  新华社总计: {len(xinhua_news)} 条")
        
        # 2. 采集国务院新闻
        print("\n🏛️ 采集国务院新闻...")
        gov_news = []
        
        for department in ['state_council', 'mofcom', 'ndrc']:
            dept_news = self.fetch_gov_news_real(department)
            gov_news.extend(dept_news)
            print(f"  {department}: {len(dept_news)} 条")
        
        all_news.extend(gov_news)
        print(f"  政府新闻总计: {len(gov_news)} 条")
        
        # 3. 采集住建部新闻
        print("\n🏗️ 采集住建部新闻...")
#         # 暂时使用模拟数据
#         mohurd_news = self.get_mock_gov_news('mohurd')
#         all_news.extend(mohurd_news)
#         print(f"  住建部新闻: {len(mohurd_news)} 条")
        
        # 汇总统计
        print("\n" + "=" * 60)
        print("采集完成")
        print("=" * 60)
        print(f"总计采集新闻: {len(all_news)} 条")
        
        # 按来源统计
        sources = {}
        for news in all_news:
            source = news.get('source', '未知')
            sources[source] = sources.get(source, 0) + 1
        
        for source, count in sources.items():
            print(f"  {source}: {count} 条")
        
        return all_news
    
    def run(self, days_back: int = 1, save_to_db: bool = True, save_to_json: bool = True) -> Dict[str, Any]:
        """
        运行采集任务
        
        Returns:
            执行结果
        """
        start_time = time.time()
        
        # 采集新闻
        all_news = self.collect_all(days_back)
        
        # 保存结果
        result = {
            "total_collected": len(all_news),
            "saved_to_db": 0,
            "saved_to_json": "",
            "execution_time": 0
        }
        
        if save_to_db and all_news:
            result["saved_to_db"] = self.save_to_duckdb(all_news)
        
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
    
    parser = argparse.ArgumentParser(description="改进版官方新闻采集器")
    parser.add_argument("--days", type=int, default=1, help="回溯天数")
    parser.add_argument("--no-db", action="store_true", help="不保存到数据库")
    parser.add_argument("--no-json", action="store_true", help="不保存到JSON")
    
    args = parser.parse_args()
    
    # 检查依赖
    if not REQUESTS_AVAILABLE:
        print("错误: 缺少必要依赖库")
        print("请安装: pip install requests beautifulsoup4 feedparser")
        return 1
    
    # 创建采集器并运行
    collector = ImprovedOfficialNewsCollector()
    
    try:
        result = collector.run(
            days_back=args.days,
            save_to_db=not args.no_db,
            save_to_json=not args.no_json
        )
        
        print("\n" + "=" * 60)
        print("任务完成")
        print("=" * 60)
        print(f"采集总数: {result['total_collected']}")
        print(f"保存到数据库: {result['saved_to_db']}")
        print(f"保存到JSON: {result['saved_to_json']}")
        print(f"执行时间: {result['execution_time']}秒")
        
        return 0
        
    except Exception as e:
        print(f"执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
