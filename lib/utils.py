"""
工具函数库

提供常用的工具函数，避免各模块重复实现。
"""

from __future__ import annotations
from typing import Optional, Tuple


def parse_symbol(symbol: str) -> Tuple[str, str]:
    """
    解析股票代码

    Args:
        symbol: 股票代码 (如 "000001", "000001.SZ", "600000.SH")

    Returns:
        (代码，交易所) 元组

    Example:
        >>> parse_symbol("000001")
        ('000001', 'SZ')
        >>> parse_symbol("600000.SH")
        ('600000', 'SH')
    """
    symbol = symbol.strip().upper()

    # 已有交易所后缀
    if "." in symbol:
        code, exchange = symbol.split(".", 1)
        return code, exchange

    # 纯数字代码，根据前缀判断交易所
    if symbol.isdigit() and len(symbol) == 6:
        if symbol.startswith("6"):
            return symbol, "SH"
        elif symbol.startswith(("0", "3")):
            return symbol, "SZ"
        elif symbol.startswith(("4", "8")):
            return symbol, "BJ"

    return symbol, ""


def is_ashare_symbol(symbol: str) -> bool:
    """
    判断是否为 A 股代码

    Args:
        symbol: 股票代码

    Returns:
        True 如果是 A 股代码
    """
    code, _ = parse_symbol(symbol)
    return len(code) == 6 and code.isdigit()


def format_number(value: float, decimals: int = 2) -> str:
    """
    格式化数字显示

    Args:
        value: 数值
        decimals: 小数位数

    Returns:
        格式化后的字符串

    Example:
        >>> format_number(1234567.89)
        '1,234,567.89'
        >>> format_number(0.1234, 4)
        '0.1234'
    """
    if value is None:
        return "N/A"

    try:
        if abs(value) >= 1e8:
            return f"{value / 1e8:.{decimals}f}亿"
        elif abs(value) >= 1e4:
            return f"{value / 1e4:.{decimals}f}万"
        else:
            return f"{value:,.{decimals}f}"
    except Exception:
        return str(value)


def normalize_code(code: str) -> str:
    """
    标准化股票代码 (6 位数字)

    Args:
        code: 股票代码

    Returns:
        6 位数字代码
    """
    code = code.strip()
    # 移除交易所后缀
    if "." in code:
        code = code.split(".")[0]
    # 补齐 6 位
    return code.zfill(6)


def is_market_open() -> bool:
    """
    判断当前是否为交易时间

    Returns:
        True 如果是交易时间
    """
    import datetime

    now = datetime.datetime.now()

    # 周末
    if now.weekday() >= 5:
        return False

    # 交易时段 (简化版，不考虑节假日)
    morning_start = now.replace(hour=9, minute=30, second=0, microsecond=0)
    morning_end = now.replace(hour=11, minute=30, second=0, microsecond=0)
    afternoon_start = now.replace(hour=13, minute=0, second=0, microsecond=0)
    afternoon_end = now.replace(hour=15, minute=0, second=0, microsecond=0)

    return (morning_start <= now <= morning_end or
            afternoon_start <= now <= afternoon_end)
