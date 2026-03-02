#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据获取器 - 从 AKShare 获取数据并存储到数据库
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pandas as pd
from datetime import datetime, timedelta
import time
from typing import List
from database.duckdb_backend import get_db_backend


def get_all_a_share_symbols() -> List[str]:
    """获取沪深京 A 股全部股票代码（6 位字符串）。"""
    return [c for c, _ in get_all_a_share_code_name()]


def get_all_a_share_code_name() -> List[tuple]:
    """获取沪深京 A 股全部 (code, name)。含沪深（akshare）+ 北交所（官网直连），统一用于 stocks 表与日线拉取，保证数据一致。"""
    out: List[tuple] = []
    try:
        import akshare as ak
        df = None
        code_col = None
        name_col = None
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
                pass
        if df is not None and not df.empty and code_col:
            for _, row in df.iterrows():
                code = str(row[code_col]).strip().zfill(6)
                if not code.isdigit() or len(code) != 6:
                    continue
                name = (str(row[name_col]).strip() if name_col else "") or code
                out.append((code, name))
    except Exception as e:
        print(f"⚠️  获取沪深代码+名称失败: {e}")
    # 北交所：与 A 股拉取逻辑合并，统一数据源
    seen = {c for c, _ in out}
    for code, name in get_bj_stock_code_name():
        if code not in seen:
            seen.add(code)
            out.append((code, name))
    return out


def _fetch_bj_stock_code_name_bse_cn() -> List[tuple]:
    """从北交所官网 API 拉取股票代码+简称，不依赖 akshare 版本。"""
    def _parse_page(text: str) -> tuple:
        """解析一页 JSON，返回 (content_list, total_pages)。"""
        i = text.find("[")
        if i < 0:
            return [], 0
        try:
            data_json = json.loads(text[i : text.rfind("]") + 1])
        except json.JSONDecodeError:
            return [], 0
        if not data_json or not isinstance(data_json, list):
            return [], 0
        total_pages = data_json[0].get("totalPages", 1)
        content = data_json[0].get("content") or []
        return content, total_pages

    def _row_to_code_name(row) -> tuple:
        code, name = "", ""
        if isinstance(row, dict):
            code = (row.get("xxzqdm") or row.get("证券代码") or row.get("code") or "").strip()
            name = (row.get("xxzqjc") or row.get("证券简称") or row.get("name") or code).strip()
        elif isinstance(row, (list, tuple)) and len(row) > 28:
            code = str(row[26]).strip() if len(row) > 26 else ""
            name = str(row[28]).strip() if len(row) > 28 else code
        if "." in code:
            code = code.split(".")[0]
        code = code.zfill(6)
        if not code.isdigit() or len(code) != 6:
            return None, None
        return code, (name or code)

    url = "https://www.bse.cn/nqxxController/nqxxCnzq.do"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    out = []
    try:
        import requests
        data = {"page": "0", "typejb": "T", "xxfcbj[]": "2", "xxzqdm": "", "sortfield": "xxzqdm", "sorttype": "asc"}
        r = requests.post(url, data=data, headers=headers, timeout=20, allow_redirects=True)
        r.raise_for_status()
        content, total_pages = _parse_page(r.text)
        for row in content:
            code, name = _row_to_code_name(row)
            if code:
                out.append((code, name))
        for page in range(1, total_pages):
            data["page"] = str(page)
            r = requests.post(url, data=data, headers=headers, timeout=20, allow_redirects=True)
            r.raise_for_status()
            content, _ = _parse_page(r.text)
            for row in content:
                code, name = _row_to_code_name(row)
                if code:
                    out.append((code, name))
        if out:
            return out
    except Exception as e:
        print(f"⚠️  北交所官网拉取(requests)失败: {e}")

    try:
        import urllib.request
        import urllib.parse
        data = {"page": "0", "typejb": "T", "xxfcbj[]": "2", "xxzqdm": "", "sortfield": "xxzqdm", "sorttype": "asc"}
        body = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
        with opener.open(req, timeout=20) as resp:
            text = resp.read().decode("utf-8")
        content, total_pages = _parse_page(text)
        for row in content:
            code, name = _row_to_code_name(row)
            if code:
                out.append((code, name))
        for page in range(1, total_pages):
            data["page"] = str(page)
            body = urllib.parse.urlencode(data).encode("utf-8")
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with opener.open(req, timeout=20) as resp:
                text = resp.read().decode("utf-8")
            content, _ = _parse_page(text)
            for row in content:
                code, name = _row_to_code_name(row)
                if code:
                    out.append((code, name))
        return out
    except Exception as e:
        print(f"⚠️  北交所官网拉取(urllib)失败: {e}")
    return out


