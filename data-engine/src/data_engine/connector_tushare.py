"""A 股数据连接器：通过 Tushare 拉取 A 股/北交所日线/分钟线，归一化为 core.OHLCV。"""

from __future__ import annotations
from functools import wraps
from pathlib import Path
import pickle
import hashlib
import time
import os

import datetime as dt
from typing import Callable, Any, List

from core import OHLCV
from core.ashare_symbol import (
    ashare_symbol_to_tushare_ts_code,
    normalize_ashare_symbol,
)

try:
    import tushare as ts
    import pandas as pd
except ImportError:
    ts = None
    pd = None

# 兼容旧调用与测试
_normalize_symbol = normalize_ashare_symbol
_to_tushare_ts_code = ashare_symbol_to_tushare_ts_code


def _to_utc(dt_obj: dt.datetime) -> dt.datetime:
    """若为 naive 则视为本地时间并转为 UTC（A 股 15:00 收盘）。"""
    if dt_obj.tzinfo is None:
        dt_obj = dt_obj.replace(tzinfo=dt.timezone.utc)
    return dt_obj


def get_tushare_config():
    """获取Tushare配置"""
    config = {
        "token": os.getenv("TUSHARE_TOKEN", "").strip(),
        "request_interval": float(os.getenv("TUSHARE_REQUEST_INTERVAL", "1")),
        "max_retries": int(os.getenv("TUSHARE_MAX_RETRIES", "3")),
        "cache_dir": os.getenv("TUSHARE_CACHE_DIR", "/tmp/tushare_cache"),
        "enable_cache": os.getenv("TUSHARE_ENABLE_CACHE", "true").lower() == "true",
        "cache_ttl": int(os.getenv("TUSHARE_CACHE_TTL", "24")),
        "output_format": os.getenv("TUSHARE_OUTPUT_FORMAT", "csv"),
        "default_adjust": os.getenv("TUSHARE_DEFAULT_ADJUST", "qfq"),
    }
    return config


def _init_tushare() -> bool:
    """初始化Tushare，设置token"""
    if ts is None:
        return False

    config = get_tushare_config()
    token = config["token"]

    if not token:
        print("警告: 未设置TUSHARE_TOKEN环境变量，Tushare连接器将无法使用")
        print("请设置环境变量: export TUSHARE_TOKEN='你的token'")
        print("或在.env文件中配置")
        return False

    try:
        ts.set_token(token)
        return True
    except Exception as e:  # pylint: disable=broad-exception-caught  # external Tushare API
        print(f"Tushare初始化失败: {e}")
        return False


