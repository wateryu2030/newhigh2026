# -*- coding: utf-8 -*-
"""
专业交易仪表盘：账户总览、资金曲线、持仓、信号、市场状态、风险灯。
运行: streamlit run ui/dashboard.py
"""
from __future__ import annotations
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

import streamlit as st
import pandas as pd

try:
    import plotly.express as px
    import plotly.graph_objects as go
    _HAS_PLOTLY = True
except ImportError:
    _HAS_PLOTLY = False


def _demo_account():
    """演示用账户数据。"""
    from paper_trading import PaperBroker, TradeEngine
    from strategies.ma_cross import MACrossStrategy
    from data.data_loader import load_kline
    broker = PaperBroker(1_000_000)
    engine = TradeEngine(broker=broker)
    strat = MACrossStrategy()
    try:
        df = load_kline("000001", "2024-01-01", "2024-12-31", source="akshare")
        if df is None or len(df) < 30:
            df = load_kline("600519", "2024-01-01", "2024-06-30", source="akshare")
    except Exception:
        df = None
    if df is not None and len(df) >= 20:
        def get_sigs(d):
            return strat.generate_signals(d)
        engine.run_from_kline(df, "000001.XSHG" if "6" in str(df) else "000001.XSHE", get_sigs)
    return broker.account


def _risk_color(level: str) -> str:
    m = {"LOW": "#00ff00", "NORMAL": "#ffaa00", "HIGH": "#ff6600", "STOP": "#ff0000"}
    return m.get(level, "#888")


def main():
    st.set_page_config(page_title="量化交易仪表盘", page_icon="📊", layout="wide")
    st.title("📊 量化交易仪表盘")
    st.caption("newhigh2026 - AKShare + RQAlpha + 模拟交易")

    # 尝试加载真实账户，失败则用演示
    account = None
    try:
        from paper_trading import PaperBroker
        # 这里可以接入持久化账户
        account = _demo_account()
    except Exception as e:
        st.warning(f"使用演示数据: {e}")
        account = _demo_account()

    if account is None:
        st.error("无法加载账户数据")
        return

    # 1. 账户总览
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("当前资产", f"¥{account.total_equity:,.0f}")
    with col2:
        ret = account.profit_ratio
        st.metric("收益率", f"{ret:.2%}", delta=f"{ret:.2%}")
    with col3:
        dd = account.max_drawdown
        st.metric("最大回撤", f"{dd:.2%}")
    with col4:
        pos_val = account.position_value
        tot = account.total_equity or 1
        st.metric("持仓比例", f"{pos_val/tot:.1%}")

    # 2. 资金曲线
    st.subheader("资金曲线")
    if account.equity_curve:
        eq_df = pd.DataFrame(account.equity_curve, columns=["date", "equity"])
        if _HAS_PLOTLY:
            fig = px.line(eq_df, x="date", y="equity", title="权益曲线")
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.line_chart(eq_df.set_index("date"))
    else:
        st.info("暂无权益曲线数据")

    # 3. 当前持仓
    st.subheader("当前持仓")
    if account.positions:
        rows = []
        for sym, pos in account.positions.items():
            rows.append({
                "标的": sym,
                "数量": pos.amount,
                "成本价": f"{pos.cost_price:.2f}",
                "现价": f"{pos.current_price:.2f}" if pos.current_price else "-",
                "市值": f"{pos.market_value:,.0f}",
                "盈亏比例": f"{pos.profit_ratio:.2%}",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else:
        st.info("暂无持仓")

    # 4. 今日信号（演示占位）
    st.subheader("今日交易信号")
    st.info("接入策略模块后在此展示 BUY/SELL 信号")

    # 5 & 6. 市场状态 + 风险灯
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("市场状态")
        st.markdown("**BULL** / NEUTRAL / BEAR（接入指数数据后展示）")
    with col_b:
        st.subheader("风险状态灯")
        risk_level = "NORMAL"
        color = _risk_color(risk_level)
        st.markdown(f'<span style="color:{color};font-size:24px;">● {risk_level}</span>', unsafe_allow_html=True)

    # 7. 最近交易
    st.subheader("最近交易记录")
    if account.trades:
        rows = []
        for t in account.trades[-20:]:
            rows.append({"日期": t.date, "标的": t.symbol, "方向": t.side, "价格": t.price, "数量": t.amount, "金额": t.total})
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else:
        st.info("暂无交易记录")


if __name__ == "__main__":
    main()
