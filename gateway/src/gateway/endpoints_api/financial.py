"""
财报分析 API 端点

提供财报查询、股东信息、变化分析等接口。

API 列表:
- GET /api/financial/anti-quant-pool - 反量化长线选股池
- GET /api/financial/anti-quant-stock/{stock_code} - 单只股票反量化因子
- GET /api/financial/report/{stock_code} - 获取财报数据
- GET /api/financial/metrics/{stock_code} - 获取关键指标
- GET /api/financial/changes/{stock_code} - 获取指标变化
- GET /api/financial/top-changes/{stock_code} - 获取十大变化
- GET /api/financial/shareholders/{stock_code} - 获取 10 大股东信息
- GET /api/financial/shareholder-changes/{stock_code} - 获取股东变化
- GET /api/financial/shareholder-tracking/{stock_code} - 获取股东追踪 (5 年)
- GET /api/financial/market-top-changes - 获取全市场变化排名
- POST /api/financial/collect - 触发财报采集任务
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from fastapi import APIRouter, Query, HTTPException

import pandas as pd

# 定位项目根目录（gateway 在 project/gateway/src/gateway/ 下）
_THIS_DIR = Path(__file__).resolve().parent
_GATEWAY_SRC = _THIS_DIR.parent  # gateway/src/gateway
_GATEWAY_ROOT = _GATEWAY_SRC.parent  # gateway/src
_PROJECT_ROOT = _GATEWAY_ROOT.parent.parent  # project root (parent of gateway/)

# 导入采集器和分析器
import sys
sys.path.insert(0, str(_PROJECT_ROOT / "data" / "src"))
sys.path.insert(0, str(_PROJECT_ROOT / "core" / "src"))

from data.collectors.financial_report import FinancialReportCollector
from core.analysis.financial_analyzer import FinancialAnalyzer


router = APIRouter(prefix="/financial", tags=["财报分析"])


@router.get("/report/{stock_code}")
def get_financial_report(
    stock_code: str,
    report_type: Optional[str] = Query(None, description="年报/季报/半年报"),
    limit: int = Query(10, description="返回数量"),
):
    """
    获取财报数据
    
    Args:
        stock_code: 股票代码
        report_type: 报告类型 (可选)
        limit: 返回数量
    """
    try:
        from lib.database import get_connection
        conn = get_connection(read_only=False)
        if conn is None:
            return {"ok": False, "error": "数据库连接失败，请检查 quant_system.duckdb 是否存在"}
        
        query = """
            SELECT * FROM financial_report
            WHERE stock_code = ?
        """
        params = [stock_code]
        
        if report_type:
            query += " AND report_type = ?"
            params.append(report_type)
        
        query += " ORDER BY report_date DESC LIMIT ?"
        params.append(limit)
        
        df = conn.execute(query, params).fetchdf()
        conn.close()
        
        if df.empty:
            return {"ok": False, "error": "未找到财报数据", "stock_code": stock_code}
        
        return {
            "ok": True,
            "stock_code": stock_code,
            "count": len(df),
            "data": df.to_dict("records"),
        }
        
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/metrics/{stock_code}")
def get_key_metrics(stock_code: str):
    """
    获取关键指标
    
    Args:
        stock_code: 股票代码
    """
    try:
        collector = FinancialReportCollector()
        metrics = collector.get_key_metrics(stock_code)
        
        if not metrics:
            return {"ok": False, "error": "获取指标失败", "stock_code": stock_code}
        
        return {
            "ok": True,
            "stock_code": stock_code,
            "data": metrics,
        }
        
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/changes/{stock_code}")
def get_metric_changes(
    stock_code: str,
    metric_name: Optional[str] = Query(None, description="指标名称"),
    periods: int = Query(4, description="分析期数"),
):
    """
    获取指标变化
    
    Args:
        stock_code: 股票代码
        metric_name: 指标名称 (可选)
        periods: 分析期数
    """
    try:
        analyzer = FinancialAnalyzer()
        
        metric_names = None
        if metric_name:
            metric_names = [metric_name]
        
        changes = analyzer.calculate_changes(stock_code, metric_names, periods)
        
        return {
            "ok": True,
            "stock_code": stock_code,
            "count": len(changes),
            "data": changes,
        }
        
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/top-changes/{stock_code}")
def get_top_changes(
    stock_code: str,
    report_date: Optional[str] = Query(None, description="报告日期"),
    top_n: int = Query(10, description="返回数量"),
):
    """
    获取十大变化
    
    Args:
        stock_code: 股票代码
        report_date: 报告日期 (可选)
        top_n: 返回数量
    """
    try:
        analyzer = FinancialAnalyzer()
        changes = analyzer.get_top_changes(stock_code, report_date, top_n)
        
        return {
            "ok": True,
            "stock_code": stock_code,
            "count": len(changes),
            "data": changes,
        }
        
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/shareholders/{stock_code}")
def get_top_10_shareholders(
    stock_code: str,
    report_date: Optional[str] = Query(None, description="报告日期"),
):
    """
    获取 10 大股东信息
    
    Args:
        stock_code: 股票代码
        report_date: 报告日期 (可选，默认最新)
    """
    try:
        from lib.database import get_connection
        conn = get_connection(read_only=False)
        if conn is None:
            return {"ok": False, "error": "数据库连接失败", "stock_code": stock_code}
        
        # 获取最新报告日期
        if report_date is None:
            result = conn.execute("""
                SELECT MAX(report_date) FROM top_10_shareholders
                WHERE stock_code = ?
            """, [stock_code]).fetchone()
            report_date = result[0] if result else None
        
        if report_date is None:
            conn.close()
            return {"ok": False, "error": "无股东数据", "stock_code": stock_code}
        
        df = conn.execute("""
            SELECT * FROM top_10_shareholders
            WHERE stock_code = ? AND report_date = ?
            ORDER BY rank
        """, [stock_code, report_date]).fetchdf()
        
        conn.close()
        
        if df.empty:
            return {"ok": False, "error": "无股东数据", "stock_code": stock_code}
        
        return {
            "ok": True,
            "stock_code": stock_code,
            "report_date": report_date,
            "count": len(df),
            "data": df.to_dict("records"),
        }
        
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/shareholder-changes/{stock_code}")
def get_shareholder_changes(
    stock_code: str,
    current_date: Optional[str] = Query(None, description="当前报告期"),
    previous_date: Optional[str] = Query(None, description="上期报告期"),
):
    """
    获取股东变化分析
    
    Args:
        stock_code: 股票代码
        current_date: 当前报告期 (可选)
        previous_date: 上期报告期 (可选)
    """
    try:
        analyzer = FinancialAnalyzer()
        analysis = analyzer.analyze_shareholder_changes(
            stock_code, current_date, previous_date
        )
        
        return {
            "ok": True,
            "stock_code": stock_code,
            "data": analysis,
        }
        
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/collected-stocks-rank3")
def get_collected_stocks_rank3(
    limit: int = Query(200, description="返回数量"),
    report_date: Optional[str] = Query(None, description="报告日期，默认最新"),
):
    """
    已采集完成股票列表及第3大股东情况（兼容旧接口）
    """
    return _get_collected_stocks_shareholders(report_date=report_date, rank_filter=3, limit=limit)


@router.get("/collected-stocks-all-ranks")
def get_collected_stocks_all_ranks(
    limit: int = Query(500, description="返回股票数量，每只最多10条股东记录"),
    report_date: Optional[str] = Query(None, description="报告日期，默认最新"),
):
    """
    已采集完成股票列表及全部十大股东
    
    返回：股票代码、名称、最新报告期、排名(1-10)、股东名称、类型、持股数、持股比例
    """
    return _get_collected_stocks_shareholders(report_date=report_date, rank_filter=None, limit=limit * 10)


def _get_collected_stocks_shareholders(
    report_date: Optional[str] = None,
    rank_filter: Optional[int] = None,
    limit: int = 2000,
) -> dict:
    """内部：按报告期和可选 rank 过滤返回股东数据"""
    try:
        from lib.database import get_connection
        conn = get_connection(read_only=False)
        if conn is None:
            return {"ok": False, "error": "数据库连接失败", "count": 0, "report_date": None, "data": []}

        if report_date is None:
            row = conn.execute("""
                SELECT MAX(report_date) AS d FROM top_10_shareholders
            """).fetchone()
            report_date = str(row[0])[:10] if row and row[0] else None

        if not report_date:
            conn.close()
            return {"ok": True, "count": 0, "report_date": None, "data": []}

        rank_clause = "AND t.rank = ?" if rank_filter is not None else ""
        params: list = [report_date]
        if rank_filter is not None:
            params.append(rank_filter)
        params.append(limit)

        df = conn.execute(f"""
            SELECT t.stock_code, COALESCE(b.name, t.stock_code) AS stock_name,
                   t.report_date, t.rank, t.shareholder_name, t.shareholder_type,
                   t.share_count, t.share_ratio
            FROM top_10_shareholders t
            LEFT JOIN a_stock_basic b ON t.stock_code = b.code
            WHERE t.report_date = ? {rank_clause}
            ORDER BY t.stock_code, t.rank
            LIMIT ?
        """, params).fetchdf()

        conn.close()

        if df.empty:
            return {"ok": True, "count": 0, "report_date": report_date, "data": []}

        data = [
            {
                "stock_code": str(row["stock_code"]),
                "stock_name": str(row["stock_name"] or row["stock_code"]),
                "report_date": str(row["report_date"])[:10],
                "rank": int(row["rank"] or 0),
                "shareholder_name": str(row["shareholder_name"] or ""),
                "shareholder_type": str(row["shareholder_type"] or ""),
                "share_count": int(row["share_count"] or 0),
                "share_ratio": round(float(row["share_ratio"] or 0), 2),
            }
            for _, row in df.iterrows()
        ]
        return {"ok": True, "count": len(data), "report_date": report_date, "data": data}

    except Exception as e:
        return {"ok": False, "error": str(e), "data": []}


@router.get("/shareholder-by-name")
def get_shareholder_by_name(
    name: str = Query(..., description="股东名称关键词（模糊匹配）"),
    limit: int = Query(20, description="返回数量"),
):
    """
    按股东名称模糊搜索，返回匹配的股东列表（供大佬策略页搜索下拉）
    
    Args:
        name: 股东名称关键词
        limit: 返回数量
    """
    try:
        from lib.database import get_connection
        conn = get_connection(read_only=False)
        if conn is None:
            return {"ok": False, "error": "数据库连接失败", "count": 0, "data": []}
        
        keyword = f"%{name.strip()}%"
        df = conn.execute("""
            SELECT shareholder_name, shareholder_type,
                   COUNT(DISTINCT stock_code) AS stock_count
            FROM top_10_shareholders
            WHERE shareholder_name LIKE ?
            GROUP BY shareholder_name, shareholder_type
            ORDER BY stock_count DESC
            LIMIT ?
        """, [keyword, limit]).fetchdf()
        
        conn.close()
        
        if df.empty:
            return {"ok": True, "count": 0, "data": []}
        
        data = [
            {
                "name": str(row["shareholder_name"] or ""),
                "shareholder_type": str(row["shareholder_type"] or ""),
                "stock_count": int(row["stock_count"] or 0),
            }
            for _, row in df.iterrows()
        ]
        return {"ok": True, "count": len(data), "data": data}
        
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/shareholder-strategy")
def get_shareholder_strategy(
    name: str = Query(..., description="股东名称（精确）"),
):
    """
    获取股东策略画像：持仓列表、变动流水、行业偏好等（供大佬策略页主内容）
    
    Args:
        name: 股东名称（需与 shareholder-by-name 返回的 name 一致）
    """
    try:
        from lib.database import get_connection

        conn = get_connection(read_only=False)
        if conn is None:
            return {"ok": False, "error": "数据库连接失败", "holdings": [], "changes": []}
        
        # 1. 获取该股东所有记录，按报告期排序
        df = conn.execute("""
            SELECT t.stock_code, t.report_date, t.rank, t.shareholder_name,
                   t.shareholder_type, t.share_count, t.share_ratio,
                   COALESCE(b.name, t.stock_code) AS stock_name,
                   b.sector AS industry
            FROM top_10_shareholders t
            LEFT JOIN a_stock_basic b ON t.stock_code = b.code
            WHERE t.shareholder_name = ?
            ORDER BY t.report_date ASC, t.rank
        """, [name.strip()]).fetchdf()
        
        if df.empty:
            conn.close()
            return {"ok": False, "error": "未找到该股东数据", "holdings": [], "changes": []}
        
        # 2. 获取最新收盘价用于估算持仓市值（可选）
        latest_dates = df["report_date"].drop_duplicates().sort_values(ascending=False).head(1)
        latest_date = str(latest_dates.iloc[0]) if len(latest_dates) > 0 else None
        
        # 3. 构建 holdings：按股票聚合，取最新报告期
        holdings_raw = df.sort_values("report_date", ascending=False).drop_duplicates(
            subset=["stock_code"], keep="first"
        )
        
        # 获取每只股票首次出现的报告期
        first_entry = df.groupby("stock_code")["report_date"].min().to_dict()
        
        # 获取每只股票最后出现的报告期（用于判断是否已退出）
        last_seen = df.groupby("stock_code")["report_date"].max().to_dict()
        all_dates = sorted(df["report_date"].unique())
        max_date = all_dates[-1] if all_dates else None
        
        def _date_to_quarter(d):
            if d is None:
                return "—"
            if hasattr(d, "year") and hasattr(d, "month"):
                y, m = d.year, d.month
            else:
                s = str(d)
                y = int(s[:4]) if len(s) >= 4 else 0
                m = int(s[5:7]) if len(s) >= 7 else 1
            if m <= 3:
                return f"{y}Q1"
            if m <= 6:
                return f"{y}Q2"
            if m <= 9:
                return f"{y}Q3"
            return f"{y}Q4"
        
        holdings = []
        for _, row in holdings_raw.iterrows():
            sc = str(row["stock_code"])
            rd = row["report_date"]
            exit_q = None
            status = "current"
            if max_date and str(last_seen.get(sc)) != str(max_date):
                status = "exited"
                exit_q = _date_to_quarter(last_seen.get(sc))
            
            share_count = int(row.get("share_count") or 0)
            ratio = float(row.get("share_ratio") or 0)
            # 万股
            hold_shares = share_count / 10000.0
            
            holdings.append({
                "stockCode": sc,
                "stockName": str(row.get("stock_name") or sc),
                "industry": str(row.get("industry") or "—"),
                "marketCap": 0,  # 暂无市值数据
                "pe": 0,
                "holdShares": round(hold_shares, 2),
                "holdValue": 0,  # 暂无
                "ratio": round(ratio, 2),
                "firstEntry": _date_to_quarter(first_entry.get(sc)),
                "status": status,
                "exitQuarter": exit_q,
            })
        
        # 4. 构建 changes：按报告期对比相邻两期
        changes = []
        by_stock = df.groupby("stock_code")
        for stock_code, g in by_stock:
            g = g.sort_values("report_date")
            rows = list(g.itertuples(index=False))
            stock_name = str(rows[0].stock_name) if hasattr(rows[0], 'stock_name') else str(stock_code)
            for i, r in enumerate(rows):
                rd = r.report_date
                q = _date_to_quarter(rd)
                prev = rows[i - 1] if i > 0 else None
                share_count = int(getattr(r, 'share_count', 0) or 0)
                prev_count = int(getattr(prev, 'share_count', 0) or 0) if prev else 0
                
                if prev is None:
                    action = "新进"
                    change_shares = share_count / 10000.0
                    change_ratio = 100
                else:
                    diff = share_count - prev_count
                    if diff > 0:
                        action = "增持"
                        change_shares = diff / 10000.0
                        change_ratio = (diff / prev_count * 100) if prev_count else 100
                    elif diff < 0:
                        action = "减持"
                        change_shares = diff / 10000.0
                        change_ratio = (diff / prev_count * 100) if prev_count else -100
                    else:
                        continue
                
                changes.append({
                    "quarter": q,
                    "stockCode": str(stock_code),
                    "stockName": stock_name,
                    "action": action,
                    "changeShares": round(change_shares, 2),
                    "changeRatio": round(change_ratio, 2) if action != "新进" else 100,
                })
        
        # 退出：在最后出现的报告期标记
        for stock_code, g in by_stock:
            g = g.sort_values("report_date")
            rows = list(g.itertuples(index=False))
            last_rd = rows[-1].report_date
            if max_date and str(last_rd) != str(max_date):
                stock_name = str(rows[-1].stock_name) if hasattr(rows[-1], 'stock_name') else str(stock_code)
                share_count = int(getattr(rows[-1], 'share_count', 0) or 0)
                changes.append({
                    "quarter": _date_to_quarter(last_rd),
                    "stockCode": str(stock_code),
                    "stockName": stock_name,
                    "action": "退出",
                    "changeShares": -share_count / 10000.0,
                    "changeRatio": -100,
                })
        
        changes.sort(key=lambda x: (x["quarter"], x["stockCode"]), reverse=True)
        
        # 5. 汇总统计 + 最新报告季度（供前端默认时间滑块）
        total_value = sum(h.get("holdValue") or 0 for h in holdings)
        stock_count = len(holdings)
        latest_quarter = _date_to_quarter(max_date) if max_date else None
        
        conn.close()
        
        return {
            "ok": True,
            "shareholder_name": name.strip(),
            "latest_quarter": latest_quarter,
            "info": {
                "name": name.strip(),
                "identity": _infer_identity(str(holdings_raw.iloc[0].get("shareholder_type", ""))),
                "tags": [],
                "stats": {
                    "totalMarketCap": round(total_value, 1),
                    "stockCount": stock_count,
                    "avgHoldPeriod": 12,
                    "winRate": 0,
                },
            },
            "holdings": holdings,
            "changes": changes[:50],
        }
        
    except Exception as e:
        return {"ok": False, "error": str(e), "holdings": [], "changes": []}


def _infer_identity(shareholder_type: str) -> str:
    """从 shareholder_type 推断前端 identity 标签"""
    t = (shareholder_type or "").lower()
    if "社保" in t or "基金" in t and "社保" in t:
        return "社保"
    if "qfii" in t or "境外" in t or "香港" in t:
        return "QFII"
    if "私募" in t or "有限合伙" in t:
        return "私募"
    if "自然人" in t or "个人" in t:
        return "牛散"
    if "公司" in t or "集团" in t or "有限" in t:
        return "产业资本"
    return "私募"


@router.get("/shareholder-tracking/{stock_code}")
def get_shareholder_tracking(
    stock_code: str,
    years: int = Query(5, description="追踪年数"),
    shareholder_name: Optional[str] = Query(None, description="股东名称"),
):
    """
    获取股东追踪报告 (5 年历史)
    
    Args:
        stock_code: 股票代码
        years: 追踪年数
        shareholder_name: 特定股东名称 (可选)
    """
    try:
        analyzer = FinancialAnalyzer()
        tracking = analyzer.get_shareholder_tracking(
            stock_code, years, shareholder_name
        )
        
        return {
            "ok": True,
            "stock_code": stock_code,
            "years": years,
            "data": tracking,
        }
        
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/market-top-changes")
def get_market_top_changes(
    metric_name: str = Query("total_revenue", description="指标名称"),
    report_date: Optional[str] = Query(None, description="报告日期"),
    top_n: int = Query(50, description="返回数量"),
    change_type: str = Query("growth", description="变化类型 (growth/decline)"),
):
    """
    获取全市场变化排名
    
    Args:
        metric_name: 指标名称
        report_date: 报告日期 (可选)
        top_n: 返回数量
        change_type: 变化类型 (growth=增长，decline=下降)
    """
    try:
        analyzer = FinancialAnalyzer()
        changes = analyzer.get_market_top_changes(
            metric_name, report_date, top_n, change_type
        )
        
        return {
            "ok": True,
            "metric": metric_name,
            "change_type": change_type,
            "count": len(changes),
            "data": changes,
        }
        
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/collect")
def trigger_collection(
    stock_codes: Optional[List[str]] = Query(None, description="股票代码列表"),
    report_type: str = Query("年报", description="报告类型"),
    limit: Optional[int] = Query(None, description="限制采集数量"),
):
    """
    触发财报采集任务
    
    Args:
        stock_codes: 股票代码列表 (可选，None 则采集全部 A 股)
        report_type: 报告类型
        limit: 限制采集数量 (可选)
    """
    try:
        collector = FinancialReportCollector()
        
        # 获取股票列表
        if stock_codes is None:
            stocks_df = collector.get_company_list()
            if stocks_df.empty:
                return {"ok": False, "error": "获取股票列表失败"}
            stock_codes = stocks_df["code"].tolist()
        
        # 限制数量
        if limit:
            stock_codes = stock_codes[:limit]
        
        # 执行采集
        stats = collector.collect_all_stocks(
            stock_codes=stock_codes,
            report_type=report_type,
            delay_seconds=0.3
        )
        
        return {
            "ok": True,
            "message": "采集完成",
            "stats": stats,
        }
        
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/anti-quant-pool")
def get_anti_quant_pool(
    limit: int = Query(100, description="返回候选股数量"),
    min_top10_ratio: float = Query(50.0, description="持股集中度下限(%)"),
):
    """
    反量化长线选股池：基于股东稳定性、机构纯度、换主频率筛选的候选股票
    
    返回：候选股票列表、因子汇总、数据覆盖说明
    """
    try:
        import sys
        from pathlib import Path
        _proj = Path(__file__).resolve().parent.parent.parent.parent
        if str(_proj) not in sys.path:
            sys.path.insert(0, str(_proj))
        if str(_proj / "lib") not in sys.path:
            sys.path.insert(0, str(_proj / "lib"))
        from lib.anti_quant_strategy import run_strategy

        factors, candidates = run_strategy()
        if candidates.empty:
            return {
                "ok": True,
                "count": 0,
                "filter_mode": "none",
                "summary": {},
                "data": [],
                "note": "暂无符合条件股票。可放宽 CONFIG 中阈值。",
            }

        # 按持股集中度过滤
        candidates = candidates[candidates["top10_ratio_latest"] >= min_top10_ratio]
        if candidates.empty:
            return {
                "ok": True,
                "count": 0,
                "filter_mode": "relaxed",
                "summary": {"total_stocks_analyzed": len(factors), "candidate_count": 0},
                "data": [],
                "note": f"持股集中度≥{min_top10_ratio}% 时无候选。可调低 min_top10_ratio。",
            }
        candidates = candidates.head(limit)

        # 关联股票名称
        from lib.database import get_connection
        conn = get_connection(read_only=False)
        names_df = pd.DataFrame()
        try:
            if conn and not candidates.empty:
                codes = candidates["stock_code"].astype(str).tolist()
                placeholders = ",".join(["?"] * len(codes))
                try:
                    names_df = conn.execute(
                        f"SELECT code, name FROM a_stock_basic WHERE code IN ({placeholders})",
                        codes,
                    ).fetchdf()
                except Exception:
                    pass
        finally:
            if conn:
                conn.close()
        names_map = dict(zip(names_df["code"].astype(str), names_df["name"].astype(str))) if not names_df.empty else {}

        data = []
        for _, row in candidates.iterrows():
            sc = str(row["stock_code"])
            data.append({
                "stock_code": sc,
                "stock_name": names_map.get(sc, sc),
                "top10_ratio": round(float(row.get("top10_ratio_latest", 0)), 2),
                "top10_ratio_std": round(float(row["top10_ratio_std"]), 2) if pd.notna(row.get("top10_ratio_std")) else None,
                "institution_count_current": int(row.get("institution_count_current", 0)),
                "long_term_institution_count": float(row.get("long_term_institution_count", 0)),
                "turnover_avg": round(float(row["turnover_avg"]), 2) if pd.notna(row.get("turnover_avg")) else None,
                "report_count": int(row.get("report_count", 0)),
                "latest_report_date": str(row.get("latest_report_date"))[:10] if pd.notna(row.get("latest_report_date")) else None,
                "filter_mode": str(row.get("filter_mode", "relaxed")),
            })

        # 汇总统计
        summary = {
            "total_stocks_analyzed": len(factors),
            "candidate_count": len(candidates),
            "avg_top10_ratio": round(candidates["top10_ratio_latest"].mean(), 2),
            "avg_institution_count": round(candidates["institution_count_current"].mean(), 2),
            "filter_mode": str(candidates["filter_mode"].iloc[0]) if not candidates.empty else "relaxed",
        }

        return {
            "ok": True,
            "count": len(data),
            "filter_mode": summary["filter_mode"],
            "summary": summary,
            "data": data,
            "note": "当报告期不足 4 期时使用放宽规则：持股集中度≥50%、当前机构数≥2。完整 5 年数据后可启用严格规则。",
        }
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "trace": traceback.format_exc(), "data": []}


@router.get("/anti-quant-stock/{stock_code}")
def get_anti_quant_stock_factors(stock_code: str):
    """
    单只股票的反量化因子详情
    """
    try:
        import sys
        from pathlib import Path
        _proj = Path(__file__).resolve().parent.parent.parent.parent
        if str(_proj) not in sys.path:
            sys.path.insert(0, str(_proj))
        if str(_proj / "lib") not in sys.path:
            sys.path.insert(0, str(_proj / "lib"))
        from lib.anti_quant_strategy import run_strategy

        factors, candidates = run_strategy()
        sc = str(stock_code).zfill(6)
        f = factors[factors["stock_code"].astype(str) == sc]
        if f.empty:
            return {"ok": False, "error": "未找到该股票因子数据", "stock_code": stock_code}

        row = f.iloc[0]
        is_candidate = not candidates[candidates["stock_code"].astype(str) == sc].empty

        return {
            "ok": True,
            "stock_code": stock_code,
            "in_pool": is_candidate,
            "factors": {
                "top10_ratio": round(float(row.get("top10_ratio_latest", 0)), 2),
                "top10_ratio_std": round(float(row["top10_ratio_std"]), 2) if pd.notna(row.get("top10_ratio_std")) else None,
                "institution_count_current": int(row.get("institution_count_current", 0)),
                "long_term_institution_count": float(row.get("long_term_institution_count", 0)),
                "turnover_avg": round(float(row["turnover_avg"]), 2) if pd.notna(row.get("turnover_avg")) else None,
                "report_count": int(row.get("report_count", 0)),
                "data_sufficient": bool(row.get("data_sufficient", False)),
            },
            "latest_report_date": str(row.get("latest_report_date"))[:10] if pd.notna(row.get("latest_report_date")) else None,
        }
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "trace": traceback.format_exc()}


@router.get("/overview")
def get_financial_overview():
    """
    获取财报数据概览
    
    返回：
    - 已采集股票数量
    - 财报记录总数
    - 股东记录总数
    - 最新报告日期
    """
    try:
        from lib.database import get_connection
        conn = get_connection(read_only=False)
        if conn is None:
            return {"ok": False, "error": "数据库连接失败", "data": {}}
        
        # 统计股票数量
        stock_count = conn.execute("""
            SELECT COUNT(DISTINCT stock_code) FROM financial_report
        """).fetchone()[0]
        
        # 统计财报记录数
        report_count = conn.execute("""
            SELECT COUNT(*) FROM financial_report
        """).fetchone()[0]
        
        # 统计股东记录数
        holder_count = conn.execute("""
            SELECT COUNT(*) FROM top_10_shareholders
        """).fetchone()[0]
        
        # 最新报告日期
        latest_report = conn.execute("""
            SELECT MAX(report_date) FROM financial_report
        """).fetchone()[0]
        
        latest_holder = conn.execute("""
            SELECT MAX(report_date) FROM top_10_shareholders
        """).fetchone()[0]
        
        conn.close()
        
        return {
            "ok": True,
            "data": {
                "stock_count": stock_count or 0,
                "report_count": report_count or 0,
                "holder_count": holder_count or 0,
                "latest_report_date": str(latest_report) if latest_report else None,
                "latest_holder_date": str(latest_holder) if latest_holder else None,
            },
        }
        
    except Exception as e:
        return {"ok": False, "error": str(e)}