def retry_on_failure(max_retries: int = None, delay: float = None):
    """重试装饰器"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            config = get_tushare_config()
            retries = max_retries or config["max_retries"]
            retry_delay = delay or config["request_interval"]

            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:  # pylint: disable=broad-exception-caught  # external Tushare API
                    if attempt == retries - 1:
                        raise
                    print(
                        f"尝试 {attempt + 1}/{retries} 失败: {e}, "
                        f"{retry_delay}秒后重试..."
                    )
                    time.sleep(retry_delay)
            return None

        return wrapper

    return decorator


def get_cache_key(func_name: str, *args, **kwargs) -> str:
    """生成缓存键"""
    key_data = f"{func_name}:{args}:{sorted(kwargs.items())}"
    return hashlib.md5(key_data.encode()).hexdigest()


def get_cache_path(cache_key: str) -> Path:
    """获取缓存文件路径"""
    config = get_tushare_config()
    cache_dir = Path(config["cache_dir"])
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{cache_key}.pkl"


def is_cache_valid(cache_path: Path) -> bool:
    """检查缓存是否有效"""
    config = get_tushare_config()
    if not config["enable_cache"]:
        return False

    if not cache_path.exists():
        return False

    # 检查缓存是否过期
    cache_age = time.time() - cache_path.stat().st_mtime
    max_age = config["cache_ttl"] * 3600  # 转换为秒

    return cache_age < max_age


def load_from_cache(cache_path: Path) -> Any:
    """从缓存加载数据"""
    try:
        with open(cache_path, "rb") as f:
            return pickle.load(f)
    except Exception as e:  # pylint: disable=broad-exception-caught  # external Tushare API
        print(f"加载缓存失败: {e}")
        return None


def save_to_cache(cache_path: Path, data: Any) -> bool:
    """保存数据到缓存"""
    try:
        with open(cache_path, "wb") as f:
            pickle.dump(data, f)
        return True
    except Exception as e:  # pylint: disable=broad-exception-caught  # external Tushare API
        print(f"保存缓存失败: {e}")
        return False


def validate_ohlcv_data(data: List[OHLCV]) -> tuple[bool, str]:
    """验证OHLCV数据质量"""
    if not data:
        return False, "数据为空"

    # 检查数据完整性
    for i, ohlcv in enumerate(data):
        # 检查价格数据
        if ohlcv.open <= 0 or ohlcv.high <= 0 or ohlcv.low <= 0 or ohlcv.close <= 0:
            return False, f"第{i}条数据价格异常: open={
                ohlcv.open}, high={
                ohlcv.high}, low={
                ohlcv.low}, close={
                ohlcv.close}"

        # 检查价格关系
        if ohlcv.high < ohlcv.low:
            return False, f"第{i}条数据: 最高价({ohlcv.high}) < 最低价({ohlcv.low})"

        if ohlcv.high < ohlcv.open or ohlcv.high < ohlcv.close:
            return False, f"第{i}条数据: 最高价({ohlcv.high})不是最高值"

        if ohlcv.low > ohlcv.open or ohlcv.low > ohlcv.close:
            return False, f"第{i}条数据: 最低价({ohlcv.low})不是最低值"

        # 检查成交量
        if ohlcv.volume < 0:
            return False, f"第{i}条数据: 成交量({ohlcv.volume})为负数"

    # 检查时间顺序（应该是倒序，最新在前）
    for i in range(len(data) - 1):
        if data[i].timestamp < data[i + 1].timestamp:
            return False, f"时间顺序异常: 第{i}条时间({data[i].timestamp}) < 第{i +
                                                                     1}条时间({data[i +
                                                                                 1].timestamp})"

    return True, "数据质量正常"


def log_data_stats(data: List[OHLCV], symbol: str):
    """记录数据统计信息"""
    if not data:
        print(f"{symbol}: 无数据")
        return

    print(f"{symbol}: 获取到 {len(data)} 条数据")
    print(f"  时间范围: {data[-1].timestamp.date()} 到 {data[0].timestamp.date()}")
    print(f"  最新收盘价: {data[0].close:.2f}")
    print(f"  平均成交量: {sum(d.volume for d in data) / len(data):,.0f}")

    # 检查数据质量
    is_valid, message = validate_ohlcv_data(data)
    if is_valid:
        print(f"  ✓ 数据质量: {message}")
    else:
        print(f"  ⚠ 数据质量问题: {message}")


def cached(func: Callable) -> Callable:
    """缓存装饰器"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        config = get_tushare_config()
        if not config["enable_cache"]:
            return func(*args, **kwargs)

        # 生成缓存键
        cache_key = get_cache_key(func.__name__, *args, **kwargs)
        cache_path = get_cache_path(cache_key)

        # 检查缓存
        if is_cache_valid(cache_path):
            cached_data = load_from_cache(cache_path)
            if cached_data is not None:
                print(f"使用缓存数据: {cache_path.name}")
                return cached_data

        # 获取新数据
        data = func(*args, **kwargs)

        # 保存缓存
        if data is not None:
            save_to_cache(cache_path, data)

        return data

    return wrapper


