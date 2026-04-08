"""
A 股 / 北交所证券代码：newhigh 统一后缀（.SH / .SZ / .BSE）、Tushare ts_code（.BJ）、astock order_book_id（.XSHG / .XSHE / .BSE）。

沪 B 股（900/901/902 开头）归为 .SH / XSHG，勿与北交所 920 等混淆。
"""

from __future__ import annotations


def strip_ashare_code(raw: str) -> str:
    """取点号前代码段（常见 6～8 位数字）。"""
    s = str(raw or "").strip()
    if not s:
        return s
    return s.split(".", maxsplit=1)[0]


def normalize_ashare_symbol(code: str) -> str:
    """
    纯代码或已带后缀 → newhigh 统一 symbol：600519.SH、000001.SZ、830799.BSE。
    """
    c = strip_ashare_code(code)
    if not c:
        return c
    if c.startswith("6"):
        return f"{c}.SH"
    if c.startswith(("900", "901", "902")):
        return f"{c}.SH"
    if len(c) == 8 or c.startswith(("4", "8", "9")):
        return f"{c}.BSE"
    return f"{c}.SZ"


def ashare_symbol_to_tushare_ts_code(code: str) -> str:
    """Tushare pro_api：北交所用 .BJ，沪深与 normalize 后缀一致。"""
    sym = normalize_ashare_symbol(code)
    if sym.endswith(".BSE"):
        return f"{sym.split('.', maxsplit=1)[0]}.BJ"
    return sym


def normalize_ashare_symbol_bj_display(code: str) -> str:
    """
    对外展示 / 部分行情接口用北交所后缀 .BJ；沪深与 normalize_ashare_symbol 一致。
    入参常为 6 位纯代码（Hongshan 路由等）。
    """
    sym = normalize_ashare_symbol(code)
    c = strip_ashare_code(sym)
    if sym.endswith(".BSE"):
        return f"{c}.BJ"
    return sym


def order_book_id_to_newhigh_symbol(order_book_id: str) -> str:
    """
    astock order_book_id → newhigh symbol。
    600519.XSHG → 600519.SH，000001.XSHE → 000001.SZ，830799.BSE → 830799.BSE。
    """
    ob = (order_book_id or "").strip()
    if "." not in ob:
        return ob
    code, market = ob.split(".", 1)
    mu = market.upper()
    if mu == "XSHG":
        return f"{code}.SH"
    if mu == "XSHE":
        return f"{code}.SZ"
    if mu == "BSE":
        return f"{code}.BSE"
    return f"{code}.{market}"


def symbol_to_order_book_id(symbol: str) -> str:
    """
    newhigh symbol 或 6～8 位纯代码 → astock order_book_id。
    """
    s = strip_ashare_code(symbol)
    if not s or len(s) < 5 or len(s) > 8:
        return symbol or ""
    ns = normalize_ashare_symbol(s)
    if ns.endswith(".SH"):
        return f"{s}.XSHG"
    if ns.endswith(".SZ"):
        return f"{s}.XSHE"
    if ns.endswith(".BSE"):
        return f"{s}.BSE"
    return f"{s}.XSHE"
