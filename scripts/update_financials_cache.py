#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新市场扫描器使用的财务缓存：去年营收、净利润、每股收益、每股净资产、行业、区域。
- 业绩报表 stock_yjbb_em：营收、净利润、eps、bps、行业
- 公司概况 stock_profile_cninfo：区域（注册地省份）
"""
from __future__ import annotations
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)


def _get_symbols_set(limit: int | None) -> set[str]:
    """获取待更新标的集合（6 位代码），用于过滤；None 表示不过滤。"""
    try:
        from database.duckdb_backend import get_db_backend
        db = get_db_backend()
        if db and hasattr(db, "get_stocks"):
            rows = db.get_stocks()
            symbols = [r[1] if len(r) > 1 else str(r[0]).split(".")[0] for r in rows]
            symbols = [str(s).zfill(6) for s in symbols if s and str(s).isdigit()]
            if limit:
                symbols = symbols[:limit]
            return set(symbols)
    except Exception:
        pass
    return set()


def _extract_region(addr: str | None) -> str | None:
    """从注册地址提取省份/区域，如 广东省深圳市xxx -> 广东，北京市xxx -> 北京"""
    if not addr or not str(addr).strip():
        return None
    s = str(addr).strip()
    m = re.match(r"^([^省]+)省", s)
    if m:
        return m.group(1).strip()
    m = re.match(r"^([^市]+)市", s)
    if m:
        return m.group(1).strip()
    m = re.match(r"^(北京|上海|天津|重庆)", s)
    if m:
        return m.group(1)
    return s[:6] if len(s) > 6 else s


def _fetch_yjbb_batch(report_date: str):
    """东方财富业绩报表：一次拉取全市场。"""
    try:
        import akshare as ak
        df = ak.stock_yjbb_em(date=report_date)
        if df is None or df.empty:
            return None
        return df
    except Exception as e:
        print(f"stock_yjbb_em 失败: {e}", file=sys.stderr)
        return None


def _fetch_region_for_symbol(symbol: str) -> str | None:
    """单只股票公司概况，提取注册地省份（巨潮 stock_profile_cninfo）。"""
    time.sleep(0.15)
    try:
        import akshare as ak
        df = ak.stock_profile_cninfo(symbol=symbol)
        if df is not None and not df.empty and "注册地址" in df.columns:
            addr = df["注册地址"].iloc[0]
            if addr and str(addr).strip():
                return _extract_region(str(addr))
    except Exception:
        pass
    return None


def _fetch_region_from_banks(cache: dict) -> int:
    """从东方财富地域板块成分股补充区域。北京板块、广东板块等 -> symbol->region。"""
    try:
        import akshare as ak
        rank = ak.stock_hsgt_board_rank_em(symbol="北向资金增持地域板块排行", indicator="今日")
        if rank is None or rank.empty:
            return 0
        name_col = "名称" if "名称" in rank.columns else rank.columns[1]
        regions = rank[name_col].tolist()
        added = 0
        for r in regions:
            if not r or not isinstance(r, str) or "板块" not in r:
                continue
            region_short = r.replace("板块", "").strip()
            if len(region_short) < 2:
                continue
            try:
                cons = ak.stock_board_concept_cons_em(symbol=r)
                if cons is None or cons.empty:
                    continue
                code_col = "代码" if "代码" in cons.columns else "股票代码"
                if code_col not in cons.columns:
                    continue
                for _, row in cons.iterrows():
                    code = row.get(code_col)
                    if code is None:
                        continue
                    sym = str(code).strip().zfill(6)
                    if sym.isdigit() and sym in cache and not cache[sym].get("region"):
                        cache[sym]["region"] = region_short
                        added += 1
            except Exception:
                continue
            time.sleep(0.3)
        return added
    except Exception as e:
        print(f"地域板块补充区域失败: {e}", file=sys.stderr)
        return 0


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description="更新 data/financials_cache.json（营收/净利润/eps/bps/行业/区域）")
    p.add_argument("--limit", type=int, default=None, help="仅保留前 N 只标的（默认全部）")
    p.add_argument("--out", default=None, help="输出路径，默认 data/financials_cache.json")
    p.add_argument("--date", default=None, help="报告期 YYYYMMDD，默认 20231231")
    p.add_argument("--region-limit", type=int, default=0, help="拉取区域信息的标的数量，0=不拉取")
    p.add_argument("--region-all", action="store_true", help="拉取全部标的的区域信息（约5000+只，需15~25分钟）")
    args = p.parse_args()

    out_path = args.out or os.path.join(_ROOT, "data", "financials_cache.json")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    report_date = args.date or "20231231"
    symbols_filter = _get_symbols_set(args.limit) if args.limit else None

    print(f"拉取业绩报表: report_date={report_date} …")
    df = _fetch_yjbb_batch(report_date)
    if df is None or df.empty:
        print("未获取到数据")
        return 1

    code_col = "股票代码"
    revenue_col = next((c for c in df.columns if "营业总收入" in c and "同比" not in c and "环比" not in c), "营业总收入-营业总收入")
    profit_col = next((c for c in df.columns if "净利润" in c and "同比" not in c and "环比" not in c), "净利润-净利润")
    eps_col = "每股收益" if "每股收益" in df.columns else None
    bps_col = "每股净资产" if "每股净资产" in df.columns else None
    industry_col = "所处行业" if "所处行业" in df.columns else None

    cache = {}
    for _, row in df.iterrows():
        code = row.get(code_col)
        if code is None or (hasattr(code, "strip") and not str(code).strip()):
            continue
        sym = str(code).strip().zfill(6)
        if not sym.isdigit():
            continue
        if symbols_filter is not None and sym not in symbols_filter:
            continue
        try:
            rev = row.get(revenue_col)
            profit = row.get(profit_col)
            revenue_ly = float(rev) if rev is not None and str(rev) not in ("nan", "") else None
            profit_ly = float(profit) if profit is not None and str(profit) not in ("nan", "") else None
            eps_val = row.get(eps_col) if eps_col else None
            bps_val = row.get(bps_col) if bps_col else None
            eps_ly = float(eps_val) if eps_val is not None and str(eps_val) not in ("nan", "") else None
            bps_ly = float(bps_val) if bps_val is not None and str(bps_val) not in ("nan", "") else None
            industry = str(row.get(industry_col)).strip() if industry_col and row.get(industry_col) not in (None, "") else None
            if industry == "nan":
                industry = None
            cache[sym] = {
                "revenue_ly": revenue_ly,
                "profit_ly": profit_ly,
                "eps_ly": eps_ly,
                "bps_ly": bps_ly,
                "industry": industry,
            }
        except (TypeError, ValueError):
            continue

    region_count = len(cache) if args.region_all else args.region_limit
    if region_count > 0:
        syms = list(cache.keys())[:region_count]
        workers = min(3, max(1, (len(syms) // 1000) + 1))
        eta_min = len(syms) * 0.18 / workers / 60
        print(f"拉取区域信息（共 {len(syms)} 只，{workers} 线程，约 {eta_min:.1f} 分钟）…", flush=True)
        done = 0
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(_fetch_region_for_symbol, sym): sym for sym in syms}
            for f in as_completed(futures):
                sym = futures[f]
                try:
                    r = f.result()
                    if r:
                        cache[sym]["region"] = r
                except Exception:
                    pass
                done += 1
                if done % 200 == 0:
                    print(f"  已处理 {done}/{len(syms)}", flush=True)

    n_bank = _fetch_region_from_banks(cache)
    if n_bank > 0:
        print(f"从地域板块补充区域: +{n_bank} 只")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=0)
    print(f"共写入 {len(cache)} 条到 {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