@retry_on_failure()
@cached
def _fetch_hist_df(code: str, start_date: str, end_date: str, period: str, adjust: str = ""):  # pylint: disable=unused-argument
    """拉取日/周/月 K 线 DataFrame，使用Tushare接口"""
    if ts is None or pd is None:
        raise ImportError("Tushare或pandas未安装")

    if not _init_tushare():
        raise RuntimeError("Tushare初始化失败")

    # 初始化pro接口
    pro = ts.pro_api()

    ts_code = ashare_symbol_to_tushare_ts_code(code)

    try:
        if period == "daily":
            # 日线数据
            df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            if df.empty:
                raise ValueError(f"未找到{ts_code}在{start_date}到{end_date}的数据")

            # 重命名列以匹配标准格式
            df = df.rename(
                columns={
                    "trade_date": "date",
                    "ts_code": "code",
                    "open": "open",
                    "high": "high",
                    "low": "low",
                    "close": "close",
                    "vol": "volume",
                    "amount": "amount",
                }
            )

            # 转换日期格式
            df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
            df = df.sort_values("date", ascending=False)

            return df

        if period == "weekly":
            # 周线数据
            df = pro.weekly(ts_code=ts_code, start_date=start_date, end_date=end_date)
            if df.empty:
                raise ValueError(f"未找到{ts_code}周线数据")

            df = df.rename(
                columns={
                    "trade_date": "date",
                    "ts_code": "code",
                    "open": "open",
                    "high": "high",
                    "low": "low",
                    "close": "close",
                    "vol": "volume",
                    "amount": "amount",
                }
            )

            df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
            df = df.sort_values("date", ascending=False)

            return df

        if period == "monthly":  # pylint: disable=no-else-return
            # 月线数据
            df = pro.monthly(ts_code=ts_code, start_date=start_date, end_date=end_date)
            if df.empty:
                raise ValueError(f"未找到{ts_code}月线数据")

            df = df.rename(
                columns={
                    "trade_date": "date",
                    "ts_code": "code",
                    "open": "open",
                    "high": "high",
                    "low": "low",
                    "close": "close",
                    "vol": "volume",
                    "amount": "amount",
                }
            )

            df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
            df = df.sort_values("date", ascending=False)

            return df

        else:
            raise ValueError(f"不支持的周期: {period}")

    except Exception as e:  # pylint: disable=broad-exception-caught  # external Tushare API
        print(f"Tushare获取数据失败: {e}")
        raise


def fetch_ohlcv(
    code: str,
    start_date: str,
    end_date: str,
    period: str = "daily",
    adjust: str = "",
) -> List[OHLCV]:
    """
    拉取 A 股/北交所历史 K 线数据，返回 OHLCV 对象列表。

    Args:
        code: 股票代码，如 "000001" 或 "600519"
        start_date: 开始日期，格式 "YYYYMMDD"
        end_date: 结束日期，格式 "YYYYMMDD"
        period: 周期，"daily"（日线）、"weekly"（周线）、"monthly"（月线）
        adjust: 复权类型，"qfq"（前复权）、"hfq"（后复权）、""（不复权）

    Returns:
        List[OHLCV]: OHLCV 对象列表，按时间倒序排列（最新在前）

    Raises:
        ImportError: Tushare 未安装
        ValueError: 参数错误或数据为空
        RuntimeError: Tushare 初始化失败
    """
    if ts is None:
        raise ImportError("Tushare 未安装，请运行: pip install tushare")

    # 拉取 DataFrame
    df = _fetch_hist_df(code, start_date, end_date, period, adjust)

    if df.empty:
        raise ValueError(f"未找到 {code} 在 {start_date} 到 {end_date} 的{period}数据")

    # 转换为 OHLCV 对象列表
    ohlcv_list = []
    for _, row in df.iterrows():
        # 兼容 pandas Timestamp 和 plain datetime
        date_val = row["date"]
        if hasattr(date_val, "to_pydatetime"):
            ts_utc = _to_utc(date_val.to_pydatetime())
        else:
            ts_utc = _to_utc(date_val)
        ohlcv = OHLCV(
            symbol=normalize_ashare_symbol(code),
            timestamp=ts_utc,
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row.get("volume", 0)),
            interval="1d" if period == "daily" else "1w" if period == "weekly" else "1M",
        )
        ohlcv_list.append(ohlcv)

    # 记录统计信息和验证数据质量
    log_data_stats(ohlcv_list, code)

    return ohlcv_list


