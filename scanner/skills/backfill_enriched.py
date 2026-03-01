# -*- coding: utf-8 -*-
"""
Skill 8: Backfill Enriched
为候选股补充更详细的量化因子数据（如 RSI、换手率、主力资金流、均线状态等）
"""
from __future__ import annotations
import os
import sys
from typing import Any, Dict, List
from datetime import datetime, timedelta

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)


def _calculate_rsi(prices: List[float], period: int = 14) -> float:
    """计算RSI"""
    if len(prices) < period + 1:
        return 50.0
    
    gains = []
    losses = []
    
    for i in range(1, period + 1):
        change = prices[-i] - prices[-i-1]
        if change > 0:
            gains.append(change)
        else:
            losses.append(abs(change))
    
    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)


def _calculate_ma_status(prices: List[float]) -> Dict[str, Any]:
    """计算均线状态"""
    if len(prices) < 60:
        return {"ma20": 0, "ma60": 0, "trend": "unknown"}
    
    ma5 = sum(prices[-5:]) / 5
    ma10 = sum(prices[-10:]) / 10
    ma20 = sum(prices[-20:]) / 20
    ma60 = sum(prices[-60:]) / 60
    
    current = prices[-1]
    
    trend = "bullish" if ma5 > ma20 > ma60 else "bearish" if ma5 < ma20 < ma60 else "neutral"
    
    return {
        "ma5": round(ma5, 2),
        "ma10": round(ma10, 2),
        "ma20": round(ma20, 2),
        "ma60": round(ma60, 2),
        "price_vs_ma20": round((current - ma20) / ma20 * 100, 2),
        "price_vs_ma60": round((current - ma60) / ma60 * 100, 2),
        "trend": trend,
        "golden_cross": ma5 > ma20 and prices[-2] < ma20,  # 金叉信号
    }


def _load_stock_names_fast() -> Dict[str, str]:
    """快速加载股票名称映射（优先使用本地缓存）"""
    import sys
    import os
    
    # 尝试从多个来源加载
    name_map = {}
    
    # 1. 尝试从 web_platform 的 override 加载
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        csv_paths = [
            os.path.join(project_root, "data", "tech_leader_stocks.csv"),
            os.path.join(project_root, "data", "consume_leader_stocks.csv"),
        ]
        for csv_path in csv_paths:
            if os.path.exists(csv_path):
                import csv
                with open(csv_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        symbol = row.get("symbol", "").strip()
                        name = row.get("name", "").strip()
                        if symbol and name:
                            name_map[symbol] = name
    except Exception:
        pass
    
    # 2. 内置常见股票名称映射（解决常用股票）
    builtin_names = {
        # 人工智能
        "002230": "科大讯飞", "000938": "中国软件", "000977": "浪潮信息",
        "300496": "中科曙光", "002236": "大华股份", "002594": "比亚迪",
        # 半导体
        "603501": "韦尔股份", "002371": "北方华创", "300661": "圣邦股份",
        "600584": "长电科技", "603933": "睿能科技",
        # 机器人
        "002896": "中大力德", "300024": "机器人", "002527": "新时达",
        "002559": "亚威股份", "300124": "汇川技术",
        # 新能源
        "300750": "宁德时代", "601012": "隆基绿能", "600438": "通威股份",
        "300274": "阳光电源", "002459": "晶澳科技", "600732": "爱旭股份",
        # 华为概念
        "300339": "润和软件", "300598": "诚迈科技", "002512": "达华智能",
        "300418": "昆仑万维", "300031": "宝通科技",
        # 自动驾驶
        "002151": "北斗星通", "002405": "四维图新",
        # 生物医药
        "600276": "恒瑞医药", "000538": "云南白药", "300003": "乐普医疗",
        "300122": "智飞生物", "002007": "华兰生物",
        # 数字经济
        "300229": "拓尔思", "300212": "易华录", "600756": "浪潮软件",
        # 其他
        "600745": "闻泰科技", "600519": "贵州茅台", "300014": "亿纬锂能",
        "002460": "赣锋锂业", "002709": "天赐材料", "002624": "完美世界",
        "300459": "汤姆猫", "002121": "科陆电子",
    }
    name_map.update(builtin_names)
    
    # 3. 如果数量太少，尝试从 AKShare 补全（限制数量避免太慢）
    if len(name_map) < 50:
        try:
            from data.stock_pool import get_a_share_list
            # 使用超时机制
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("AKShare timeout")
            
            # 设置5秒超时
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(5)
            
            try:
                stock_list = get_a_share_list()
                for s in stock_list:
                    symbol = s.get("symbol", "")
                    name = s.get("name", "")
                    if symbol and name and symbol not in name_map:
                        name_map[symbol] = name
            except TimeoutError:
                pass
            finally:
                signal.alarm(0)
        except Exception:
            pass
    
    return name_map


def execute(ctx) -> Any:
    """
    补充量化因子数据
    
    :param ctx: SkillContext
    :return: 更新后的ctx
    """
    from data.data_loader import load_kline
    
    theme_stock_map = ctx.theme_stock_map
    
    if not theme_stock_map:
        ctx.enriched_data = {}
        return ctx
    
    # 加载股票名称映射（使用快速版本）
    name_map = _load_stock_names_fast()
    
    enriched_data = {}
    
    end = datetime.now().date()
    start = (end - timedelta(days=120)).strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")
    
    for theme, stocks in theme_stock_map.items():
        theme_enriched = []
        
        for symbol in stocks:
            try:
                df = load_kline(symbol, start, end_str, source="database")
                if df is None or len(df) < 60:
                    continue
                
                closes = df["close"].tolist() if "close" in df.columns else []
                if not closes:
                    continue
                
                # 计算因子
                rsi = _calculate_rsi(closes)
                ma_status = _calculate_ma_status(closes)
                
                # 涨跌幅
                price_change_5d = (closes[-1] - closes[-5]) / closes[-5] * 100 if len(closes) >= 5 else 0
                price_change_20d = (closes[-1] - closes[-20]) / closes[-20] * 100 if len(closes) >= 20 else 0
                
                # 波动率
                volatility = sum(abs(closes[i] - closes[i-1]) / closes[i-1] 
                                 for i in range(1, min(20, len(closes)))) / min(19, len(closes)-1) * 100
                
                # 获取股票名称
                stock_name = name_map.get(symbol, symbol)
                
                theme_enriched.append({
                    "symbol": symbol,
                    "name": stock_name,
                    "current_price": round(closes[-1], 2),
                    "rsi": rsi,
                    **ma_status,
                    "price_change_5d": round(price_change_5d, 2),
                    "price_change_20d": round(price_change_20d, 2),
                    "volatility": round(volatility, 2),
                })
                
            except Exception as e:
                print(f"[BackfillEnriched] 处理 {symbol} 失败: {e}")
                continue
        
        enriched_data[theme] = theme_enriched
    
    ctx.enriched_data = enriched_data
    
    return ctx