def get_bj_stock_code_name() -> List[tuple]:
    """获取北交所股票 (code, name)。优先北交所官网直连，失败再用 akshare。"""
    # 优先北交所官网（不依赖 akshare 版本）
    out = _fetch_bj_stock_code_name_bse_cn()
    if out:
        return out
    try:
        import akshare as ak
        if hasattr(ak, "stock_info_bj_name_code"):
            df = ak.stock_info_bj_name_code()
            if df is not None and not df.empty:
                code_col = "证券代码" if "证券代码" in df.columns else ("code" if "code" in df.columns else None)
                name_col = "证券简称" if "证券简称" in df.columns else ("name" if "name" in df.columns else None)
                if code_col:
                    for _, row in df.iterrows():
                        code = str(row[code_col]).strip()
                        if "." in code:
                            code = code.split(".")[0]
                        code = code.zfill(6)
                        if not code.isdigit() or len(code) != 6:
                            continue
                        name = (str(row[name_col]).strip() if name_col else "") or code
                        out.append((code, name))
                    return out
    except Exception as e:
        print(f"⚠️  akshare 北交所接口失败: {e}")
    return out


def _order_book_id_for_code(code: str) -> str:
    """根据 6 位代码返回 order_book_id：沪 6 -> XSHG，北交所 4/8/9 -> BSE，深 0/3 -> XSHE。"""
    code = str(code).strip()
    if code.startswith("6"):
        return f"{code}.XSHG"
    if code.startswith("4") or code.startswith("8") or code.startswith("9"):
        return f"{code}.BSE"
    return f"{code}.XSHE"


def get_pool_symbols(data_dir: str = "data") -> List[str]:
    """从策略用到的所有 CSV 股票池中收集唯一股票代码（纯数字，如 600745）。"""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(root, data_dir) if not os.path.isabs(data_dir) else data_dir
    symbols = set()
    files_columns = [
        ("industry_stock_map.csv", "代码"),
        ("tech_leader_stocks.csv", "代码"),
        ("consume_leader_stocks.csv", "代码"),
        ("etf_list.csv", "代码"),
    ]
    for filename, col in files_columns:
        path = os.path.join(data_dir, filename)
        if not os.path.exists(path):
            continue
        try:
            df = pd.read_csv(path, encoding="utf-8-sig")
            if col not in df.columns:
                continue
            for v in df[col].dropna().astype(str):
                v = v.strip()
                if not v or v in ("nan", "None"):
                    continue
                # 去掉 .XSHG / .XSHE 得到纯代码
                if "." in v:
                    v = v.split(".")[0]
                if v.isdigit() and len(v) == 6:
                    symbols.add(v)
        except Exception:
            continue
    return sorted(symbols)


