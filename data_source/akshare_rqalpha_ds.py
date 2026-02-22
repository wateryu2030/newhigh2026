#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKShare → RQAlpha 数据源适配器
核心定位：全品类金融数据供给引擎，为 RQAlpha 提供标准化数据接口

职责：
1. 调用 AKShare API 获取 A 股、期货、宏观等全品类数据
2. 转换为 RQAlpha 兼容的数据格式（字段对齐、时间戳标准化）
3. 提供数据缓存机制，避免重复请求
4. 处理数据缺失和请求失败的异常情况
"""
import warnings
from typing import Optional, Dict, Iterable, List, Union, Tuple
from datetime import datetime, date, timedelta
import numpy as np
import pandas as pd

try:
    import akshare as ak
except ImportError:
    raise ImportError("请先安装 akshare: pip install akshare")

from rqalpha.interface import AbstractDataSource, ExchangeRate
from rqalpha.model.instrument import Instrument
from rqalpha.const import INSTRUMENT_TYPE, MARKET, TRADING_CALENDAR_TYPE
from rqalpha.utils.datetime_func import convert_date_to_int, convert_int_to_date


class AKShareRQAlphaDataSource(AbstractDataSource):
    """
    AKShare → RQAlpha 数据源适配器
    
    核心功能：
    - 直接调用 AKShare API 获取 A 股日线数据
    - 自动转换日期格式（AKShare: 20240401 → RQAlpha: datetime）
    - 字段映射对齐（AKShare 字段 → RQAlpha Bar 字段）
    - 数据缓存（避免重复请求）
    """
    
    def __init__(self, cache_ttl_hours: int = 1):
        """
        初始化数据源适配器
        
        Args:
            cache_ttl_hours: 缓存过期时间（小时），默认 1 小时
        """
        self.cache_ttl_hours = cache_ttl_hours
        self._data_cache: Dict[str, Dict] = {}  # 缓存：{cache_key: {data: DataFrame, timestamp: datetime}}
        self._instruments_cache: Dict[str, Instrument] = {}  # Instrument 缓存
        
    def _convert_akshare_date(self, ak_date: str) -> datetime:
        """
        AKShare 日期格式（20240401）转换为 RQAlpha 的 datetime
        
        Args:
            ak_date: AKShare 日期字符串，格式 YYYYMMDD
            
        Returns:
            datetime 对象
        """
        try:
            return datetime.strptime(ak_date, "%Y%m%d")
        except ValueError:
            # 尝试其他格式
            try:
                return pd.to_datetime(ak_date)
            except:
                raise ValueError(f"无法解析日期格式: {ak_date}")
    
    def _convert_date_to_akshare(self, dt: datetime) -> str:
        """
        RQAlpha datetime 转换为 AKShare 日期格式（YYYYMMDD）
        
        Args:
            dt: datetime 对象
            
        Returns:
            YYYYMMDD 格式字符串
        """
        if isinstance(dt, str):
            dt = pd.to_datetime(dt)
        return dt.strftime("%Y%m%d")
    
    def _get_cache_key(self, order_book_id: str, start_date: str, end_date: str) -> str:
        """生成缓存键"""
        return f"{order_book_id}_{start_date}_{end_date}"
    
    def _is_cache_valid(self, cache_entry: Dict) -> bool:
        """检查缓存是否有效"""
        if not cache_entry:
            return False
        timestamp = cache_entry.get('timestamp')
        if not timestamp:
            return False
        age = datetime.now() - timestamp
        return age < timedelta(hours=self.cache_ttl_hours)
    
    def _get_akshare_stock_data(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        从 AKShare 获取 A 股日线数据
        
        Args:
            symbol: 股票代码（如 "600745"）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            
        Returns:
            DataFrame，包含日线数据，字段已对齐 RQAlpha 格式
        """
        cache_key = self._get_cache_key(f"{symbol}.XSHG", start_date, end_date)
        
        # 检查缓存
        if cache_key in self._data_cache:
            cache_entry = self._data_cache[cache_key]
            if self._is_cache_valid(cache_entry):
                return cache_entry['data'].copy()
        
        try:
            # 调用 AKShare API 获取 A 股历史数据
            # 注意：AKShare 的 stock_zh_a_hist 需要 symbol（如 "600745"）和日期范围
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start=start_date,
                end=end_date,
                adjust="qfq"  # 前复权
            )
            
            if df is None or len(df) == 0:
                # 单日请求无数据多为节假日，不重复告警
                if start_date != end_date:
                    warnings.warn(f"AKShare 返回空数据: {symbol} {start_date}-{end_date}")
                return None
            
            # 字段映射：AKShare → RQAlpha
            # AKShare 字段: 日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额, 振幅, 涨跌幅, 涨跌额, 换手率
            # RQAlpha Bar 字段: datetime, open, close, high, low, volume, total_turnover
            
            df = df.rename(columns={
                '日期': 'datetime',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'total_turnover',
            })
            
            # 转换日期格式
            df['datetime'] = pd.to_datetime(df['datetime'])
            
            # 确保数据类型正确
            for col in ['open', 'close', 'high', 'low', 'volume', 'total_turnover']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 按日期排序
            df = df.sort_values('datetime').reset_index(drop=True)
            
            # 存入缓存
            self._data_cache[cache_key] = {
                'data': df.copy(),
                'timestamp': datetime.now()
            }
            
            return df
            
        except Exception as e:
            warnings.warn(f"获取 AKShare 数据失败 {symbol} {start_date}-{end_date}: {e}")
            return None
    
    def _create_instrument(self, order_book_id: str) -> Instrument:
        """
        创建 Instrument 对象
        
        Args:
            order_book_id: 合约代码（如 "600745.XSHG"）
            
        Returns:
            Instrument 对象
        """
        if order_book_id in self._instruments_cache:
            return self._instruments_cache[order_book_id]
        
        symbol = order_book_id.split('.')[0]
        exchange = "XSHG" if order_book_id.endswith(".XSHG") else "XSHE"
        
        ins_dict = {
            "order_book_id": order_book_id,
            "symbol": symbol,
            "type": "CS",  # 股票
            "listed_date": datetime(2000, 1, 1),
            "de_listed_date": datetime(2099, 12, 31),
            "round_lot": 100,
            "board_type": "MainBoard",
            "exchange": exchange,
        }
        
        ins = Instrument(ins_dict, market=MARKET.CN)
        self._instruments_cache[order_book_id] = ins
        return ins
    
    def get_instruments(self, id_or_syms: Optional[Iterable[str]] = None,
                       types: Optional[Iterable[INSTRUMENT_TYPE]] = None) -> Iterable[Instrument]:
        """
        获取合约列表（实现 AbstractDataSource 接口）
        
        Args:
            id_or_syms: 合约代码列表（如 ["600745.XSHG", "000001.XSHE"]）
            types: 合约类型过滤（暂不支持）
            
        Returns:
            Instrument 迭代器
        """
        if id_or_syms:
            for sym in id_or_syms:
                # 标准化格式
                if sym.endswith('.XSHE') or sym.endswith('.XSHG'):
                    order_book_id = sym
                else:
                    # 自动判断交易所
                    symbol = sym
                    order_book_id = f"{symbol}.XSHG" if symbol.startswith('6') else f"{symbol}.XSHE"
                
                yield self._create_instrument(order_book_id)
        else:
            # 如果没有指定，返回空（AKShare 是动态数据源，不预加载所有股票）
            return iter([])
    
    def get_trading_calendars(self):
        """
        获取交易日历（实现 AbstractDataSource 接口）
        
        Returns:
            交易日历字典，键为 TRADING_CALENDAR_TYPE，值为 DatetimeIndex
        """
        import pandas as pd
        # 生成一个简单的交易日历（工作日，排除周末）
        # 实际应用中可以从 AKShare 获取真实的交易日历
        start_date = pd.Timestamp('2000-01-01')
        end_date = pd.Timestamp('2099-12-31')
        # 生成工作日（周一到周五）
        dt_index = pd.bdate_range(start=start_date, end=end_date, freq='B')
        return {TRADING_CALENDAR_TYPE.CN_STOCK: dt_index}
    
    def get_yield_curve(self, start_date, end_date, tenor=None):
        """获取国债利率（暂不支持）"""
        return None
    
    def get_dividend(self, instrument: Instrument):
        """获取分红信息（暂不支持）"""
        return None
    
    def get_split(self, instrument: Instrument):
        """获取拆股信息（暂不支持）"""
        return None
    
    def get_bar(self, instrument: Instrument, dt: Union[datetime, date], frequency: str):
        """
        获取单个 bar（实现 AbstractDataSource 接口）
        
        Args:
            instrument: 合约对象
            dt: 日期时间
            frequency: 频率（目前只支持 "1d"）
            
        Returns:
            Bar 对象（numpy structured array）或 None
        """
        if frequency != '1d':
            return None
        
        order_book_id = instrument.order_book_id
        symbol = order_book_id.split('.')[0]
        
        # 转换为 AKShare 日期格式
        dt_obj = dt if isinstance(dt, datetime) else datetime.combine(dt, datetime.min.time())
        start_date = self._convert_date_to_akshare(dt_obj)
        end_date = start_date  # 单日数据
        
        # 获取数据（会使用缓存）
        df = self._get_akshare_stock_data(symbol, start_date, end_date)
        
        if df is None or len(df) == 0:
            return None
        
        # 查找对应日期的 bar
        target_date = pd.to_datetime(dt_obj).normalize()
        matching_rows = df[df['datetime'].dt.normalize() == target_date]
        
        if len(matching_rows) == 0:
            return None
        
        row = matching_rows.iloc[0]
        
        # 转换为 RQAlpha Bar 格式（numpy structured array）
        dt_int = np.uint64(convert_date_to_int(dt_obj))
        
        bar = np.array([(
            dt_int,
            float(row['open']) if pd.notna(row['open']) else 0.0,
            float(row['high']) if pd.notna(row['high']) else 0.0,
            float(row['low']) if pd.notna(row['low']) else 0.0,
            float(row['close']) if pd.notna(row['close']) else 0.0,
            float(row['volume']) if pd.notna(row['volume']) else 0.0,
            float(row['total_turnover']) if pd.notna(row.get('total_turnover', 0)) else 0.0,
        )], dtype=[
            ('datetime', 'u8'),
            ('open', 'f8'),
            ('high', 'f8'),
            ('low', 'f8'),
            ('close', 'f8'),
            ('volume', 'f8'),
            ('total_turnover', 'f8'),
        ])
        
        return bar[0]
    
    def history_bars(self, instrument: Instrument, bar_count: Optional[int],
                    frequency: str, fields: Union[str, List[str], None],
                    dt: datetime, skip_suspended: bool = True,
                    include_now: bool = False, adjust_type: str = 'pre',
                    adjust_orig: Optional[datetime] = None) -> Optional[np.ndarray]:
        """
        获取历史 bar 数据（实现 AbstractDataSource 接口）
        
        Args:
            instrument: 合约对象
            bar_count: 获取的历史数据数量，None 表示获取尽可能多的历史数据
            frequency: 周期频率（目前只支持 "1d"）
            fields: 返回数据字段（如 "close", ["open", "close"]）
            dt: 截止日期时间
            skip_suspended: 是否跳过停牌日
            include_now: 是否包含当前 bar
            adjust_type: 复权类型
            adjust_orig: 复权基准日期
            
        Returns:
            numpy structured array 或 None
        """
        if frequency != '1d':
            return None
        
        order_book_id = instrument.order_book_id
        symbol = order_book_id.split('.')[0]
        
        # 计算需要获取的数据范围
        # 如果 bar_count 为 None，获取尽可能多的数据（比如最近 1 年）
        if bar_count is None:
            bar_count = 250  # 约 1 年的交易日
        
        # 计算开始日期（往前推 bar_count 个交易日，约 bar_count * 1.5 自然日）
        end_dt_obj = dt if isinstance(dt, datetime) else datetime.combine(dt, datetime.min.time())
        start_dt_obj = end_dt_obj - timedelta(days=int(bar_count * 1.5))
        
        start_date = self._convert_date_to_akshare(start_dt_obj)
        end_date = self._convert_date_to_akshare(end_dt_obj)
        
        # 获取数据（会使用缓存）
        df = self._get_akshare_stock_data(symbol, start_date, end_date)
        
        if df is None or len(df) == 0:
            return None
        
        # 过滤日期范围（只取 <= dt 的数据）
        df = df[df['datetime'] <= pd.to_datetime(end_dt_obj)]
        
        if len(df) == 0:
            return None
        
        # 转换为 RQAlpha Bar 格式
        bars = []
        for _, row in df.iterrows():
            dt_int = np.uint64(convert_date_to_int(row['datetime']))
            bar = (
                dt_int,
                float(row['open']) if pd.notna(row['open']) else 0.0,
                float(row['high']) if pd.notna(row['high']) else 0.0,
                float(row['low']) if pd.notna(row['low']) else 0.0,
                float(row['close']) if pd.notna(row['close']) else 0.0,
                float(row['volume']) if pd.notna(row['volume']) else 0.0,
                float(row['total_turnover']) if pd.notna(row.get('total_turnover', 0)) else 0.0,
            )
            bars.append(bar)
        
        if not bars:
            return None
        
        bars_array = np.array(bars, dtype=[
            ('datetime', 'u8'),
            ('open', 'f8'),
            ('high', 'f8'),
            ('low', 'f8'),
            ('close', 'f8'),
            ('volume', 'f8'),
            ('total_turnover', 'f8'),
        ])
        
        # 如果指定了 bar_count，只返回最后 bar_count 条
        if bar_count is not None and len(bars_array) > bar_count:
            bars_array = bars_array[-bar_count:]
        
        # 如果指定了 fields，只返回指定字段
        if fields is not None:
            if isinstance(fields, str):
                return bars_array[fields]
            else:
                return bars_array[fields]
        
        return bars_array
    
    def get_bar_range(self, instrument: Instrument, start_dt: datetime, end_dt: datetime, frequency: str):
        """
        获取 bar 序列（实现 AbstractDataSource 接口）
        
        Args:
            instrument: 合约对象
            start_dt: 开始日期
            end_dt: 结束日期
            frequency: 频率（目前只支持 "1d"）
            
        Returns:
            Bar 数组（numpy structured array）或 None
        """
        if frequency != '1d':
            return None
        
        order_book_id = instrument.order_book_id
        symbol = order_book_id.split('.')[0]
        
        # 转换为 AKShare 日期格式
        start_date = self._convert_date_to_akshare(start_dt)
        end_date = self._convert_date_to_akshare(end_dt)
        
        # 获取数据（会使用缓存）
        df = self._get_akshare_stock_data(symbol, start_date, end_date)
        
        if df is None or len(df) == 0:
            return None
        
        # 过滤日期范围
        df = df[(df['datetime'] >= pd.to_datetime(start_dt)) & 
                (df['datetime'] <= pd.to_datetime(end_dt))]
        
        if len(df) == 0:
            return None
        
        # 转换为 RQAlpha Bar 格式
        bars = []
        for _, row in df.iterrows():
            dt_int = np.uint64(convert_date_to_int(row['datetime']))
            bar = (
                dt_int,
                float(row['open']) if pd.notna(row['open']) else 0.0,
                float(row['high']) if pd.notna(row['high']) else 0.0,
                float(row['low']) if pd.notna(row['low']) else 0.0,
                float(row['close']) if pd.notna(row['close']) else 0.0,
                float(row['volume']) if pd.notna(row['volume']) else 0.0,
                float(row['total_turnover']) if pd.notna(row.get('total_turnover', 0)) else 0.0,
            )
            bars.append(bar)
        
        if not bars:
            return None
        
        return np.array(bars, dtype=[
            ('datetime', 'u8'),
            ('open', 'f8'),
            ('high', 'f8'),
            ('low', 'f8'),
            ('close', 'f8'),
            ('volume', 'f8'),
            ('total_turnover', 'f8'),
        ])
    
    def get_order_book_id_list(self):
        """获取所有合约代码列表（动态数据源，返回空）"""
        return []
    
    def get_all_instruments(self):
        """获取所有合约（动态数据源，返回空）"""
        return []
    
    def get_exchange(self, order_book_id: str):
        """获取交易所信息"""
        if order_book_id.endswith('.XSHG'):
            return 'XSHG'
        elif order_book_id.endswith('.XSHE'):
            return 'XSHE'
        else:
            return 'XSHG' if order_book_id.startswith('6') else 'XSHE'
    
    def get_commission(self, instrument: Instrument):
        """获取手续费（默认值）"""
        return 0.0003  # 万三
    
    def get_margin(self, instrument: Instrument):
        """获取保证金（股票不需要）"""
        return 1.0
    
    def get_contract_multiplier(self, instrument: Instrument):
        """获取合约乘数（股票为 1）"""
        return 1.0
    
    def get_settlement_price(self, instrument: Instrument, date: datetime):
        """获取结算价（股票使用收盘价）"""
        bar = self.get_bar(instrument, date, '1d')
        if bar is not None:
            return bar['close']
        return None
    
    def get_settlement_list(self, instrument: Instrument, start_date: datetime, end_date: datetime):
        """获取结算价列表"""
        bars = self.get_bar_range(instrument, start_date, end_date, '1d')
        if bars is not None:
            return bars['close']
        return None
    
    def get_exchange_rate(self, trading_date: date, local: MARKET, settlement: MARKET = MARKET.CN) -> ExchangeRate:
        """
        获取汇率（实现 AbstractDataSource 接口）
        
        Args:
            trading_date: 交易日期
            local: 本地市场（MARKET 枚举）
            settlement: 结算市场（默认 CN）
            
        Returns:
            ExchangeRate 对象（NamedTuple）
        """
        # A 股使用人民币，汇率始终为 1.0
        # ExchangeRate 是 NamedTuple，需要按顺序传递所有字段
        return ExchangeRate(
            bid_reference=1.0,
            ask_reference=1.0,
            bid_settlement_sh=1.0,
            ask_settlement_sh=1.0,
            bid_settlement_sz=1.0,
            ask_settlement_sz=1.0
        )
    
    def get_trading_calendar_type(self, order_book_id: str):
        """获取交易日历类型"""
        return TRADING_CALENDAR_TYPE.CN
    
    def get_trading_minutes_for(self, order_book_id: str, dt: datetime):
        """获取交易分钟数（A 股：240 分钟）"""
        return 240
    
    def is_suspended(self, order_book_id: str, dates: List) -> List[bool]:
        """
        检查股票是否停牌（实现 AbstractDataSource 接口）
        
        Args:
            order_book_id: 合约代码
            dates: 日期列表
            
        Returns:
            布尔值列表，True 表示停牌
        """
        # AKShare 数据源暂不支持停牌检查，默认返回 False（未停牌）
        return [False] * len(dates)
    
    def is_st_stock(self, order_book_id: str, dates: List) -> List[bool]:
        """
        检查股票是否为 ST 股票（实现 AbstractDataSource 接口）
        
        Args:
            order_book_id: 合约代码
            dates: 日期列表
            
        Returns:
            布尔值列表，True 表示 ST 股票
        """
        # AKShare 数据源暂不支持 ST 检查，默认返回 False
        return [False] * len(dates)
    
    def get_open_auction_bar(self, instrument: Instrument, dt: datetime):
        """获取集合竞价 bar（暂不支持）"""
        return None
    
    def get_algo_bar(self, instrument: Instrument, start_min: int, end_min: int, dt: datetime):
        """获取算法 bar（暂不支持）"""
        return None
    
    def get_history_ticks(self, instrument: Instrument, count: int, dt: datetime):
        """获取历史 tick 数据（暂不支持）"""
        return None
    
    def get_current_tick(self, instrument: Instrument, dt: datetime):
        """获取当前 tick（暂不支持）"""
        return None
    
    def get_limit_up(self, order_book_id: str) -> float:
        """获取涨停价（暂不支持，返回 NaN）"""
        return np.nan
    
    def get_limit_down(self, order_book_id: str) -> float:
        """获取跌停价（暂不支持，返回 NaN）"""
        return np.nan
    
    def get_a1(self, order_book_id: str) -> float:
        """获取卖一价（暂不支持，返回 NaN）"""
        return np.nan
    
    def get_b1(self, order_book_id: str) -> float:
        """获取买一价（暂不支持，返回 NaN）"""
        return np.nan
    
    def available_data_range(self, frequency):
        """
        可用数据范围（实现 AbstractDataSource 接口）
        
        AKShare 是动态数据源，理论上可以获取任意时间范围的数据
        返回一个合理的默认范围
        
        Args:
            frequency: 频率（如 "1d"）
            
        Returns:
            (start_date, end_date) 元组
        """
        # AKShare 可以获取从 2000 年到当前的数据
        # 返回一个宽泛的范围，让 RQAlpha 使用配置中的日期范围
        from datetime import date
        return date(2000, 1, 1), date(2099, 12, 31)
