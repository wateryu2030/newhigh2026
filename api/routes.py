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

    @bp.route("/news", methods=["GET"])
    def news():
        """
        新闻采集 + 舆情分析。
        Query: symbol=, sources=eastmoney,caixin,douyin (逗号分隔)
        """
        _root()
        try:
            symbol = request.args.get("symbol", "600519")
            sources_str = request.args.get("sources", "eastmoney,caixin")
            sources = [s.strip() for s in sources_str.split(",") if s.strip()]
            limit = request.args.get("limit", type=int) or 30
            from news import fetch_all_news, analyze_sentiment, aggregate_sentiment
            raw = fetch_all_news(symbol=symbol, sources=sources, limit_per_source=limit)
            all_items = []
            for site, items in raw.items():
                filtered = [x for x in items if not x.get("error")]
                all_items.extend(filtered)
            analyzed = analyze_sentiment(all_items)
            agg = aggregate_sentiment(analyzed)
            return jsonify({
                "success": True,
                "symbol": symbol,
                "news": analyzed,
                "sentiment": agg,
                "count": len(analyzed),
            })
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

    @bp.route("/ai_recommendations", methods=["GET"])
    def ai_recommendations():
        """
        AI 选股推荐 Top N。
        Query: top=20
        """
        _root()
        try:
            import sys
            if _API_ROOT not in sys.path:
                sys.path.insert(0, _API_ROOT)
            top = request.args.get("top", type=int) or 20
            top = min(max(1, top), 50)
            from datetime import datetime, timedelta
            try:
                from data.data_loader import load_kline
            except Exception:
                import importlib.util
                spec = importlib.util.spec_from_file_location("data_loader", os.path.join(_API_ROOT, "data", "data_loader.py"))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                load_kline = mod.load_kline
            try:
                from data.stock_pool import get_a_share_symbols
                symbols = get_a_share_symbols(exclude_delisted=True)
            except Exception:
                symbols = []
            if not symbols:
                try:
                    from database.data_fetcher import get_all_a_share_symbols
                    symbols = get_all_a_share_symbols()
                except Exception:
                    symbols = ["000001", "600519", "000858", "600036", "600745", "300750", "601318", "000333"]
            if len(symbols) > 200:
                symbols = symbols[:200]
            end = datetime.now().date()
            start = (end - timedelta(days=120)).strftime("%Y-%m-%d")
            end_str = end.strftime("%Y-%m-%d")
            market_data = {}
            for code in symbols:
                df = load_kline(code, start, end_str, source="database")
                if df is None or len(df) < 60:
                    df = load_kline(code, start, end_str, source="akshare")
                if df is not None and len(df) >= 60:
                    key = code + ".XSHG" if code.startswith("6") else code + ".XSHE"
                    market_data[key] = df
            from ai_models.model_manager import ModelManager
            from ai_models.signal_ranker import rank_signals, top_n_symbols
            manager = ModelManager()
            ai_scores = manager.predict(market_data)
            if ai_scores is None or ai_scores.empty:
                return jsonify({"success": True, "list": [], "message": "未找到已训练模型，请先运行 train_ai_model.py"})
            ranked = rank_signals(ai_scores, ai_weight=1.0, strategy_weight=0.0)
            top_list = top_n_symbols(ranked, n=top)
            rows = []
            for i, sym in enumerate(top_list, 1):
                r = ranked[ranked["symbol"] == sym].iloc[0]
                rows.append({"rank": i, "symbol": sym, "score": round(float(r["final_score"]), 4)})
            return jsonify({"success": True, "list": rows})
        except Exception as e:
            import traceback
            return jsonify({"success": False, "error": str(e), "list": [], "detail": traceback.format_exc()}), 500

    @bp.route("/portfolio_result", methods=["POST"])
    def portfolio_result():
        """
        机构组合结果：多策略信号 → 资金分配 → 风控 → 目标仓位。
        Body: { stockCodes?: string[], capital?: number }
        """
        _root()
        try:
            data = request.json or {}
            symbols = data.get("stockCodes") or []
            capital = float(data.get("capital") or 1000000)
            if not symbols:
                try:
                    from data.stock_pool import get_a_share_symbols
                    symbols = get_a_share_symbols(exclude_delisted=True)
                except Exception:
                    pass
                if not symbols:
                    try:
                        from database.data_fetcher import get_all_a_share_symbols
                        symbols = get_all_a_share_symbols()
                    except Exception:
                        pass
                if not symbols:
                    symbols = ["000001", "600519", "000858", "600036", "600745", "300750"]
                if len(symbols) > 100:
                    symbols = symbols[:100]
            from datetime import datetime, timedelta
            from data.data_loader import load_kline
            end = datetime.now().date()
            start = (end - timedelta(days=120)).strftime("%Y-%m-%d")
            end_str = end.strftime("%Y-%m-%d")
            market_data = {}
            for code in symbols:
                c = code.split(".")[0] if "." in code else code
                df = load_kline(c, start, end_str, source="database")
                if df is not None and len(df) >= 60:
                    key = code if "." in code else (c + ".XSHG" if c.startswith("6") else c + ".XSHE")
                    market_data[key] = df
            from engine import InstitutionalPortfolioEngine
            engine = InstitutionalPortfolioEngine(capital=capital, max_positions=15)
            result = engine.run(market_data, index_df=None, current_max_drawdown=0.0)
            orders = result.get("orders") or []
            target_positions = result.get("target_positions") or {}
            risk_scale = result.get("risk_scale", 1.0)
            return jsonify({
                "success": True,
                "orders": orders,
                "target_positions": target_positions,
                "risk_scale": risk_scale,
                "count": len(orders),
            })
        except Exception as e:
            import traceback
            return jsonify({"success": False, "error": str(e), "orders": [], "target_positions": {}, "detail": traceback.format_exc()}), 500

    return bp


def register_routes(app):
    """将 API 蓝图注册到 Flask 应用。"""
    bp = create_api_blueprint()
    app.register_blueprint(bp)
