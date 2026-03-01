# -*- coding: utf-8 -*-
"""
生产级 API 入口：可独立运行（python backend/api/main.py）或由 web_platform 挂载。
提供策略、组合、订单、账户、AI 决策等接口。
"""
from __future__ import annotations
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "institutional-api"})


@app.route("/api/strategy/run", methods=["POST"])
def strategy_run():
    """运行策略池。Body: { symbols?: [], strategy?: "dragon"|"trend"|"mean" }"""
    try:
        data = request.json or {}
        from backend.strategy.dragon import DragonStrategy
        from backend.strategy.trend import TrendStrategy
        from backend.strategy.mean_reversion import MeanReversion
        from data.data_loader import load_kline
        from datetime import datetime, timedelta
        symbols = data.get("symbols") or ["000001", "600519"]
        strategy_name = (data.get("strategy") or "trend").strip().lower()
        end = datetime.now().date()
        start = (end - timedelta(days=120)).strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")
        if strategy_name == "dragon":
            st = DragonStrategy()
        elif strategy_name == "mean":
            st = MeanReversion()
        else:
            st = TrendStrategy()
        results = []
        for code in symbols[:50]:
            try:
                df = load_kline(code, start, end_str, source="database")
                if df is None or len(df) < 60:
                    continue
                if "close" not in df.columns and "收盘" in df.columns:
                    df["close"] = df["收盘"]
                out = st.generate(df, code=code)
                for o in out:
                    o["strategy"] = strategy_name
                    results.append(o)
            except Exception:
                continue
        return jsonify({"success": True, "data": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/ai/decision", methods=["GET"])
def ai_decision():
    """AI 基金经理当前决策。"""
    try:
        from backend.ai.fund_manager import AIFundManager
        mgr = AIFundManager()
        market = {"index_ma20": 1, "index_ma60": 0.9}
        weights = mgr.decide(market)
        return jsonify({"success": True, "regime": mgr.get_last_regime(), "weights": weights})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "regime": "bear", "weights": {"dragon": 0.2, "trend": 0.2, "mean": 0.2, "cash": 0.4}}), 500


@app.route("/api/account", methods=["GET"])
def account():
    """资金与持仓。"""
    try:
        from backend.broker.sim import SimBroker
        b = SimBroker()
        return jsonify({"success": True, "balance": b.get_balance(), "positions": b.query_position(None)})
    except Exception as e:
        return jsonify({"success": True, "balance": {"total_asset": 1000000, "cash": 1000000, "frozen": 0}, "positions": {}})


@app.route("/api/order", methods=["POST"])
def order_place():
    """下单。Body: { symbol, qty, side, price? }"""
    try:
        data = request.json or {}
        from backend.execution.engine import ExecutionEngine
        eng = ExecutionEngine(broker_mode="simulation")
        order = eng.place_order(
            data.get("symbol", "").strip(),
            int(data.get("qty") or 0),
            (data.get("side") or "BUY").upper(),
            data.get("price"),
        )
        return jsonify({"success": True, "order": order})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def create_app():
    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5051))
    host = os.environ.get("HOST", "127.0.0.1")
    print("Institutional API: http://{}:{}".format(host, port))
    app.run(host=host, port=port, debug=True)
