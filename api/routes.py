# -*- coding: utf-8 -*-
"""
API 路由注册：组合回测、TradingView K 线数据、股票池等。
与 web_platform 主应用解耦，通过 register_routes(app) 挂载。
"""
import os
from flask import Blueprint, request, jsonify

_API_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _root():
    import sys
    if _API_ROOT not in sys.path:
        sys.path.insert(0, _API_ROOT)
    return _API_ROOT


def create_api_blueprint():
    """创建 API 蓝图，供主应用注册。"""
    bp = Blueprint("api_extra", __name__, url_prefix="/api")

    @bp.route("/portfolio", methods=["POST"])
    def portfolio_backtest():
        """
        多策略组合回测。
        Body: { strategies: [{ strategy_id, weight, symbol? }], stockCode, startDate, endDate, timeframe? }
        """
        _root()
        try:
            data = request.json or {}
            strategies = data.get("strategies") or []
            stock_code = data.get("stockCode")
            start_date = data.get("startDate")
            end_date = data.get("endDate")
            timeframe = (data.get("timeframe") or "D").strip().upper() or "D"
            if timeframe not in ("D", "W", "M"):
                timeframe = "D"
            if not strategies or not stock_code or not start_date or not end_date:
                return jsonify({"success": False, "error": "参数不完整"}), 400
            from portfolio import run_portfolio_backtest
            result = run_portfolio_backtest(
                strategies=strategies,
                stock_code=stock_code,
                start_date=start_date,
                end_date=end_date,
                timeframe=timeframe,
            )
            if result.get("error"):
                return jsonify({"success": False, "error": result["error"]}), 400
            return jsonify({"success": True, "result": result})
        except Exception as e:
            import traceback
            return jsonify({"success": False, "error": str(e), "detail": traceback.format_exc()}), 500

    @bp.route("/tv_kline", methods=["POST"])
    def tv_kline():
        """
        将回测 result 转为 TradingView 级 K 线数据结构。
        Body: { result: { kline, markers, ... } }
        """
        _root()
        try:
            data = request.json or {}
            result = data.get("result") or {}
            from core.tv_kline import to_tv_series_payload
            payload = to_tv_series_payload(result)
            return jsonify({"success": True, "payload": payload})
        except Exception as e:
            import traceback
            return jsonify({"success": False, "error": str(e), "detail": traceback.format_exc()}), 500

    @bp.route("/universe", methods=["GET"])
    def universe():
        """
        获取股票池（A 股）。
        Query: source=database|csv, limit=, csvPath=
        """
        _root()
        try:
            source = request.args.get("source", "database")
            limit = request.args.get("limit", type=int)
            csv_path = request.args.get("csvPath")
            from data import get_universe
            u = get_universe(source=source, limit=limit, csv_path=csv_path)
            return jsonify({"success": True, "universe": u.to_dict_list(), "source": u.source, "count": len(u)})
        except Exception as e:
            import traceback
            return jsonify({"success": False, "error": str(e), "universe": []}), 500

    return bp


def register_routes(app):
    """将 API 蓝图注册到 Flask 应用。"""
    bp = create_api_blueprint()
    app.register_blueprint(bp)
