#!/usr/bin/env python3
"""
重点股票新闻监控采集器 (简化版)
监控标的：002701 奥瑞金、300212 易华录、600881 亚泰集团
数据源：证券时报、已有新闻数据过滤
"""

import os
import sys
import datetime
import json
import duckdb
from typing import List, Dict, Any
from pathlib import Path

# 重点监控股票
MONITORED_STOCKS = [
    {'code': '002701', 'name': '奥瑞金', 'full_name': '奥瑞金科技股份有限公司'},
    {'code': '300212', 'name': '易华录', 'full_name': '北京易华录信息技术股份有限公司'},
    {'code': '600881', 'name': '亚泰集团', 'full_name': '吉林亚泰 (集团) 股份有限公司'}
]

# 监控关键词
MONITOR_KEYWORDS = [
    '奥瑞金', 'ORGTECH', '红牛罐', '金属包装',
    '易华录', '数据湖', '数据要素', '智能交通', '华录集团',
    '亚泰集团', '亚泰', '吉林水泥', '东北建材'
]


def extract_keywords(text: str) -> List[str]:
    """提取匹配关键词"""
    matched = []
    for kw in MONITOR_KEYWORDS:
        if kw in text:
            matched.append(kw)
    return matched[:5]


def identify_stocks(text: str) -> List[Dict[str, str]]:
    """识别新闻中涉及的股票"""
    stocks = []
    for stock in MONITORED_STOCKS:
        if stock['name'] in text or stock['code'] in text or stock['full_name'] in text:
            stocks.append(stock)
    return stocks


def filter_existing_news() -> List[Dict[str, Any]]:
    """从现有新闻数据库中筛选监控股票相关新闻"""
    try:
        conn = duckdb.connect('data/quant_system.duckdb')

        # 从 official_news 表中筛选
        result = conn.execute("""
            SELECT id, title, source, content, url, keywords, collected_at
            FROM official_news
            WHERE collected_at >= ?
            ORDER BY collected_at DESC
        """, [(datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()]).fetchall()

        filtered_news = []
        for row in result:
            news_id, title, source, content, url, keywords, collected_at = row

            # 检查是否包含监控关键词
            text = f"{title} {content}"
            matched_keywords = extract_keywords(text)
            stocks = identify_stocks(text)

            if matched_keywords or stocks:
                filtered_news.append({
                    'id': news_id,
                    'title': title,
                    'source': source,
                    'category': 'stock_news',
                    'publish_time': collected_at,
                    'content': content[:500] if content else '',
                    'url': url or '',
                    'keywords': matched_keywords,
                    'related_stocks': [s['code'] for s in stocks],
                    'collected_at': collected_at
                })

        conn.close()
        return filtered_news

    except Exception as e:
        print(f"筛选新闻失败：{e}")
        return []


def generate_stock_news_report(news_list: List[Dict[str, Any]], output_path: str):
    """生成股票新闻监控报告"""

    # 按股票分组
    stock_news = {code: [] for code in ['002701', '300212', '600881']}
    other_news = []

    for news in news_list:
        related = news.get('related_stocks', [])
        if related:
            for code in related:
                if code in stock_news:
                    stock_news[code].append(news)
        else:
            other_news.append(news)

    # 生成报告
    report = []
    report.append("# 重点股票新闻监控报告")
    report.append(f"**生成时间**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append(f"**监控标的**: 002701 奥瑞金、300212 易华录、600881 亚泰集团")
    report.append("")

    for code, stock_info in [('002701', '奥瑞金'), ('300212', '易华录'), ('600881', '亚泰集团')]:
        report.append(f"## {code} {stock_info}")
        report.append("")

        news = stock_news[code]
        if news:
            report.append(f"相关新闻：{len(news)} 条")
            report.append("")
            for n in news[:10]:  # 最多显示 10 条
                report.append(f"### {n['title']}")
                report.append(f"- 时间：{n['publish_time']}")
                report.append(f"- 来源：{n['source']}")
                report.append(f"- 关键词：{', '.join(n['keywords']) if n['keywords'] else '无'}")
                report.append(f"- 链接：{n['url'] or '无'}")
                report.append("")
        else:
            report.append("今日无相关新闻")
            report.append("")

    # 保存报告
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))

    return output_path


def main():
    """主函数"""
    print("=" * 60)
    print("重点股票新闻监控")
    print("=" * 60)
    print(f"时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"监控标的：奥瑞金 (002701)、易华录 (300212)、亚泰集团 (600881)")
    print()

    # 筛选现有新闻
    print("📰 筛选监控股票相关新闻...")
    news_list = filter_existing_news()
    print(f"  找到 {len(news_list)} 条相关新闻")

    # 生成报告
    report_path = f"data-pipeline/data/news/stock_monitor_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)

    generate_stock_news_report(news_list, report_path)
    print(f"✅ 生成监控报告：{report_path}")

    # 保存 JSON
    json_path = f"data-pipeline/data/news/stock_monitor_news_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'collected_at': datetime.datetime.now().isoformat(),
                'total_count': len(news_list),
                'monitored_stocks': [s['code'] for s in MONITORED_STOCKS]
            },
            'news': news_list
        }, f, ensure_ascii=False, indent=2)

    print(f"✅ 保存 JSON 文件：{json_path}")

    # 统计
    print("\n" + "=" * 60)
    print("监控完成")
    print("=" * 60)
    print(f"总计相关新闻：{len(news_list)} 条")

    return {'total': len(news_list), 'report_path': report_path, 'json_path': json_path}


if __name__ == '__main__':
    main()
