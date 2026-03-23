"""System data overview endpoint: 涨停池、狙击候选、交易信号、新闻等数据统计。"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/system/data-overview")
def get_system_data_overview() -> dict:
    """
    获取系统关键数据统计，供前端 Dashboard 展示：
    - 涨停池：a_stock_limitup 条数
    - 狙击候选：sniper_candidates 条数
    - 交易信号：trade_signals 条数
    - 新闻数据：news_items 条数
    - 股票池：a_stock_basic 条数
    - 日 K 线：a_stock_daily 条数
    - 龙虎榜：a_stock_longhubang 条数
    - 资金流：a_stock_fundflow 条数
    - 情绪状态：market_emotion 最新 state
    - 游资席位：top_hotmoney_seats 条数
    """
    from data_pipeline.storage.duckdb_manager import get_conn

    conn = None
    try:
        conn = get_conn()
        if not conn:
            return {
                "ok": False,
                "error": "无法连接数据库",
                "counts": {},
            }

        # 并行查询所有表
        counts = {}
        
        # 涨停池
        try:
            result = conn.execute("SELECT COUNT(*) FROM a_stock_limitup").fetchone()
            counts["limitup_pool"] = result[0] if result else 0
        except Exception:
            counts["limitup_pool"] = 0

        # 狙击候选
        try:
            result = conn.execute("SELECT COUNT(*) FROM sniper_candidates").fetchone()
            counts["sniper_candidates"] = result[0] if result else 0
        except Exception:
            counts["sniper_candidates"] = 0

        # 交易信号
        try:
            result = conn.execute("SELECT COUNT(*) FROM trade_signals").fetchone()
            counts["trade_signals"] = result[0] if result else 0
        except Exception:
            counts["trade_signals"] = 0

        # 新闻数据
        try:
            result = conn.execute("SELECT COUNT(*) FROM news_items").fetchone()
            counts["news_items"] = result[0] if result else 0
        except Exception:
            counts["news_items"] = 0

        # 股票池
        try:
            result = conn.execute("SELECT COUNT(*) FROM a_stock_basic").fetchone()
            counts["stock_pool"] = result[0] if result else 0
        except Exception:
            counts["stock_pool"] = 0

        # 日 K 线
        try:
            result = conn.execute("SELECT COUNT(*) FROM a_stock_daily").fetchone()
            counts["daily_bars"] = result[0] if result else 0
        except Exception:
            counts["daily_bars"] = 0

        # 龙虎榜：按「代码+上榜日」有效条数统计（与下钻 API 一致，不含 lhb_date 为空的脏行）
        try:
            result = conn.execute(
                """
                SELECT COUNT(*) FROM (
                    SELECT 1 FROM a_stock_longhubang
                    WHERE lhb_date IS NOT NULL
                      AND code IS NOT NULL
                      AND LENGTH(TRIM(CAST(code AS VARCHAR))) >= 4
                    GROUP BY code, lhb_date
                ) t
                """
            ).fetchone()
            counts["longhubang"] = result[0] if result else 0
        except Exception:
            counts["longhubang"] = 0

        # 资金流
        try:
            result = conn.execute("SELECT COUNT(*) FROM a_stock_fundflow").fetchone()
            counts["fundflow"] = result[0] if result else 0
        except Exception:
            counts["fundflow"] = 0

        # 情绪状态（最新）
        emotion_state = None
        try:
            result = conn.execute(
                "SELECT emotion_state FROM market_emotion ORDER BY trade_date DESC LIMIT 1"
            ).fetchone()
            emotion_state = result[0] if result else None
        except Exception:
            pass
        counts["emotion_state"] = emotion_state

        # 游资席位
        try:
            result = conn.execute("SELECT COUNT(*) FROM top_hotmoney_seats").fetchone()
            counts["hotmoney_seats"] = result[0] if result else 0
        except Exception:
            counts["hotmoney_seats"] = 0

        return {
            "ok": True,
            "counts": counts,
            "summary": {
                "limitup_pool": counts.get("limitup_pool", 0),
                "sniper_candidates": counts.get("sniper_candidates", 0),
                "trade_signals": counts.get("trade_signals", 0),
                "news_items": counts.get("news_items", 0),
            },
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "counts": {},
        }
    finally:
        if conn:
            conn.close()
