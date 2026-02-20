#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库模型定义 - SQLite
"""
import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Tuple
import pandas as pd


class StockDatabase:
    """股票数据库管理类"""
    
    def __init__(self, db_path="data/astock.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 股票基本信息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stocks (
                order_book_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                name TEXT,
                market TEXT,
                listed_date TEXT,
                de_listed_date TEXT,
                type TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 日线行情表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_bars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_book_id TEXT NOT NULL,
                trade_date DATE NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                total_turnover REAL,
                adjust_factor REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(order_book_id, trade_date)
            )
        ''')
        
        # 交易日历表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trading_calendar (
                trade_date DATE PRIMARY KEY,
                is_trading INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_bars_order_book_id ON daily_bars(order_book_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_bars_trade_date ON daily_bars(trade_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_bars_composite ON daily_bars(order_book_id, trade_date)')
        
        conn.commit()
        conn.close()
        print(f"✅ 数据库初始化完成: {self.db_path}")
    
    def add_stock(self, order_book_id: str, symbol: str, name: str = None, 
                  market: str = "CN", listed_date: str = None, 
                  de_listed_date: str = None, type: str = "CS"):
        """添加股票基本信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO stocks 
            (order_book_id, symbol, name, market, listed_date, de_listed_date, type, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (order_book_id, symbol, name, market, listed_date, de_listed_date, type, datetime.now()))
        conn.commit()
        conn.close()
    
    def add_daily_bars(self, order_book_id: str, bars_df: pd.DataFrame):
        """批量添加日线数据"""
        if bars_df is None or len(bars_df) == 0:
            return
        
        conn = sqlite3.connect(self.db_path)
        
        # 准备数据
        data = []
        for _, row in bars_df.iterrows():
            trade_date = pd.to_datetime(row['日期']).strftime('%Y-%m-%d')
            data.append((
                order_book_id,
                trade_date,
                float(row.get('开盘', 0)),
                float(row.get('最高', 0)),
                float(row.get('最低', 0)),
                float(row.get('收盘', 0)),
                float(row.get('成交量', 0)),
                float(row.get('成交额', 0)),
                1.0  # adjust_factor
            ))
        
        cursor = conn.cursor()
        cursor.executemany('''
            INSERT OR REPLACE INTO daily_bars 
            (order_book_id, trade_date, open, high, low, close, volume, total_turnover, adjust_factor)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', data)
        
        conn.commit()
        conn.close()
        print(f"✅ 已保存 {len(data)} 条 {order_book_id} 的日线数据")
    
    def get_daily_bars(self, order_book_id: str, start_date: str = None, 
                       end_date: str = None) -> pd.DataFrame:
        """获取日线数据"""
        conn = sqlite3.connect(self.db_path)
        
        query = "SELECT trade_date, open, high, low, close, volume, total_turnover FROM daily_bars WHERE order_book_id = ?"
        params = [order_book_id]
        
        if start_date:
            query += " AND trade_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND trade_date <= ?"
            params.append(end_date)
        
        query += " ORDER BY trade_date"
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if len(df) > 0:
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df = df.set_index('trade_date')
        
        return df
    
    def get_stocks(self) -> List[Tuple]:
        """获取所有股票列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT order_book_id, symbol, name FROM stocks")
        result = cursor.fetchall()
        conn.close()
        return result
    
    def add_trading_dates(self, dates: List[str]):
        """添加交易日"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        data = [(date, 1) for date in dates]
        cursor.executemany('''
            INSERT OR REPLACE INTO trading_calendar (trade_date, is_trading)
            VALUES (?, ?)
        ''', data)
        conn.commit()
        conn.close()
    
    def get_trading_dates(self, start_date: str = None, end_date: str = None) -> List[str]:
        """获取交易日列表"""
        conn = sqlite3.connect(self.db_path)
        query = "SELECT trade_date FROM trading_calendar WHERE is_trading = 1"
        params = []
        
        if start_date:
            query += " AND trade_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND trade_date <= ?"
            params.append(end_date)
        
        query += " ORDER BY trade_date"
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df['trade_date'].tolist() if len(df) > 0 else []
