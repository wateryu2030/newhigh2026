#!/usr/bin/env python3
"""
政策新闻数据库管理
- 创建数据库表结构
- 插入/查询新闻数据
- 提供 FastAPI 服务（默认端口 8001）

数据库：本目录下 `sqlite/news.db`（避免与仓库根 `data/` gitignore 规则冲突）
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from contextlib import contextmanager

# 数据库路径（本文件在 integrations/hongshan/policy-news/）
_POLICY_DIR = Path(__file__).resolve().parent
DB_PATH = _POLICY_DIR / "sqlite" / "news.db"

# 确保数据目录存在
DB_PATH.parent.mkdir(exist_ok=True)


@contextmanager
def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_database():
    """初始化数据库表结构"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 创建新闻表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                category TEXT NOT NULL,
                content TEXT,
                url TEXT,
                publish_date TEXT,
                sentiment REAL DEFAULT 0.0,
                domains TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_news_category ON news(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_news_date ON news(publish_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_news_source ON news(source)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_news_created ON news(created_at)')
        
        conn.commit()
        print("✓ 数据库初始化完成")


def insert_news(items: List[Dict]) -> int:
    """插入新闻数据，返回插入数量"""
    inserted = 0
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        for item in items:
            # 检查是否已存在（按标题去重）
            cursor.execute('SELECT id FROM news WHERE title = ?', (item.get('title', ''),))
            if cursor.fetchone():
                continue
            
            # 插入新闻
            cursor.execute('''
                INSERT INTO news (title, source, category, content, url, publish_date, sentiment, domains)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item.get('title', ''),
                item.get('source', ''),
                item.get('category', '其他政策'),
                item.get('content', ''),
                item.get('url', ''),
                item.get('date', datetime.now().strftime('%Y-%m-%d')),
                item.get('sentiment', 0.0),
                json.dumps(item.get('domains', ['综合']), ensure_ascii=False)
            ))
            inserted += 1
        
        conn.commit()
    
    return inserted


def get_news_list(
    category: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Dict]:
    """获取新闻列表"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        query = 'SELECT * FROM news WHERE 1=1'
        params = []
        
        if category:
            query += ' AND category = ?'
            params.append(category)
        
        if source:
            query += ' AND source = ?'
            params.append(source)
        
        query += ' ORDER BY publish_date DESC, created_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        return [dict(row) for row in rows]


def get_news_by_id(news_id: int) -> Optional[Dict]:
    """根据 ID 获取新闻详情"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM news WHERE id = ?', (news_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_categories() -> List[str]:
    """获取所有分类"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT category FROM news ORDER BY category')
        return [row['category'] for row in cursor.fetchall()]


def get_sources() -> List[str]:
    """获取所有来源"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT source FROM news ORDER BY source')
        return [row['source'] for row in cursor.fetchall()]


def get_stats() -> Dict:
    """获取统计信息"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 总数
        cursor.execute('SELECT COUNT(*) as total FROM news')
        total = cursor.fetchone()['total']
        
        # 按分类统计
        cursor.execute('SELECT category, COUNT(*) as count FROM news GROUP BY category ORDER BY count DESC')
        by_category = {row['category']: row['count'] for row in cursor.fetchall()}
        
        # 按来源统计
        cursor.execute('SELECT source, COUNT(*) as count FROM news GROUP BY source ORDER BY count DESC')
        by_source = {row['source']: row['count'] for row in cursor.fetchall()}
        
        # 今日新增
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('SELECT COUNT(*) as count FROM news WHERE DATE(created_at) = ?', (today,))
        today_count = cursor.fetchone()['count']
        
        return {
            'total': total,
            'by_category': by_category,
            'by_source': by_source,
            'today_count': today_count
        }


def clear_old_news(days: int = 90):
    """清理旧新闻（默认保留 90 天）"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM news WHERE DATE(created_at) < DATE("now", ?)', (f'-{days} days',))
        deleted = cursor.rowcount
        conn.commit()
        return deleted


# API 服务（FastAPI）
def create_api_app():
    """创建 FastAPI 应用"""
    try:
        from fastapi import FastAPI, Query, HTTPException
        from fastapi.middleware.cors import CORSMiddleware
        import uvicorn
    except ImportError:
        print("错误：需要安装 fastapi 和 uvicorn")
        print("安装：pip install fastapi uvicorn --break-system-packages")
        return None
    
    app = FastAPI(title="红山量化 - 政策新闻 API", version="1.0.0")
    
    # CORS 配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/")
    def root():
        return {"message": "红山量化政策新闻 API", "version": "1.0.0"}
    
    @app.get("/news/stats")
    def get_statistics():
        """获取统计信息"""
        return {"data": get_stats()}
    
    @app.get("/news/categories")
    def list_categories():
        """获取所有分类"""
        return {"data": get_categories()}
    
    @app.get("/news/sources")
    def list_sources():
        """获取所有来源"""
        return {"data": get_sources()}
    
    @app.get("/news")
    def list_news(
        category: Optional[str] = Query(None, description="分类"),
        source: Optional[str] = Query(None, description="来源"),
        limit: int = Query(50, ge=1, le=200, description="每页数量"),
        offset: int = Query(0, ge=0, description="偏移量")
    ):
        """获取新闻列表"""
        news_list = get_news_list(category, source, limit, offset)
        return {"data": news_list, "total": len(news_list)}
    
    @app.get("/news/{news_id}")
    def get_news(news_id: int):
        """获取新闻详情"""
        news = get_news_by_id(news_id)
        if not news:
            raise HTTPException(status_code=404, detail="新闻不存在")
        return {"data": news}
    
    @app.post("/news/ingest")
    def ingest_news(items: List[Dict]):
        """批量导入新闻"""
        count = insert_news(items)
        return {"message": f"成功导入 {count} 条新闻"}
    
    return app


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "init":
            init_database()
        elif command == "stats":
            stats = get_stats()
            print(json.dumps(stats, indent=2, ensure_ascii=False))
        elif command == "api":
            # 启动 API 服务
            app = create_api_app()
            if app:
                import uvicorn
                uvicorn.run(app, host="0.0.0.0", port=8001)
        else:
            print(f"未知命令：{command}")
            print("可用命令：init, stats, api")
    else:
        # 默认初始化
        init_database()
        stats = get_stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))