class DataFetcher:
    """数据获取器"""
    
    def __init__(self, db_path=None):
        """db_path 忽略，统一使用 DuckDB。"""
        self.db = get_db_backend()
    
    def fetch_stock_data(self, symbol: str, start_date: str = None, end_date: str = None,
                        adjust: str = "qfq", name: str = None):
        """
        获取单只股票数据并存储。

        Args:
            symbol: 股票代码（如 "600745"）
            start_date: 开始日期 "YYYYMMDD"
            end_date: 结束日期 "YYYYMMDD"
            adjust: 复权类型 "qfq"前复权/"hfq"后复权/""不复权
            name: 股票中文名称，若提供则写入 stocks 表，保证列表页显示完整
        """
        if not start_date:
            start_date = "20200101"
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")

        print(f"获取 {symbol} 数据: {start_date} 至 {end_date}")

        try:
            import akshare as ak
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )

            if df is None or len(df) == 0:
                print(f"⚠️  {symbol} 未获取到数据")
                return False

            order_book_id = _order_book_id_for_code(symbol)
            market = "CN"

            # 保存股票基本信息（含名称，保证交易页列表显示完整）
            self.db.add_stock(
                order_book_id=order_book_id,
                symbol=symbol,
                name=name,
                market=market,
                listed_date=None,
                de_listed_date=None,
                type="CS"
            )

            # 保存日线数据（按复权类型写入）
            self.db.add_daily_bars(order_book_id, df, adjust_type=adjust)

            print(f"✅ {symbol} ({order_book_id}) {adjust or '不复权'} 数据获取成功: {len(df)} 条")
            return True

        except Exception as e:
            print(f"❌ 获取 {symbol} 数据失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def fetch_multiple_stocks(self, symbols: List[str], start_date: str = None,
                             end_date: str = None, delay: float = 0.1,
                             code_name_map: dict = None):
        """批量获取多只股票数据。code_name_map: 可选，code -> 中文名称，用于写入 stocks 表。"""
        print(f"\n开始批量获取 {len(symbols)} 只股票数据...")
        success_count = 0
        name_map = code_name_map or {}

        for i, symbol in enumerate(symbols, 1):
            name = name_map.get(symbol, "")
            print(f"\n[{i}/{len(symbols)}] 处理 {symbol}（前复权+后复权）...")
            ok_qfq = self.fetch_stock_data(symbol, start_date, end_date, adjust="qfq", name=name)
            if i < len(symbols):
                time.sleep(delay * 0.5)
            ok_hfq = self.fetch_stock_data(symbol, start_date, end_date, adjust="hfq", name=None)
            if ok_qfq or ok_hfq:
                success_count += 1
            # 避免请求过快
            if i < len(symbols):
                time.sleep(delay)

        print(f"\n✅ 批量获取完成: {success_count}/{len(symbols)} 成功（每只含 qfq+hfq）")
        return success_count
    
    def fetch_wentai_data(self):
        """获取闻泰科技数据（示例）"""
        return self.fetch_stock_data("600745", "20200101", datetime.now().strftime("%Y%m%d"))

    def fetch_pool_stocks(self, start_date: str = None, end_date: str = None, data_dir: str = "data",
                          delay: float = 0.15) -> int:
        """
        全量同步股票池：从 data 目录下所有策略用到的 CSV 中收集股票代码，并拉取这些股票的日线数据写入数据库。
        用于多标的策略（如策略2/策略1）回测前补全数据，减少「No market data」。
        """
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365 * 2)).strftime("%Y%m%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        symbols = get_pool_symbols(data_dir)
        if not symbols:
            print("未找到任何股票池文件或代码，请先确保 data/ 下存在 industry_stock_map.csv 或 tech_leader_stocks.csv 等")
            return 0
        print(f"股票池共 {len(symbols)} 只，将拉取 {start_date} 至 {end_date} 的日线数据")
        return self.fetch_multiple_stocks(symbols, start_date, end_date, delay=delay)

    def fetch_all_a_stocks(
        self,
        start_date: str = None,
        end_date: str = None,
        delay: float = 0.12,
        skip_existing: bool = True,
    ) -> int:
        """
        全量导入 A 股日线：获取沪深京全部股票列表（含名称），逐只拉取日线并写入数据库。
        skip_existing=True 时，若某只股票在区间内已有数据则跳过，便于断点续传。
        同时写入 stocks 表名称，保证交易页列表显示完整。
        """
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365 * 2)).strftime("%Y%m%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        code_name_list = get_all_a_share_code_name()
        if not code_name_list:
            return 0
        symbols = [c for c, _ in code_name_list]
        code_name_map = {c: n for c, n in code_name_list}
        to_fetch = symbols
        if skip_existing:
            start_d = start_date[:4] + "-" + start_date[4:6] + "-" + start_date[6:8]
            end_d = end_date[:4] + "-" + end_date[4:6] + "-" + end_date[6:8]
            to_fetch = []
            for sym in symbols:
                ob = _order_book_id_for_code(sym)
                bars = self.db.get_daily_bars(ob, start_d, end_d)
                if bars is None or (hasattr(bars, "__len__") and len(bars) < 10):
                    to_fetch.append(sym)
            print(f"共 {len(symbols)} 只 A 股，其中 {len(to_fetch)} 只需拉取（已跳过有数据的）")
        else:
            print(f"共 {len(symbols)} 只 A 股，将拉取 {start_date} 至 {end_date} 的日线数据")
        if not to_fetch:
            print("无需拉取新数据")
            return 0
        return self.fetch_multiple_stocks(
            to_fetch, start_date, end_date, delay=delay, code_name_map=code_name_map
        )

    def backfill_adjust_qfq(
        self,
        symbols: List[str] = None,
        start_date: str = None,
        end_date: str = None,
        delay: float = 0.12,
        code_name_map: dict = None,
    ) -> int:
        """
        全量复权补全：对指定标的（或全市场）在给定日期区间内用 前复权(qfq)+后复权(hfq) 拉取并写入库，
        覆盖已有日线，与全量/增量更新逻辑一致。symbols 为空时使用 get_all_a_share_code_name()。
        返回成功补全的标的数量（任一复权成功即计 1）。
        """
        return self.backfill_adjust(symbols, start_date, end_date, delay, code_name_map)

    def backfill_adjust(
        self,
        symbols: List[str] = None,
        start_date: str = None,
        end_date: str = None,
        delay: float = 0.12,
        code_name_map: dict = None,
    ) -> int:
        """全量复权补全：前复权(qfq)+后复权(hfq) 同时拉取并写入，在数据更新时补齐双轨。"""
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365 * 3)).strftime("%Y%m%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        if symbols is None:
            code_name_list = get_all_a_share_code_name()
            if not code_name_list:
                print("⚠️  未获取到股票列表，跳过复权补全")
                return 0
            symbols = [c for c, _ in code_name_list]
            code_name_map = code_name_map or {c: n for c, n in code_name_list}
        else:
            code_name_map = code_name_map or {}
        print(f"复权补全: 共 {len(symbols)} 只，区间 {start_date}–{end_date}，前复权+后复权")
        success = 0
        for i, symbol in enumerate(symbols, 1):
            name = code_name_map.get(symbol, "")
            ok_qfq = self.fetch_stock_data(symbol, start_date, end_date, adjust="qfq", name=name)
            if i < len(symbols):
                time.sleep(delay * 0.5)
            ok_hfq = self.fetch_stock_data(symbol, start_date, end_date, adjust="hfq", name=None)
            if ok_qfq or ok_hfq:
                success += 1
            if i < len(symbols):
                time.sleep(delay)
        print(f"✅ 复权补全完成: {success}/{len(symbols)} 只（qfq+hfq）")
        return success

    def update_trading_calendar(self, start_date: str = "20200101", end_date: str = None):
        """更新交易日历（简化版：使用工作日作为代理）"""
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")

        start = datetime.strptime(start_date, "%Y%m%d")
        end = datetime.strptime(end_date, "%Y%m%d")

        dates = []
        current = start
        while current <= end:
            # 简单判断：周一到周五为交易日（实际应使用真实交易日历）
            if current.weekday() < 5:  # 0-4 为周一到周五
                dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)

        self.db.add_trading_dates(dates)
        print(f"✅ 交易日历已更新: {len(dates)} 个交易日")


