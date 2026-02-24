#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库数据源适配器 - 从 DuckDB 读取数据供 RQAlpha 使用
"""
import numpy as np
import pandas as pd
from datetime import datetime, date
from typing import Optional, Iterable, List, Dict, Union
from rqalpha.interface import AbstractDataSource, ExchangeRate
from rqalpha.model.instrument import Instrument
from rqalpha.const import INSTRUMENT_TYPE, MARKET, TRADING_CALENDAR_TYPE
from rqalpha.utils.datetime_func import convert_date_to_int, convert_int_to_date
from database.duckdb_backend import get_db_backend


class DatabaseDataSource(AbstractDataSource):
    """
    从 DuckDB 读取数据的数据源适配器
    实现完整的 AbstractDataSource 接口
    """
    
    def __init__(self, base_config):
        self.db = get_db_backend()
        self._instruments = {}
        self._cache = {}
        self._load_instruments()
    
    def _load_instruments(self):
        """从数据库加载股票列表"""
        stocks = self.db.get_stocks()
        for order_book_id, symbol, name in stocks:
            # Instrument 需要字典参数
            ins_dict = {
                "order_book_id": order_book_id,
                "symbol": symbol,
                "type": "CS",
                "listed_date": datetime(2000, 1, 1),
                "de_listed_date": datetime(2099, 12, 31),
                "round_lot": 100,
                "board_type": "MainBoard",
                "exchange": "XSHG" if order_book_id.endswith(".XSHG") else "XSHE",
            }
            ins = Instrument(ins_dict, market=MARKET.CN)
            self._instruments[order_book_id] = ins
    
    def get_instruments(self, id_or_syms: Optional[Iterable[str]] = None,
                       types: Optional[Iterable[INSTRUMENT_TYPE]] = None) -> Iterable[Instrument]:
        """获取合约列表"""
        if id_or_syms:
            for sym in id_or_syms:
                # 处理格式
                if sym.endswith('.XSHE') or sym.endswith('.XSHG'):
                    order_book_id = sym
                else:
                    symbol = sym
                    order_book_id = f"{symbol}.XSHG" if symbol.startswith('6') else f"{symbol}.XSHE"
                
                if order_book_id in self._instruments:
                    yield self._instruments[order_book_id]
                else:
                    # 如果数据库中没有，创建一个临时 Instrument
                    symbol_clean = symbol if not sym.endswith(('.XSHE', '.XSHG')) else sym.split('.')[0]
                    ins_dict = {
                        "order_book_id": order_book_id,
                        "symbol": symbol_clean,
                        "type": "CS",
                        "listed_date": datetime(2000, 1, 1),
                        "de_listed_date": datetime(2099, 12, 31),
                        "round_lot": 100,
                        "board_type": "MainBoard",
                        "exchange": "XSHG" if order_book_id.endswith(".XSHG") else "XSHE",
                    }
                    ins = Instrument(ins_dict, market=MARKET.CN)
                    self._instruments[order_book_id] = ins
                    yield ins
        else:
            for ins in self._instruments.values():
                yield ins
    
    def get_bar(self, instrument: Instrument, dt: Union[datetime, date], frequency: str):
        """获取单个 bar"""
        if frequency != '1d':
            return None
        
        bars = self._get_bars(instrument)
        if bars is None or len(bars) == 0:
            return None
        
        dt_str = dt.strftime('%Y-%m-%d') if isinstance(dt, (datetime, date)) else str(dt)
        dt_int = np.uint64(convert_date_to_int(dt))
        
        # 查找对应日期的 bar
        bar_dates = bars['datetime']
        pos = np.searchsorted(bar_dates, dt_int)
        
        if pos < len(bars) and bar_dates[pos] == dt_int:
            return bars[pos]
        return None
    
    def history_bars(self, instrument: Instrument, bar_count: Optional[int],
                    frequency: str, fields: Union[str, List[str], None],
                    dt: datetime, skip_suspended: bool = True,
                    include_now: bool = False, adjust_type: str = 'pre',
                    adjust_orig: Optional[datetime] = None) -> Optional[np.ndarray]:
        """获取历史 bar 数据"""
        if frequency != '1d':
            return None
        
        bars = self._get_bars(instrument)
        if bars is None or len(bars) == 0:
            return None
        
        dt_int = np.uint64(convert_date_to_int(dt))
        i = np.searchsorted(bars['datetime'], dt_int, side='right')
        
        if bar_count is None:
            left = 0
        else:
            left = max(0, i - bar_count)
        
        result = bars[left:i]
        
        if fields is not None:
            if isinstance(fields, str):
                return result[fields]
            else:
                return result[fields]
        
        return result
    
    def _get_bars(self, instrument: Instrument) -> Optional[np.ndarray]:
        """从数据库获取并缓存历史数据"""
        if instrument.order_book_id in self._cache:
            return self._cache[instrument.order_book_id]
        
        try:
            # 从数据库获取数据
            df = self.db.get_daily_bars(instrument.order_book_id)
            
            if df is None or len(df) == 0:
                return None
            
            # 转换为 RQAlpha 格式的结构化数组
            dtype = [
                ('datetime', 'u8'),
                ('open', 'f8'),
                ('close', 'f8'),
                ('high', 'f8'),
                ('low', 'f8'),
                ('volume', 'f8'),
                ('total_turnover', 'f8'),
            ]
            
            bars = np.empty(len(df), dtype=dtype)
            bars['datetime'] = df.index.map(lambda x: np.uint64(convert_date_to_int(x.date()))).values
            bars['open'] = df['open'].values
            bars['close'] = df['close'].values
            bars['high'] = df['high'].values
            bars['low'] = df['low'].values
            bars['volume'] = df['volume'].values
            bars['total_turnover'] = df['total_turnover'].values
            
            # 缓存
            self._cache[instrument.order_book_id] = bars
            return bars
            
        except Exception as e:
            print(f"获取 {instrument.order_book_id} 数据失败: {e}")
            return None
    
    def get_trading_calendars(self) -> Dict[TRADING_CALENDAR_TYPE, pd.DatetimeIndex]:
        """获取交易日历"""
        dates = self.db.get_trading_dates()
        if dates:
            dt_index = pd.DatetimeIndex([pd.to_datetime(d) for d in dates])
        else:
            # 如果没有数据，返回默认范围
            dt_index = pd.date_range('2020-01-01', '2025-12-31', freq='B')
        return {TRADING_CALENDAR_TYPE.CN_STOCK: dt_index}
    
    def available_data_range(self, frequency):
        """可用数据范围"""
        dates = self.db.get_trading_dates()
        if dates:
            start = pd.to_datetime(dates[0]).date()
            end = pd.to_datetime(dates[-1]).date()
        else:
            start = date(2020, 1, 1)
            end = date(2025, 12, 31)
        return start, end
    
    def get_dividend(self, instrument):
        return None
    
    def get_split(self, instrument):
        return None
    
    def get_ex_cum_factor(self, instrument):
        return None
    
    def is_suspended(self, order_book_id: str, dates: List) -> List[bool]:
        return [False] * len(dates)
    
    def is_st_stock(self, order_book_id: str, dates: List) -> List[bool]:
        return [False] * len(dates)
    
    def get_open_auction_bar(self, instrument, dt):
        bar = self.get_bar(instrument, dt, '1d')
        if bar is None:
            return {'datetime': convert_date_to_int(dt), 'open': np.nan, 'volume': 0}
        return {
            'datetime': bar['datetime'],
            'open': bar['open'],
            'volume': bar['volume'],
            'limit_up': bar['close'] * 1.1,
            'limit_down': bar['close'] * 0.9,
        }
    
    def get_settle_price(self, instrument, date):
        bar = self.get_bar(instrument, date, '1d')
        return bar['close'] if bar is not None else np.nan
    
    def get_yield_curve(self, start_date, end_date, tenor=None):
        return None
    
    def get_exchange_rate(self, trading_date: date, local: MARKET, settlement: MARKET = MARKET.CN):
        return ExchangeRate(1, 1, 1, 1, 1, 1)