def fetch_stock_basic() -> pd.DataFrame:
    """
    获取股票基本信息

    Returns:
        pd.DataFrame: 包含股票基本信息的DataFrame
    """
    if ts is None or pd is None:
        raise ImportError("Tushare或pandas未安装")

    if not _init_tushare():
        raise RuntimeError("Tushare初始化失败")

    pro = ts.pro_api()

    try:
        # 获取所有上市股票
        df = pro.stock_basic(
            exchange="",
            list_status="L",
            fields="ts_code,symbol,name,area,industry,list_date,market,is_hs",
        )
        return df
    except Exception as e:  # pylint: disable=broad-exception-caught  # external Tushare API
        print(f"获取股票基本信息失败: {e}")
        raise


def fetch_realtime_quotes(codes: List[str]) -> pd.DataFrame:
    """
    获取实时行情数据

    Args:
        codes: 股票代码列表，如 ["000001", "600519"]

    Returns:
        pd.DataFrame: 实时行情数据
    """
    if ts is None or pd is None:
        raise ImportError("Tushare或pandas未安装")

    try:
        # 注意：此函数可能需要相应权限
        normalized_codes = [
            normalize_ashare_symbol(code).split(".", maxsplit=1)[0] for code in codes
        ]
        df = ts.get_realtime_quotes(normalized_codes)
        return df
    except Exception as e:  # pylint: disable=broad-exception-caught  # external Tushare API
        print(f"获取实时行情失败: {e}")
        raise


def fetch_financial_data(
    code: str, report_type: str = "income", start_date: str = "", end_date: str = ""
) -> pd.DataFrame:
    """
    获取财务数据

    Args:
        code: 股票代码
        report_type: 报表类型，"income"(利润表), "balancesheet"(资产负债表), "cashflow"(现金流量表)
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        pd.DataFrame: 财务数据
    """
    if ts is None or pd is None:
        raise ImportError("Tushare或pandas未安装")

    if not _init_tushare():
        raise RuntimeError("Tushare初始化失败")

    pro = ts.pro_api()
    ts_code = ashare_symbol_to_tushare_ts_code(code)

    try:
        if report_type == "income":
            df = pro.income(ts_code=ts_code, start_date=start_date, end_date=end_date)
        elif report_type == "balancesheet":
            df = pro.balancesheet(ts_code=ts_code, start_date=start_date, end_date=end_date)
        elif report_type == "cashflow":
            df = pro.cashflow(ts_code=ts_code, start_date=start_date, end_date=end_date)
        else:
            raise ValueError(f"不支持的报表类型: {report_type}")

        return df
    except Exception as e:  # pylint: disable=broad-exception-caught  # external Tushare API
        print(f"获取财务数据失败: {e}")
        raise


# 测试函数
def test_tushare_connector():
    """测试Tushare连接器"""
    print("测试Tushare连接器...")

    # 检查环境变量
    token = os.getenv("TUSHARE_TOKEN")
    if not token:
        print("⚠ 未设置TUSHARE_TOKEN环境变量")
        print("请设置: export TUSHARE_TOKEN='你的token'")
        return False

    try:
        # 测试初始化
        if not _init_tushare():
            print("✗ Tushare初始化失败")
            return False

        print("✓ Tushare初始化成功")

        # 测试获取股票基本信息
        print("测试获取股票基本信息...")
        pro = ts.pro_api()
        df = pro.stock_basic(ts_code="000001.SZ", fields="ts_code,name,industry,list_date")
        if not df.empty:
            print(f"✓ 获取股票信息成功: {df.iloc[0]['name']}")
        else:
            print("⚠ 获取股票信息返回空数据")

        return True

    except Exception as e:  # pylint: disable=broad-exception-caught  # external Tushare API
        print(f"✗ 测试失败: {e}")
        return False


if __name__ == "__main__":
    # 直接运行测试
    if test_tushare_connector():
        print("Tushare连接器测试通过！")
    else:
        print("Tushare连接器测试失败，请检查配置。")