def sync_stock_names_to_db() -> int:
    """
    将沪深京 A 股代码+名称全量写入 DuckDB stocks 表。
    使用与日线拉取一致的 get_all_a_share_code_name()（沪深+北交所），保证数据一致。
    返回写入（更新）的股票数量。
    """
    code_name_list = list(get_all_a_share_code_name())
    if not code_name_list:
        print("⚠️  未获取到任何股票列表")
        return 0
    n_bj = sum(1 for c, _ in code_name_list if c and c[:1] in ("4", "8", "9"))
    n_sh_sz = len(code_name_list) - n_bj
    print(f"沪深: {n_sh_sz} 只, 北交所: {n_bj} 只, 合计: {len(code_name_list)} 只 → 写入 DB")
    db = get_db_backend()
    count = 0
    for code, name in code_name_list:
        order_book_id = _order_book_id_for_code(code)
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
            count += 1
        except Exception:
            continue
    return count


if __name__ == "__main__":
    fetcher = DataFetcher()
    
    # 获取闻泰科技数据
    print("=" * 60)
    print("获取闻泰科技（600745）数据")
    print("=" * 60)
    fetcher.fetch_wentai_data()
    
    # 更新交易日历
    print("\n" + "=" * 60)
    print("更新交易日历")
    print("=" * 60)
    fetcher.update_trading_calendar()
