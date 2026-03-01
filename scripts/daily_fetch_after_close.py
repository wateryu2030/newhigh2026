#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易日 15:30 后自动拉取新增日线数据（增量更新），并同步新增股票信息。

流程：1) 同步 A 股列表，拉取库中不存在的标的（新股等）；2) 对库中全部标的做日线增量更新。

用法：
  python scripts/daily_fetch_after_close.py

调度方式二选一：
  1) 随 Web 启动：运行 web_platform.py 时已内置工作日 15:30（上海时区）定时任务，需安装 APScheduler。
  2) 系统 crontab（不依赖 Web 常驻）：
     30 15 * * 1-5 cd /path/to/astock && .venv/bin/python scripts/daily_fetch_after_close.py
"""
import os
import sys
import time
import logging
from datetime import datetime, timedelta

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def is_trading_day(dt: datetime) -> bool:
    """简单判断是否为交易日：周一至周五（未排除节假日）。"""
    return dt.weekday() < 5


def _get_current_a_share_list():
    """获取当前沪深京 A 股代码与名称列表。返回 [(code, name), ...]，code 为 6 位。兼容多种 akshare 接口。"""
    import akshare as ak
    df = None
    code_col, name_col = None, None
    # 优先 stock_info_a_code_name；部分版本无此接口则用 stock_zh_a_spot_em
    if hasattr(ak, "stock_info_a_code_name"):
        try:
            df = ak.stock_info_a_code_name()
            if df is not None and not df.empty:
                code_col = "code" if "code" in df.columns else None
                name_col = "name" if "name" in df.columns else None
        except Exception:
            df = None
    if (df is None or df.empty or not code_col) and hasattr(ak, "stock_zh_a_spot_em"):
        try:
            df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                code_col = "代码" if "代码" in df.columns else ("code" if "code" in df.columns else None)
                name_col = "名称" if "名称" in df.columns else ("name" if "name" in df.columns else None)
        except Exception:
            df = None
    if df is None or df.empty or not code_col:
        logger.warning("获取 A 股列表失败：当前 akshare 无 stock_info_a_code_name / stock_zh_a_spot_em 或返回为空")
        return []
    out = []
    for _, row in df.iterrows():
        code = str(row.get(code_col, "")).strip().zfill(6)
        name = str(row.get(name_col, "")).strip() if name_col else code
        if code.isdigit() and len(code) == 6:
            out.append((code, name or code))
    return out


def sync_new_stocks(delay_seconds: float = 0.2) -> int:
    """
    同步新增股票：对比当前 A 股列表与数据库，对库中不存在的标的拉取基本信息与日线并入库。
    返回新入库的标的数量。
    """
    from database.duckdb_backend import get_db_backend

    db = get_db_backend()
    if not os.path.exists(getattr(db, "db_path", "")):
        logger.warning("数据库文件不存在，跳过同步新股")
        return 0

    current = _get_current_a_share_list()
    if not current:
        return 0
    current_codes = {c[0] for c in current}
    current_map = {c[0]: c[1] for c in current}

    existing = set()
    for order_book_id, symbol, _ in db.get_stocks():
        code = (symbol or order_book_id.split(".")[0]).strip()
        if code.isdigit() and len(code) == 6:
            existing.add(code)
    new_codes = sorted(current_codes - existing)
    if not new_codes:
        logger.info("无新增股票需同步")
        return 0

    # 单次运行最多同步数量，避免首次空库时一次拉全市场导致超时/限流
    max_new_per_run = 500
    if len(new_codes) > max_new_per_run:
        logger.info("新增股票 %d 只，本次仅处理前 %d 只，其余下次继续", len(new_codes), max_new_per_run)
        new_codes = new_codes[:max_new_per_run]
    else:
        logger.info("发现 %d 只新增股票，开始拉取并入库", len(new_codes))
    today = datetime.now().date()
    today_ymd = today.strftime("%Y%m%d")
    # 新股通常上市不久，拉取近 1 年即可覆盖；若上市更早则后续由增量任务补全
    start_ymd = (today - timedelta(days=365)).strftime("%Y%m%d")
    success = 0

    for code in new_codes:
        order_book_id = f"{code}.XSHG" if code.startswith("6") else f"{code}.XSHE"
        name = current_map.get(code, code)
        try:
            import akshare as ak
            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_ymd,
                end_date=today_ymd,
                adjust="qfq",
            )
        except Exception as e:
            logger.debug("%s 拉取失败: %s", code, e)
            if delay_seconds > 0:
                time.sleep(delay_seconds)
            continue
        if df is None or len(df) == 0:
            if delay_seconds > 0:
                time.sleep(delay_seconds)
            continue
        try:
            db.add_stock(
                order_book_id=order_book_id,
                symbol=code,
                name=name,
                market="CN",
                listed_date=None,
                de_listed_date=None,
                type="CS",
            )
            db.add_daily_bars(order_book_id, df)
            success += 1
            logger.info("新增 %s (%s) %s，写入 %d 条日线", code, order_book_id, name, len(df))
        except Exception as e:
            logger.warning("%s 写入失败: %s", code, e)
        if delay_seconds > 0:
            time.sleep(delay_seconds)

    return success


def run_incremental_fetch(delay_seconds: float = 0.15) -> int:
    """
    对数据库中已有标的，仅拉取「最新交易日之后」到「今天」的新数据并写入库。
    返回成功更新的标的数量。
    """
    from database.duckdb_backend import get_db_backend

    db = get_db_backend()
    if not os.path.exists(getattr(db, "db_path", "")):
        logger.warning("数据库文件不存在，跳过增量拉取")
        return 0

    stocks = db.get_stocks()
    if not stocks:
        logger.info("数据库无股票列表，跳过增量拉取（可先运行全量导入）")
        return 0

    today = datetime.now().date()
    today_str = today.strftime("%Y-%m-%d")
    today_ymd = today_str.replace("-", "")
    success = 0

    for order_book_id, symbol, _ in stocks:
        symbol = (symbol or order_book_id.split(".")[0]).strip()
        if not symbol or len(symbol) != 6:
            continue
        last = db.get_last_trade_date(order_book_id)
        if last:
            try:
                last_dt = datetime.strptime(last[:10], "%Y-%m-%d").date()
            except Exception:
                last_dt = None
            if last_dt and last_dt >= today:
                continue
            start_dt = (last_dt + timedelta(days=1)) if last_dt else today - timedelta(days=7)
        else:
            start_dt = today - timedelta(days=7)
        start_str = start_dt.strftime("%Y-%m-%d")
        start_ymd = start_str.replace("-", "")
        if start_ymd > today_ymd:
            continue

        try:
            import akshare as ak
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_ymd,
                end_date=today_ymd,
                adjust="qfq",
            )
        except Exception as e:
            logger.debug("%s 拉取失败: %s", symbol, e)
            continue
        if df is None or len(df) == 0:
            continue
        try:
            db.add_daily_bars(order_book_id, df)
            success += 1
            logger.info("%s (%s) 更新 %d 条", symbol, order_book_id, len(df))
        except Exception as e:
            logger.warning("%s 写入失败: %s", symbol, e)
        if delay_seconds > 0:
            time.sleep(delay_seconds)

    return success


def main() -> int:
    now = datetime.now()
    if not is_trading_day(now):
        logger.info("今日非交易日，跳过拉取")
        return 0
    logger.info("开始每日数据同步（交易日 %s）", now.strftime("%Y-%m-%d"))
    # 1) 同步新增股票（新股等）
    new_count = sync_new_stocks(delay_seconds=0.2)
    if new_count > 0:
        logger.info("新增股票同步完成，共 %d 只", new_count)
    # 2) 对库中全部标的做日线增量更新
    n = run_incremental_fetch(delay_seconds=0.12)
    logger.info("每日同步完成：新增 %d 只标的，增量更新 %d 只标的", new_count, n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
