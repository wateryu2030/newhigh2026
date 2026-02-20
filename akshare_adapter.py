#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKShare 数据适配器 - 将 AKShare 数据转换为 RQAlpha 可用的格式
这是一个简化版本，主要用于演示如何整合 akshare 和 rqalpha
"""
import numpy as np
import pandas as pd
from datetime import datetime, date
from typing import Optional, Iterable, List, Dict, Union
from rqalpha.interface import AbstractDataSource
from rqalpha.model.instrument import Instrument
from rqalpha.const import INSTRUMENT_TYPE, MARKET, TRADING_CALENDAR_TYPE
from rqalpha.utils.datetime_func import convert_date_to_int, convert_int_to_date
import akshare as ak


class AKShareDataSource(AbstractDataSource):
    """
    使用 AKShare 作为数据源的适配器
    注意：这是一个简化实现，主要用于演示
    """
    
    def __init__(self, base_config):
        self._instruments = {}
        self._cache = {}  # 缓存历史数据
        
    def get_instruments(self, id_or_syms: Optional[Iterable[str]] = None, 
                       types: Optional[Iterable[INSTRUMENT_TYPE]] = None) -> Iterable[Instrument]:
        """
        获取合约列表
        简化实现：只支持 A 股股票
        """
        if id_or_syms:
            for sym in id_or_syms:
                # 转换格式：000001 -> 000001.XSHE 或 000001.XSHG
                if sym.endswith('.XSHE') or sym.endswith('.XSHG'):
                    order_book_id = sym
                    symbol = sym.split('.')[0]
                else:
                    symbol = sym
                    # 简单判断：6开头是上海，其他是深圳
                    order_book_id = f"{symbol}.XSHG" if symbol.startswith('6') else f"{symbol}.XSHE"
                
                if order_book_id not in self._instruments:
                    ins = Instrument(
                        order_book_id=order_book_id,
                        symbol=symbol,
                        type=INSTRUMENT_TYPE.CS,
                        listed_date=datetime(2000, 1, 1),
                        de_listed_date=datetime(2099, 12, 31),
                        market=MARKET.CN,
                    )
                    self._instruments[order_book_id] = ins
                    yield ins
        else:
            # 返回已注册的合约
            for ins in self._instruments.values():
                yield ins
    
    def get_bar(self, instrument: Instrument, dt: Union[datetime, date], frequency: str):
        """获取单个 bar"""
        if frequency != '1d':
            return None
        
        bars = self._get_bars(instrument)
        if bars is None or len(bars) == 0:
            return None
        
        dt_int = np.uint64(convert_date_to_int(dt))
        pos = np.searchsorted(bars['datetime'], dt_int)
        if pos >= len(bars) or bars['datetime'][pos] != dt_int:
            return None
        
        return bars[pos]
    
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
        """从 AKShare 获取并缓存历史数据"""
        if instrument.order_book_id in self._cache:
            return self._cache[instrument.order_book_id]
        
        try:
            symbol = instrument.symbol
            # 使用 AKShare 获取历史数据
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date="20200101",
                end_date="20251231",
                adjust="qfq"  # 前复权
            )
            
            if df is None or len(df) == 0:
                return None
            
            # 转换为 rqalpha 格式
            df['datetime'] = pd.to_datetime(df['日期']).apply(
                lambda x: np.uint64(convert_date_to_int(x.date()))
            )
            
            # 构建结构化数组
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
            bars['datetime'] = df['datetime'].values
            bars['open'] = df['开盘'].values
            bars['close'] = df['收盘'].values
            bars['high'] = df['最高'].values
            bars['low'] = df['最低'].values
            bars['volume'] = df['成交量'].values
            bars['total_turnover'] = df['成交额'].values
            
            # 缓存数据
            self._cache[instrument.order_book_id] = bars
            return bars
            
        except Exception as e:
            print(f"获取 {instrument.order_book_id} 数据失败: {e}")
            return None
    
    def get_trading_calendars(self) -> Dict[TRADING_CALENDAR_TYPE, pd.DatetimeIndex]:
        """获取交易日历"""
        # 简化实现：返回一个基本的交易日历
        # 实际应该从 AKShare 获取交易日历
        dates = pd.date_range('2020-01-01', '2025-12-31', freq='B')
        return {TRADING_CALENDAR_TYPE.CN_STOCK: dates}
    
    def available_data_range(self, frequency):
        """可用数据范围"""
        return date(2020, 1, 1), date(2025, 12, 31)
    
    # 其他必需方法（简化实现）
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
            'limit_up': bar['close'] * 1.1,  # 简化
            'limit_down': bar['close'] * 0.9,
        }
    
    def get_settle_price(self, instrument, date):
        bar = self.get_bar(instrument, date, '1d')
        return bar['close'] if bar is not None else np.nan
    
    def get_yield_curve(self, start_date, end_date, tenor=None):
        return None
    
    def get_exchange_rate(self, trading_date: date, local: MARKET, settlement: MARKET = MARKET.CN):
        from rqalpha.interface import ExchangeRate
        return ExchangeRate(1, 1, 1, 1, 1, 1)
