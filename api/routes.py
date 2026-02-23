# -*- coding: utf-8 -*-
"""
API 路由注册：组合回测、TradingView K 线数据、股票池等。
与 web_platform 主应用解耦，通过 register_routes(app) 挂载。
"""
import os
from flask import Blueprint, request, jsonify, send_file, Response, stream_with_context
import io
import json
import queue
import threading
import time

_API_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _root():
    import sys
    if _API_ROOT not in sys.path:
        sys.path.insert(0, _API_ROOT)
    return _API_ROOT


def _get_full_symbols() -> list:
    """全量 A 股代码（不含退市），不限制数量。"""
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
            symbols = []
    if not symbols:
        return ["000001", "600519", "000858", "600036", "600745", "300750"]
    return symbols


def _get_stock_names() -> dict:
    """{ symbol: name }，供自然语言筛选用。"""
    try:
        from data.stock_pool import get_a_share_list
        lst = get_a_share_list()
        return {str(x.get("symbol", "")).strip(): str(x.get("name", "")).strip() for x in lst if x.get("symbol")}
    except Exception:
        return {}


def _apply_nl_filter(candidates: list, description: str, name_map: dict) -> list:
    """
    按自然语言描述从候选中筛选。
    candidates: [{"symbol": "600519", "score": 0.8}, ...] 或 [{"symbol": "600519", "value": 100000}, ...]
    description: 如 "低估值高分红、科技龙头、消费白马"
    返回: 筛选后的列表，保持原顺序或按 LLM 排序
    """
    if not description or not description.strip():
        return candidates
    desc = description.strip()
    # 准备 symbol -> name 映射
    for c in candidates:
        sym = c.get("symbol", "")
        if sym and sym not in name_map:
            code = sym.split(".")[0] if "." in sym else sym
            name_map[code] = name_map.get(code, code)
    # LLM 筛选（若有 OPENAI_API_KEY）
    if os.environ.get("OPENAI_API_KEY"):
        try:
            from openai import OpenAI
            kw = {"api_key": os.environ.get("OPENAI_API_KEY")}
            base = os.environ.get("OPENAI_API_BASE", "").strip()
            if base:
                kw["base_url"] = base.rstrip("/")
            client = OpenAI(**kw)
            lines = []
            for c in candidates:
                sym = c.get("symbol", "")
                code = sym.split(".")[0] if "." in sym else sym
                name = name_map.get(code, "")
                score = c.get("score", c.get("value", ""))
                lines.append(f"{code} {name} {score}")
            prompt = f"""用户选股要求：{desc}

候选股票（代码 名称 得分/金额）：
{chr(10).join(lines[:500])}

请从候选中筛选符合要求的股票，按相关性从高到低排序。
只返回股票代码列表，每行一个，如：
600519
000858
不要解释、不要其他内容。"""
            resp = client.chat.completions.create(
                model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=2000,
            )
            body = (resp.choices[0].message.content or "").strip()
            import re
            selected = []
            for line in body.splitlines():
                parts = re.findall(r"\d{6}", line)
                if parts:
                    selected.append(parts[0])
            # 按 selected 顺序过滤，未在 selected 中的忽略
            sel_set = {s.split(".")[0] if "." in s else s for s in selected}
            order_map = {s: i for i, s in enumerate(selected)}
            filtered = [c for c in candidates if (c.get("symbol") or "").split(".")[0] in sel_set]
            filtered.sort(key=lambda c: order_map.get((c.get("symbol") or "").split(".")[0], 9999))
            return filtered
        except Exception:
            pass
    # 回退：关键词匹配（按名称）
    keys = [k.strip() for k in desc.replace("、", " ").replace(",", " ").split() if k.strip()]
    if not keys:
        return candidates
    out = []
    for c in candidates:
        sym = c.get("symbol", "")
        code = sym.split(".")[0] if "." in sym else sym
        name = name_map.get(code, "")
        if any(k in name for k in keys):
            out.append(c)
    return out if out else candidates


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

    @bp.route("/market/sector_strength", methods=["GET"])
    def market_sector_strength():
        """板块强度（涨幅排名），用于热点与市场状态。"""
        _root()
        try:
            from market import get_sector_strength
            top = request.args.get("top", type=int) or 20
            rows = get_sector_strength(top_n=top)
            return jsonify({"success": True, "sectors": rows})
        except Exception as e:
            import traceback
            return jsonify({"success": False, "error": str(e), "sectors": [], "detail": traceback.format_exc()}), 500

    @bp.route("/market/regime", methods=["GET"])
    def market_regime():
        """市场状态：牛熊/震荡。基于指数 MA 与板块强度简要判断。"""
        _root()
        try:
            from market import get_sector_strength
            sectors = get_sector_strength(top_n=10)
            avg_strength = sum(s.get("strength", 50) for s in sectors) / len(sectors) if sectors else 50
            if avg_strength >= 60:
                regime = "BULL"
                desc = "偏多"
            elif avg_strength <= 40:
                regime = "BEAR"
                desc = "偏空"
            else:
                regime = "NEUTRAL"
                desc = "震荡"
            return jsonify({"success": True, "regime": regime, "description": desc, "avg_strength": round(avg_strength, 1)})
        except Exception as e:
            return jsonify({"success": False, "error": str(e), "regime": "NEUTRAL", "description": "未知"}), 500

    @bp.route("/scan/professional", methods=["POST"])
    def scan_professional():
        """
        专业级扫描：形态 + 热点 + 风险预算 + AI 排序。
        Body: { strategy_ids?, use_pattern_filter?, use_hot_filter?, use_ai_rank?, top_n?, capital?, risk_pct?, stop_loss_pct? }
        """
        _root()
        try:
            from scanner.scanner_pipeline import run_professional_scan
            data = request.json or {}
            strategy_ids = data.get("strategy_ids") or ["ma_cross", "rsi", "macd", "breakout"]
            top_n = max(1, min(100, int(data.get("top_n") or 50)))
            results = run_professional_scan(
                strategy_ids=strategy_ids,
                use_pattern_filter=data.get("use_pattern_filter", True),
                use_hot_filter=data.get("use_hot_filter", True),
                use_risk_budget=True,
                use_ai_rank=data.get("use_ai_rank", True),
                capital=float(data.get("capital") or 1000000),
                risk_pct=float(data.get("risk_pct") or 0.01),
                stop_loss_pct=float(data.get("stop_loss_pct") or 0.05),
                top_n=top_n,
                stock_limit=int(data.get("stock_limit") or 500),
            )
            return jsonify({"success": True, "results": results, "count": len(results)})
        except Exception as e:
            import traceback
            return jsonify({"success": False, "error": str(e), "results": [], "detail": traceback.format_exc()}), 500

    @bp.route("/scan/professional/stream", methods=["POST"])
    def scan_professional_stream():
        """
        专业扫描流式接口：通过 SSE 推送进度与最终结果，便于前端显示进度条。
        Body 同 /scan/professional。
        """
        _root()
        data = request.json or {}
        strategy_ids = data.get("strategy_ids") or ["ma_cross", "rsi", "macd", "breakout"]
        top_n = max(1, min(100, int(data.get("top_n") or 50)))
        stock_limit = int(data.get("stock_limit") or 500)
        q = queue.Queue()
        scan_result = {"results": [], "error": None}

        def run_scan():
            try:
                from scanner.scanner_pipeline import run_professional_scan
                def progress_cb(phase, current, total, message):
                    q.put({"type": "progress", "phase": phase, "current": current, "total": total, "message": message})
                results = run_professional_scan(
                    strategy_ids=strategy_ids,
                    use_pattern_filter=data.get("use_pattern_filter", True),
                    use_hot_filter=data.get("use_hot_filter", True),
                    use_risk_budget=True,
                    use_ai_rank=data.get("use_ai_rank", True),
                    capital=float(data.get("capital") or 1000000),
                    risk_pct=float(data.get("risk_pct") or 0.01),
                    stop_loss_pct=float(data.get("stop_loss_pct") or 0.05),
                    top_n=top_n,
                    stock_limit=stock_limit,
                    progress_callback=progress_cb,
                )
                scan_result["results"] = results
                q.put({"type": "done", "results": results, "count": len(results)})
            except Exception as e:
                import traceback
                scan_result["error"] = str(e)
                q.put({"type": "error", "error": str(e), "detail": traceback.format_exc()})

        def generate():
            t = threading.Thread(target=run_scan, daemon=True)
            t.start()
            deadline = time.time() + 300
            while time.time() < deadline:
                try:
                    msg = q.get(timeout=0.5)
                except queue.Empty:
                    yield "data: " + json.dumps({"type": "ping"}) + "\n\n"
                    continue
                if msg.get("type") == "done":
                    yield "data: " + json.dumps(msg) + "\n\n"
                    return
                if msg.get("type") == "error":
                    yield "data: " + json.dumps(msg) + "\n\n"
                    return
                yield "data: " + json.dumps(msg) + "\n\n"
            yield "data: " + json.dumps({"type": "error", "error": "超时"}) + "\n\n"

        return Response(
            stream_with_context(generate()),
            content_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @bp.route("/ai_recommendations", methods=["GET"])
    def ai_recommendations():
        """
        AI 选股推荐：全量筛选，符合条件进候选池；支持自然语言二次筛选。
        Query: top=50, nl_filter=低估值高分红
        """
        _root()
        try:
            import sys
            from concurrent.futures import ThreadPoolExecutor, as_completed
            if _API_ROOT not in sys.path:
                sys.path.insert(0, _API_ROOT)
            top = request.args.get("top", type=int) or 50
            top = min(max(1, top), 200)
            nl_filter = (request.args.get("nl_filter") or request.args.get("description") or "").strip()
            from datetime import datetime, timedelta
            from data.data_loader import load_kline
            symbols = _get_full_symbols()
            end = datetime.now().date()
            start = (end - timedelta(days=250)).strftime("%Y-%m-%d")
            end_str = end.strftime("%Y-%m-%d")

            def _load_one(code):
                c = code.split(".")[0] if "." in code else code
                df = load_kline(c, start, end_str, source="database")
                if df is not None and len(df) >= 60:
                    key = c + ".XSHG" if c.startswith("6") else c + ".XSHE"
                    return (key, df)
                return None

            market_data = {}
            with ThreadPoolExecutor(max_workers=16) as ex:
                for fut in as_completed([ex.submit(_load_one, code) for code in symbols]):
                    r = fut.result()
                    if r:
                        market_data[r[0]] = r[1]

            from ai_models.model_manager import ModelManager
            from ai_models.signal_ranker import rank_signals, top_n_symbols
            manager = ModelManager()
            ai_scores = manager.predict(market_data)
            if ai_scores is None or ai_scores.empty:
                return jsonify({"success": True, "list": [], "candidate_count": 0, "message": "未找到推荐：请先运行 train_ai_model.py 训练模型，并确保数据库有足够历史数据（约250日）"})
            ranked = rank_signals(ai_scores, ai_weight=1.0, strategy_weight=0.0)
            top_list = top_n_symbols(ranked, n=top)
            rows = []
            for i, sym in enumerate(top_list, 1):
                r = ranked[ranked["symbol"] == sym].iloc[0]
                rows.append({"rank": i, "symbol": sym, "score": round(float(r["final_score"]), 4)})
            candidate_count = len(rows)
            if nl_filter:
                name_map = _get_stock_names()
                rows = _apply_nl_filter(rows, nl_filter, name_map)
                for i, r in enumerate(rows, 1):
                    r["rank"] = i
            return jsonify({"success": True, "list": rows, "candidate_count": candidate_count})
        except Exception as e:
            import traceback
            return jsonify({"success": False, "error": str(e), "list": [], "detail": traceback.format_exc()}), 500

    @bp.route("/portfolio_result", methods=["POST"])
    def portfolio_result():
        """
        机构组合结果：全量筛选 → 多策略信号 → 资金分配 → 风控 → 目标仓位。
        支持自然语言二次筛选显示。concentrate=true 时少品种大仓位（适合短期集中交易）。
        Body: { stockCodes?, capital?, nl_filter?, concentrate? }
        """
        _root()
        try:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            data = request.json or {}
            symbols = data.get("stockCodes") or []
            capital = float(data.get("capital") or 1000000)
            nl_filter = (data.get("nl_filter") or data.get("description") or "").strip()
            concentrate = data.get("concentrate") is True
            if not symbols:
                symbols = _get_full_symbols()
            from datetime import datetime, timedelta
            from data.data_loader import load_kline
            end = datetime.now().date()
            start = (end - timedelta(days=250)).strftime("%Y-%m-%d")
            end_str = end.strftime("%Y-%m-%d")

            def _load_one(code):
                c = code.split(".")[0] if "." in code else code
                df = load_kline(c, start, end_str, source="database")
                if df is not None and len(df) >= 60:
                    key = c + ".XSHG" if c.startswith("6") else c + ".XSHE"
                    return (key, df)
                return None

            market_data = {}
            with ThreadPoolExecutor(max_workers=16) as ex:
                for fut in as_completed([ex.submit(_load_one, code) for code in symbols]):
                    r = fut.result()
                    if r:
                        market_data[r[0]] = r[1]

            ai_scores = None
            try:
                from ai_models.model_manager import ModelManager
                mm = ModelManager()
                ai_scores = mm.predict(market_data)
            except Exception:
                pass

            from engine import InstitutionalPortfolioEngine
            max_pos = 10 if concentrate else 30
            max_single = 0.15 if concentrate else 0.10
            engine = InstitutionalPortfolioEngine(capital=capital, max_positions=max_pos, max_single_pct=max_single)
            result = engine.run(market_data, index_df=None, current_max_drawdown=0.0, ai_scores=ai_scores)
            orders = result.get("orders") or []
            target_positions = result.get("target_positions") or {}
            risk_scale = result.get("risk_scale", 1.0)
            candidate_count = len(orders)
            if nl_filter:
                name_map = _get_stock_names()
                orders = _apply_nl_filter(orders, nl_filter, name_map)
            return jsonify({
                "success": True,
                "orders": orders,
                "target_positions": target_positions,
                "risk_scale": risk_scale,
                "count": len(orders),
                "candidate_count": candidate_count,
            })
        except Exception as e:
            import traceback
            return jsonify({"success": False, "error": str(e), "orders": [], "target_positions": {}, "detail": traceback.format_exc()}), 500

    @bp.route("/ai_trading_advice", methods=["POST"])
    def ai_trading_advice():
        """
        AI 交易建议：买卖时点 + 仓位布局。
        输出：标的、方向、建议仓位%、时点提示、止损、止盈。
        Body: { stockCodes?: string[], capital?: number, nl_filter?: string }
        """
        _root()
        try:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            data = request.json or {}
            symbols = data.get("stockCodes") or []
            capital = float(data.get("capital") or 1000000)
            nl_filter = (data.get("nl_filter") or data.get("description") or "").strip()
            concentrate = data.get("concentrate") is True
            if not symbols:
                symbols = _get_full_symbols()
            from datetime import datetime, timedelta
            from data.data_loader import load_kline
            end = datetime.now().date()
            start = (end - timedelta(days=250)).strftime("%Y-%m-%d")
            end_str = end.strftime("%Y-%m-%d")

            def _load_one(code):
                c = code.split(".")[0] if "." in code else code
                df = load_kline(c, start, end_str, source="database")
                if df is None or len(df) < 60:
                    df = load_kline(c, start, end_str, source="akshare")
                if df is not None and len(df) >= 60:
                    key = c + ".XSHG" if c.startswith("6") else c + ".XSHE"
                    return (key, df)
                return None

            market_data = {}
            with ThreadPoolExecutor(max_workers=16) as ex:
                for fut in as_completed([ex.submit(_load_one, code) for code in symbols]):
                    r = fut.result()
                    if r:
                        market_data[r[0]] = r[1]

            ai_scores = None
            try:
                from ai_models.model_manager import ModelManager
                mm = ModelManager()
                ai_scores = mm.predict(market_data)
            except Exception:
                pass

            max_pos = 10 if concentrate else 30
            max_single = 0.15 if concentrate else 0.10
            from engine import InstitutionalPortfolioEngine
            engine = InstitutionalPortfolioEngine(capital=capital, max_positions=max_pos, max_single_pct=max_single)
            result = engine.run(market_data, index_df=None, current_max_drawdown=0.0, ai_scores=ai_scores)
            orders = result.get("orders") or []
            risk_scale = result.get("risk_scale", 1.0)
            capital_eff = capital * risk_scale

            # 构建交易建议：时点、仓位、止损止盈
            advice_list = []
            for o in orders:
                sym = o.get("symbol", "")
                val = float(o.get("value") or 0)
                if not sym or val <= 0:
                    continue
                df = market_data.get(sym)
                close = None
                if df is not None and len(df) > 0:
                    last = df.iloc[-1]
                    close = float(last.get("close", 0) or 0)
                if close is None or close <= 0:
                    close = 0
                score = 0.5
                if ai_scores is not None and not ai_scores.empty and "symbol" in ai_scores.columns:
                    row = ai_scores[ai_scores["symbol"].astype(str) == sym]
                    if len(row) > 0 and "score" in row.columns:
                        score = float(row.iloc[0]["score"])
                pos_pct = val / capital_eff if capital_eff > 0 else 0
                timing = "回调至20日均线附近时分批建仓" if score >= 0.6 else "首次建仓30%，确认后再加仓"
                stop_loss_pct = -0.07
                take_profit_stages = [0.10, 0.20, 0.30]
                advice_list.append({
                    "symbol": sym,
                    "direction": "BUY",
                    "suggested_position_pct": round(pos_pct * 100, 2),
                    "suggested_amount": round(val, 0),
                    "current_price": round(close, 2) if close else None,
                    "timing_hint": timing,
                    "stop_loss_pct": round(stop_loss_pct * 100, 1),
                    "take_profit_stages": take_profit_stages,
                    "reason": f"多策略信号 + AI得分 {round(score, 3)}",
                })

            if nl_filter:
                name_map = _get_stock_names()
                advice_list = _apply_nl_filter(advice_list, nl_filter, name_map)

            return jsonify({
                "success": True,
                "advice": advice_list,
                "risk_scale": risk_scale,
                "capital_eff": round(capital_eff, 0),
                "count": len(advice_list),
            })
        except Exception as e:
            import traceback
            return jsonify({"success": False, "error": str(e), "advice": [], "detail": traceback.format_exc()}), 500

    @bp.route("/evolution/pool", methods=["GET"])
    def evolution_pool():
        """自进化策略池：返回当前池内策略列表（id、metrics、无代码）。"""
        _root()
        try:
            from evolution.strategy_pool import StrategyPool
            import os
            pool_path = os.path.join(_API_ROOT, "data", "evolution", "strategy_pool.json")
            pool = StrategyPool(persist_path=pool_path)
            pool.load()
            items = []
            for p in pool.get_all():
                items.append({
                    "id": p.get("id"),
                    "metrics": p.get("metrics"),
                    "added_at": p.get("added_at"),
                })
            return jsonify({"success": True, "pool": items, "count": len(items)})
        except Exception as e:
            import traceback
            return jsonify({"success": False, "error": str(e), "pool": [], "detail": traceback.format_exc()}), 500

    @bp.route("/evolution/run", methods=["POST"])
    def evolution_run():
        """触发一轮自进化（可选 symbol, rounds, idea）。需 OPENAI_API_KEY 才使用 LLM。"""
        _root()
        try:
            data = request.json or {}
            symbol = (data.get("symbol") or "000001").strip()
            rounds = int(data.get("rounds") or 3)
            idea = data.get("idea") or "双均线金叉死叉策略"
            from evolution.strategy_generator import StrategyGenerator
            from evolution.strategy_runner import StrategyRunner
            from evolution.strategy_evaluator import StrategyEvaluator
            from evolution.evolution_engine import EvolutionEngine
            from evolution.strategy_pool import StrategyPool
            from evolution.data_split import split_train_val_test, ensure_ohlcv
            import os
            from data.data_loader import load_kline
            from datetime import datetime, timedelta
            end = datetime.now().date()
            start = (end - timedelta(days=450)).strftime("%Y-%m-%d")
            end_str = end.strftime("%Y-%m-%d")
            df = load_kline(symbol, start, end_str, source="database")
            if df is None or len(df) < 200:
                df = load_kline(symbol, start, end_str, source="akshare")
            df = ensure_ohlcv(df) if df is not None else None
            if df is None or len(df) < 100:
                return jsonify({"success": False, "error": "数据不足", "best": []}), 400
            train, _, _ = split_train_val_test(df, 0.6, 0.2, 0.2)
            generator = StrategyGenerator()
            runner = StrategyRunner()
            evaluator = StrategyEvaluator()
            engine = EvolutionEngine(generator=generator, runner=runner, evaluator=evaluator)
            best = engine.evolve(idea, train, rounds=rounds)
            pool_path = os.path.join(_API_ROOT, "data", "evolution", "strategy_pool.json")
            os.makedirs(os.path.dirname(pool_path) or ".", exist_ok=True)
            pool = StrategyPool(min_sharpe=0.5, max_drawdown=0.25, persist_path=pool_path)
            pool.load()
            added = []
            for code, m in best[:3]:
                if pool.add(code, m):
                    added.append(m)
            pool._save()
            return jsonify({
                "success": True,
                "best": [{"metrics": m} for _, m in best[:5]],
                "pool_added": len(added),
            })
        except RuntimeError as e:
            if "OPENAI_API_KEY" in str(e):
                return jsonify({"success": False, "error": "请设置 OPENAI_API_KEY 以使用 LLM 生成策略", "best": []}), 400
            raise
        except Exception as e:
            import traceback
            return jsonify({"success": False, "error": str(e), "best": [], "detail": traceback.format_exc()}), 500

    @bp.route("/ai/correction_cycle", methods=["POST"])
    def ai_correction_cycle():
        """
        执行一轮模型修正闭环：用历史 3/4 训练 → 预测后 1/4 → 评估预测与实际 → 记录。
        新数据进来后再次调用即可持续修正模型。
        Body: { days?: 500, source?: "database", train_ratio?: 0.75, label_days?: 5 }
        """
        _root()
        try:
            data = request.json or {}
            days = int(data.get("days") or 500)
            source = (data.get("source") or "database").strip() or "database"
            train_ratio = float(data.get("train_ratio") or 0.75)
            label_days = int(data.get("label_days") or 5)
            from ai_models.correction_loop import run_cycle_with_data_loader
            result = run_cycle_with_data_loader(
                symbols=None,
                days=days,
                train_ratio=train_ratio,
                label_forward_days=label_days,
                source=source,
            )
            if not result.get("ok"):
                return jsonify({"success": False, "error": result.get("error") or result.get("reason", "unknown")}), 400
            return jsonify({
                "success": True,
                "n_train": result.get("n_train"),
                "n_forward": result.get("n_forward"),
                "train_date_range": result.get("train_date_range"),
                "forward_date_range": result.get("forward_date_range"),
                "model_path": result.get("model_path"),
                "metrics": result.get("metrics", {}),
            })
        except Exception as e:
            import traceback
            return jsonify({"success": False, "error": str(e), "detail": traceback.format_exc()}), 500

    # 基金经理再平衡用：自进化策略 + 平台插件策略，统一注册
    _FUND_MGR_PLUGIN_STRATEGIES = [
        ("ma_cross", {"sharpe": 1.0, "max_dd": 0.10}),
        ("rsi", {"sharpe": 0.9, "max_dd": 0.12}),
        ("macd", {"sharpe": 0.85, "max_dd": 0.11}),
        ("breakout", {"sharpe": 0.95, "max_dd": 0.13}),
        ("swing_newhigh", {"sharpe": 0.88, "max_dd": 0.12}),
    ]
    _FUND_MGR_STRATEGY_DESCRIPTIONS = {
        "ma_cross": "MA 均线：短期/长期均线金叉死叉，趋势跟踪",
        "rsi": "RSI：相对强弱指标超买超卖区间择时",
        "macd": "MACD：快慢线金叉死叉与柱状图背离",
        "breakout": "突破：N 日高低点突破，顺势入场",
        "swing_newhigh": "波段新高：新高突破 + 均线趋势 + 放量 + 市场过滤",
    }

    @bp.route("/fund_manager/rebalance", methods=["POST"])
    def fund_manager_rebalance():
        """AI 基金经理再平衡：自进化策略池 + 平台插件策略 → 分配权重 → 回撤控制 → allocation 与 orders。"""
        _root()
        try:
            data = request.json or {}
            capital = float(data.get("capital") or 1000000)
            current_max_drawdown = float(data.get("current_max_drawdown") or 0)
            concentrate = data.get("concentrate") is True
            top_strategies = max(1, min(6, int(data.get("top_strategies") or 3)))
            import os
            from ai_fund_manager import StrategyRegistry, AIAllocator, FundManager
            from evolution.strategy_pool import StrategyPool
            pool_path = os.path.join(_API_ROOT, "data", "evolution", "strategy_pool.json")
            registry = StrategyRegistry()
            seen = set()
            pool = StrategyPool(persist_path=pool_path)
            pool.load()
            for i, p in enumerate(pool.get_all()):
                name = p.get("id") or f"ev_{i}"
                if name not in seen:
                    seen.add(name)
                    registry.register(name, None, metrics=p.get("metrics") or {})
            for name, metrics in _FUND_MGR_PLUGIN_STRATEGIES:
                if name not in seen:
                    seen.add(name)
                    registry.register(name, None, metrics=metrics)
            if not registry.get_all():
                registry.register("ma_cross", None, metrics={"sharpe": 1.0, "max_dd": 0.1})
                registry.register("rsi", None, metrics={"sharpe": 0.8, "max_dd": 0.12})
            manager = FundManager(registry=registry, allocator=AIAllocator(), capital=capital)
            result = manager.rebalance(current_max_drawdown=current_max_drawdown)
            if concentrate and result.get("allocation"):
                alloc = result["allocation"]
                top = sorted(alloc.keys(), key=lambda k: alloc.get(k) or 0, reverse=True)[:top_strategies]
                result["allocation"] = {k: alloc[k] for k in top if k in alloc}
                result["orders"] = [o for o in (result.get("orders") or []) if o.get("strategy") in top]
            desc = dict(_FUND_MGR_STRATEGY_DESCRIPTIONS)
            for k in result.get("allocation") or {}:
                if k not in desc and k.startswith("ev_"):
                    desc[k] = "自进化策略：由系统根据历史数据自动生成并入选策略池"
            result["strategy_descriptions"] = desc
            return jsonify({"success": True, **result})
        except Exception as e:
            import traceback
            return jsonify({"success": False, "error": str(e), "allocation": {}, "orders": [], "detail": traceback.format_exc()}), 500

    _PLUGIN_IDS_FOR_SCAN = [x[0] for x in _FUND_MGR_PLUGIN_STRATEGIES]

    @bp.route("/fund_manager/strategy_stocks", methods=["POST"])
    def fund_manager_strategy_stocks():
        """
        各策略建议股票：按策略扫描市场，返回每策略当前出现信号的标的列表。
        Body: { strategy_ids?, limit_per_strategy?, concentrate? } concentrate 时每策略仅取前 5 只。
        """
        _root()
        try:
            data = request.json or {}
            strategy_ids = data.get("strategy_ids") or []
            concentrate = data.get("concentrate") is True
            default_limit = 5 if concentrate else 15
            limit_per = max(1, min(30, int(data.get("limit_per_strategy") or default_limit)))
            if not strategy_ids:
                return jsonify({"success": True, "strategy_stocks": {}})
            from scanner import scan_market, scan_market_evolution
            import os
            pool_path = os.path.join(_API_ROOT, "data", "evolution", "strategy_pool.json")
            strategy_stocks = {}
            for sid in strategy_ids:
                try:
                    if sid in _PLUGIN_IDS_FOR_SCAN:
                        rows = scan_market(strategy_id=sid, timeframe="D", limit=limit_per)
                    elif sid.startswith("ev_"):
                        rows = scan_market_evolution(ev_id=sid, timeframe="D", limit=limit_per, pool_path=pool_path)
                    else:
                        rows = []
                    strategy_stocks[sid] = [
                        {"symbol": r.get("symbol"), "name": r.get("name"), "signal": r.get("signal"),
                         "price": r.get("price"), "date": r.get("date"), "reason": (r.get("reason") or "")[:80]}
                        for r in (rows or [])
                    ]
                except Exception:
                    strategy_stocks[sid] = []
            return jsonify({"success": True, "strategy_stocks": strategy_stocks})
        except Exception as e:
            import traceback
            return jsonify({"success": False, "error": str(e), "strategy_stocks": {}, "detail": traceback.format_exc()}), 500

    def _format_ai_report_text(data: dict) -> str:
        """将 AI 报告数据格式化为纯文本，供 PDF 和飞书使用。"""
        lines = ["量化交易平台 - AI 报告", "=" * 50, ""]
        portfolio = data.get("portfolio") or {}
        if portfolio.get("orders"):
            lines.append("【机构组合】")
            lines.append(f"风控缩放: {portfolio.get('risk_scale', 1) * 100:.1f}%")
            for o in portfolio.get("orders", [])[:30]:
                lines.append(f"  {o.get('symbol', '')}  {o.get('value', 0):,.0f}  {o.get('side', 'BUY')}")
            lines.append("")
        ai_rec = data.get("ai_recommend") or {}
        if ai_rec.get("list"):
            lines.append("【AI 推荐列表】")
            for r in ai_rec.get("list", [])[:20]:
                lines.append(f"  {r.get('rank', '')}  {r.get('symbol', '')}  得分 {r.get('score', '')}")
            lines.append("")
        fm = data.get("fund_manager") or {}
        if fm.get("allocation") or fm.get("orders"):
            lines.append("【基金经理再平衡】")
            lines.append(f"风控缩放: {(fm.get('risk_scale') or 1) * 100:.1f}%")
            for k, v in (fm.get("allocation") or {}).items():
                lines.append(f"  {k}: {v:,.0f}" if isinstance(v, (int, float)) else f"  {k}: {v}")
            for o in fm.get("orders", [])[:15]:
                lines.append(f"  策略 {o.get('strategy', '')}  目标 {o.get('target_value', 0):,.0f}  {o.get('side', '')}")
            lines.append("")
        advice = data.get("trading_advice") or {}
        if advice.get("advice"):
            lines.append("【AI 交易建议】")
            for a in advice.get("advice", [])[:15]:
                lines.append(f"  {a.get('symbol', '')} BUY  仓位{a.get('suggested_position_pct', 0)}%  金额{a.get('suggested_amount', 0):,.0f}")
                lines.append(f"    时点: {a.get('timing_hint', '')}")
                lines.append(f"    止损 {a.get('stop_loss_pct', -7)}%  止盈 10%/20%/30%")
            lines.append("")
        lines.append("=" * 50)
        lines.append("以上仅供参考，不构成投资建议。")
        return "\n".join(lines)

    @bp.route("/export_pdf", methods=["POST"])
    def export_pdf():
        """
        导出 AI 报告为 PDF。
        Body: { data?: { portfolio?, ai_recommend?, fund_manager?, trading_advice? } }
        若 data 为空，返回错误提示先加载数据。
        """
        _root()
        try:
            data = request.json or {}
            report = data.get("data") or {}
            text = _format_ai_report_text(report)
            if not any([
                (report.get("portfolio") or {}).get("orders"),
                (report.get("ai_recommend") or {}).get("list"),
                (report.get("fund_manager") or {}).get("allocation") or (report.get("fund_manager") or {}).get("orders"),
                (report.get("trading_advice") or {}).get("advice"),
            ]):
                return jsonify({"success": False, "error": "请先在 AI 推荐页加载机构组合、AI 推荐、基金经理再平衡或交易建议，再导出 PDF"}), 400
            try:
                from reportlab.lib.pagesizes import A4
                from reportlab.pdfgen import canvas
                from reportlab.pdfbase import pdfmetrics
                from reportlab.pdfbase.cidfonts import UnicodeCIDFont
            except ImportError:
                return jsonify({"success": False, "error": "请安装 reportlab: pip install reportlab"}), 500
            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=A4)
            w, h = A4
            y = h - 40
            try:
                pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
                c.setFont("STSong-Light", 12)
            except Exception:
                c.setFont("Helvetica", 12)
            for line in text.splitlines():
                if y < 50:
                    c.showPage()
                    try:
                        c.setFont("STSong-Light", 12)
                    except Exception:
                        c.setFont("Helvetica", 12)
                    y = h - 40
                try:
                    c.drawString(50, y, line[:80])
                except Exception:
                    c.drawString(50, y, line[:80].encode("utf-8", "ignore").decode("utf-8", "ignore"))
                y -= 16
            c.save()
            buf.seek(0)
            from datetime import datetime
            fname = f"ai_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=fname)
        except Exception as e:
            import traceback
            return jsonify({"success": False, "error": str(e), "detail": traceback.format_exc()}), 500

    @bp.route("/send_feishu", methods=["POST"])
    def send_feishu():
        """
        通过飞书机器人发送 AI 报告到指定群/客户。
        Body: { webhook_url?: string, at_user_id?: string, data?: { portfolio?, ai_recommend?, fund_manager?, trading_advice? } }
        webhook_url 可来自环境变量 FEISHU_WEBHOOK_URL；at_user_id 用于 @指定用户。
        """
        _root()
        try:
            data = request.json or {}
            webhook_url = (data.get("webhook_url") or "").strip() or os.environ.get("FEISHU_WEBHOOK_URL", "").strip()
            if not webhook_url:
                return jsonify({"success": False, "error": "请提供 webhook_url 或设置环境变量 FEISHU_WEBHOOK_URL。在飞书群中添加自定义机器人可获取 webhook 地址。"}), 400
            at_user_id = (data.get("at_user_id") or "").strip()
            report = data.get("data") or {}
            text = _format_ai_report_text(report)
            if at_user_id:
                text += f'\n<at user_id="{at_user_id}"></at>'
            import requests
            payload = {"msg_type": "text", "content": {"text": text}}
            resp = requests.post(webhook_url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
            if resp.status_code != 200:
                return jsonify({"success": False, "error": f"飞书接口返回 {resp.status_code}: {resp.text[:200]}"}), 500
            return jsonify({"success": True, "message": "已发送到飞书"})
        except Exception as e:
            import traceback
            return jsonify({"success": False, "error": str(e), "detail": traceback.format_exc()}), 500

    return bp


def register_routes(app):
    """将 API 蓝图注册到 Flask 应用。"""
    bp = create_api_blueprint()
    app.register_blueprint(bp)
