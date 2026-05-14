"""
新数据 API 端点

提供金融财报、公司传闻、预警提醒等新型数据的只读查询接口。

API 列表:
- GET /new-data/financial-reports - 查询金融财报
- GET /new-data/rumors - 查询公司传闻/谣言
- GET /new-data/alerts - 查询预警提醒（含回购事件详情）
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Query

router = APIRouter(prefix="/new-data", tags=["新数据"])


@router.get("/financial-reports")
def get_financial_reports(
    stock_code: str = Query(..., description="股票代码"),
    limit: int = Query(10, ge=1, le=100, description="返回数量"),
    statement_type: Optional[str] = Query(None, description="报表类型，如 利润表、资产负债表、现金流量表"),
):
    """
    查询 financial_reports 表，获取指定股票的财报数据。

    Args:
        stock_code: 股票代码
        limit: 返回记录数上限
        statement_type: 报表类型过滤（可选）
    """
    try:
        from lib.database import get_connection

        conn = get_connection(read_only=False)
        if conn is None:
            return {"ok": False, "error": "数据库连接失败"}

        query = """
            SELECT stock_code, report_date, report_type, statement_type,
                   period_end, data_json, currency, created_at
            FROM financial_reports
            WHERE stock_code = ?
        """
        params = [stock_code]

        if statement_type:
            query += " AND statement_type = ?"
            params.append(statement_type)

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


@router.get("/rumors")
def get_rumors(
    stock_code: str = Query(..., description="股票代码"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    days: int = Query(7, ge=1, le=365, description="回溯天数"),
    rumor_type: Optional[str] = Query(None, description="传闻类型过滤"),
):
    """
    查询 company_rumors 表，获取指定股票的公司传闻/谣言。

    Args:
        stock_code: 股票代码
        limit: 返回记录数上限
        days: 回溯天数（基于 publish_time）
        rumor_type: 传闻类型过滤（可选）
    """
    try:
        from lib.database import get_connection

        conn = get_connection(read_only=False)
        if conn is None:
            return {"ok": False, "error": "数据库连接失败"}

        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

        query = """
            SELECT id, stock_code, title, content, source, source_url,
                   rumor_type, publish_time, keywords, sentiment_score, created_at
            FROM company_rumors
            WHERE stock_code = ?
              AND (publish_time IS NULL OR publish_time >= ?)
        """
        params = [stock_code, cutoff]

        if rumor_type:
            query += " AND rumor_type = ?"
            params.append(rumor_type)

        query += " ORDER BY publish_time DESC NULLS LAST LIMIT ?"
        params.append(limit)

        df = conn.execute(query, params).fetchdf()
        conn.close()

        if df.empty:
            return {"ok": False, "error": "未找到传闻数据", "stock_code": stock_code}

        return {
            "ok": True,
            "stock_code": stock_code,
            "count": len(df),
            "data": df.to_dict("records"),
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/alerts")
def get_alerts(
    stock_code: Optional[str] = Query(None, description="股票代码（可选，不传则返回全部）"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    alert_type: Optional[str] = Query(None, description="预警类型过滤"),
):
    """
    查询 alerts 表，获取指定股票的预警提醒。若关联了回购事件，
    会 LEFT JOIN buyback_events 获取事件详情。

    Args:
        stock_code: 股票代码
        limit: 返回记录数上限
        alert_type: 预警类型过滤（可选）
    """
    try:
        from lib.database import get_connection

        conn = get_connection(read_only=False)
        if conn is None:
            return {"ok": False, "error": "数据库连接失败"}

        query = """
            SELECT
                a.id,
                a.alert_type,
                a.stock_code,
                a.stock_name,
                a.trigger_reason,
                a.consecutive_drop_days,
                a.total_drop_pct,
                a.related_event_id,
                a.related_event_type,
                a.details,
                a.created_at,
                b.event_type AS buyback_event_type,
                b.announcement_date AS buyback_announcement_date,
                b.total_amount AS buyback_total_amount,
                b.price_low AS buyback_price_low,
                b.price_high AS buyback_price_high,
                b.planned_shares AS buyback_planned_shares,
                b.actual_shares AS buyback_actual_shares,
                b.status AS buyback_status,
                b.summary AS buyback_summary
            FROM alerts a
            LEFT JOIN buyback_events b ON a.related_event_id = b.id
            WHERE 1=1
        """
        params: list = []

        if stock_code:
            query += " AND a.stock_code = ?"
            params.append(stock_code)

        if alert_type:
            query += " AND a.alert_type = ?"
            params.append(alert_type)

        query += " ORDER BY a.created_at DESC LIMIT ?"
        params.append(limit)

        df = conn.execute(query, params).fetchdf()
        conn.close()

        if df.empty:
            return {"ok": False, "error": "未找到预警数据", "stock_code": stock_code}

        return {
            "ok": True,
            "stock_code": stock_code,
            "count": len(df),
            "data": df.to_dict("records"),
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}
