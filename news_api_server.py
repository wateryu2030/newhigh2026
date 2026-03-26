#!/usr/bin/env python3
"""
新闻展示 API 服务器
提供新闻数据的 API 接口和简单网页展示
"""

import os
import sys
import json
import datetime
from pathlib import Path
from typing import List, Dict, Any

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    import duckdb
except ImportError as e:
    print(f"缺少依赖：{e}")
    print("安装命令：pip install fastapi uvicorn duckdb")
    sys.exit(1)

# 创建 FastAPI 应用
app = FastAPI(
    title="量化平台新闻 API",
    description="提供新闻数据采集和展示服务",
    version="1.0.0"
)

# 添加 CORS 支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据库路径
DB_PATH = Path(__file__).parent / "data" / "quant_system.duckdb"


def get_db_connection():
    """获取数据库连接"""
    return duckdb.connect(str(DB_PATH))


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "量化平台新闻 API",
        "version": "1.0.0",
        "endpoints": {
            "news_list": "/api/news/list",
            "news_today": "/api/news/today",
            "news_stock": "/api/news/stock?code=002701",
            "news_summary": "/api/news/summary",
            "html_view": "/news"
        }
    }


@app.get("/api/news/list")
async def get_news_list(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    source: str = Query(None),
    days: int = Query(7, ge=1, le=30)
):
    """获取新闻列表"""
    try:
        conn = get_db_connection()

        # 构建查询
        where_clauses = []
        params = []

        if source:
            where_clauses.append("source = ?")
            params.append(source)

        date_from = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        where_clauses.append("collected_at >= ?")
        params.append(date_from)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        query = f"""
            SELECT id, title, source, content, url, keywords, collected_at
            FROM official_news
            WHERE {where_sql}
            ORDER BY collected_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        result = conn.execute(query, params).fetchall()

        # 计算总数
        count_query = f"""
            SELECT COUNT(*) FROM official_news
            WHERE {where_sql}
        """
        total = conn.execute(count_query, params[:-2]).fetchone()[0]

        conn.close()

        # 转换为字典
        news_list = []
        for row in result:
            news_list.append({
                'id': row[0],
                'title': row[1],
                'source': row[2],
                'content': row[3],
                'url': row[4],
                'keywords': row[5],
                'collected_at': row[6]
            })

        return {
            'total': total,
            'limit': limit,
            'offset': offset,
            'news': news_list
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/news/today")
async def get_news_today():
    """获取今日新闻"""
    try:
        conn = get_db_connection()

        today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        query = """
            SELECT id, title, source, content, url, keywords, collected_at
            FROM official_news
            WHERE collected_at >= ?
            ORDER BY collected_at DESC
        """

        result = conn.execute(query, [today_start.isoformat()]).fetchall()
        conn.close()

        news_list = []
        for row in result:
            news_list.append({
                'id': row[0],
                'title': row[1],
                'source': row[2],
                'content': row[3],
                'url': row[4],
                'keywords': row[5],
                'collected_at': row[6]
            })

        # 按来源统计
        source_stats = {}
        for news in news_list:
            source = news['source']
            source_stats[source] = source_stats.get(source, 0) + 1

        return {
            'date': datetime.datetime.now().strftime('%Y-%m-%d'),
            'total': len(news_list),
            'by_source': source_stats,
            'news': news_list
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/news/stock")
async def get_stock_news(code: str = Query(..., description="股票代码")):
    """获取个股相关新闻"""
    try:
        # 股票代码映射
        stock_names = {
            '002701': '奥瑞金',
            '300212': '易华录',
            '600881': '亚泰集团',
            '600889': '南京化纤'
        }

        stock_name = stock_names.get(code, code)

        conn = get_db_connection()

        # 从新闻中筛选包含股票代码或名称的
        query = """
            SELECT id, title, source, content, url, keywords, collected_at
            FROM official_news
            WHERE content LIKE ? OR title LIKE ?
            ORDER BY collected_at DESC
            LIMIT 50
        """

        keyword = f"%{code}%"
        result = conn.execute(query, [keyword, keyword]).fetchall()
        conn.close()

        news_list = []
        for row in result:
            news_list.append({
                'id': row[0],
                'title': row[1],
                'source': row[2],
                'content': row[3],
                'url': row[4],
                'keywords': row[5],
                'collected_at': row[6],
                'related_stock': code
            })

        return {
            'stock_code': code,
            'stock_name': stock_name,
            'total': len(news_list),
            'news': news_list
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/news/summary")
async def get_news_summary():
    """获取新闻摘要统计"""
    try:
        conn = get_db_connection()

        # 今日统计
        today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # 按来源统计
        source_query = """
            SELECT source, COUNT(*) as count
            FROM official_news
            WHERE collected_at >= ?
            GROUP BY source
            ORDER BY count DESC
        """
        source_stats = conn.execute(source_query, [today_start.isoformat()]).fetchall()

        # 按小时统计
        hourly_query = """
            SELECT strftime(collected_at, '%Y-%m-%d %H:00') as hour, COUNT(*) as count
            FROM official_news
            WHERE collected_at >= ?
            GROUP BY hour
            ORDER BY hour DESC
        """
        hourly_stats = conn.execute(hourly_query, [today_start.isoformat()]).fetchall()

        # 最近 7 天趋势
        trend_query = """
            SELECT strftime(collected_at, '%Y-%m-%d') as date, COUNT(*) as count
            FROM official_news
            WHERE collected_at >= ?
            GROUP BY date
            ORDER BY date DESC
        """
        date_7days = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
        trend_stats = conn.execute(trend_query, [date_7days]).fetchall()

        conn.close()

        return {
            'today': {
                'total': sum(s[1] for s in source_stats),
                'by_source': [{'source': s[0], 'count': s[1]} for s in source_stats]
            },
            'hourly': [{'hour': h[0], 'count': h[1]} for h in hourly_stats],
            'trend': [{'date': t[0], 'count': t[1]} for t in trend_stats]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/news", response_class=HTMLResponse)
async def news_html_view():
    """新闻网页展示"""
    try:
        conn = get_db_connection()

        # 获取今日新闻
        today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        query = """
            SELECT id, title, source, content, url, keywords, collected_at
            FROM official_news
            WHERE collected_at >= ?
            ORDER BY collected_at DESC
            LIMIT 100
        """

        result = conn.execute(query, [today_start.isoformat()]).fetchall()
        conn.close()

        # 生成 HTML
        html = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>量化平台 - 新闻监控</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .header h1 { font-size: 28px; margin-bottom: 10px; }
        .header p { opacity: 0.9; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .stat-card h3 { color: #666; font-size: 14px; margin-bottom: 5px; }
        .stat-card .value { font-size: 32px; font-weight: bold; color: #333; }
        .news-list { display: flex; flex-direction: column; gap: 15px; }
        .news-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        .news-card:hover { transform: translateY(-2px); }
        .news-card h2 { font-size: 18px; margin-bottom: 10px; color: #333; }
        .news-card .meta {
            display: flex;
            gap: 15px;
            font-size: 13px;
            color: #666;
            margin-bottom: 10px;
        }
        .news-card .meta span {
            background: #f0f0f0;
            padding: 3px 8px;
            border-radius: 4px;
        }
        .news-card .content { color: #555; line-height: 1.6; }
        .news-card .keywords {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 10px;
        }
        .keyword {
            background: #e8f4fd;
            color: #0366d6;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 12px;
        }
        .refresh-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
        }
        .refresh-btn:hover { background: #5568d3; }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            color: #666;
            font-size: 13px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📰 量化平台 - 新闻监控</h1>
            <p>实时监控财经新闻，辅助投资决策</p>
            <button class="refresh-btn" onclick="location.reload()" style="margin-top: 15px;">🔄 刷新</button>
        </div>

        <div class="stats">
            <div class="stat-card">
                <h3>今日新闻总数</h3>
                <div class="value">""" + str(len(result)) + """</div>
            </div>
            <div class="stat-card">
                <h3>数据源数量</h3>
                <div class="value">""" + str(len(set(r[2] for r in result))) + """</div>
            </div>
            <div class="stat-card">
                <h3>最后更新</h3>
                <div class="value" style="font-size: 18px;">""" + datetime.datetime.now().strftime('%H:%M') + """</div>
            </div>
        </div>

        <div class="news-list">
"""

        for row in result:
            news_id, title, source, content, url, keywords, collected_at = row

            # 解析关键词
            kw_list = []
            if keywords:
                try:
                    kw_list = eval(keywords) if isinstance(keywords, str) else keywords
                except:
                    kw_list = []

            # 格式化时间
            try:
                dt = datetime.datetime.fromisoformat(collected_at)
                time_str = dt.strftime('%m-%d %H:%M')
            except:
                time_str = collected_at[:16]

            html += f"""
            <div class="news-card">
                <h2>{title}</h2>
                <div class="meta">
                    <span>📍 {source}</span>
                    <span>🕐 {time_str}</span>
                </div>
                <div class="content">{content[:200]}{'...' if len(content) > 200 else ''}</div>
                <div class="keywords">
"""

            for kw in kw_list[:5]:
                html += f'<span class="keyword">{kw}</span>'

            html += """
                </div>
            </div>
"""

        html += """
        </div>

        <div class="footer">
            <p>量化平台新闻监控系统 | 数据实时更新</p>
            <p>API 接口：<code>/api/news/list</code> | <code>/api/news/today</code> | <code>/api/news/summary</code></p>
        </div>
    </div>
</body>
</html>
"""

        return HTMLResponse(content=html)

    except Exception as e:
        return HTMLResponse(content=f"<h1>Error</h1><p>{str(e)}</p>", status_code=500)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='新闻展示 API 服务器')
    parser.add_argument('--host', default='0.0.0.0', help='监听地址')
    parser.add_argument('--port', type=int, default=8080, help='监听端口')
    parser.add_argument('--reload', action='store_true', help='开发模式自动重载')

    args = parser.parse_args()

    print("=" * 60)
    print("📰 量化平台新闻 API 服务器")
    print("=" * 60)
    print(f"启动地址：http://{args.host}:{args.port}")
    print(f"网页展示：http://{args.host}:{args.port}/news")
    print(f"API 文档：http://{args.host}:{args.port}/docs")
    print("=" * 60)

    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)


if __name__ == '__main__':
    main()
