#!/usr/bin/env python3
"""
重点股票深度分析模块
针对指定股票进行全方位分析：数据 + 新闻 + 研究 + 意见
"""

import os
import sys
import duckdb
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# 添加项目路径
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "data-pipeline/src"))

try:
    from soul_framework import build_industry_opportunity_section
except ImportError:
    build_industry_opportunity_section = None  # type: ignore

try:
    from report_generator import ReportGenerator
except ImportError:
    ReportGenerator = None  # type: ignore

class DeepStockAnalyzer:
    """深度股票分析器"""

    def __init__(self, db_path: str = None):
        # 使用正确的数据库路径
        self.db_path = db_path or "/Users/apple/Ahope/newhigh/data/quant_system.duckdb"
        self.conn = None

    def connect(self):
        """连接数据库"""
        try:
            self.conn = duckdb.connect(self.db_path)
            return True
        except Exception as e:
            print(f"❌ 连接数据库失败：{e}")
            return False

    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def analyze_stock(self, stock_code: str) -> Dict:
        """
        深度分析单只股票

        Args:
            stock_code: 股票代码（如 002701.XSHE）

        Returns:
            深度分析报告
        """
        print(f"\n{'='*60}")
        print(f"深度分析：{stock_code}")
        print(f"{'='*60}")

        if not self.connect():
            return None

        try:
            # 1. 基本信息
            print("\n📋 Step 1: 获取基本信息...")
            basic_info = self._get_basic_info(stock_code)
            if not basic_info:
                print(f"⚠️ 未找到股票 {stock_code}")
                return None

            print(f"  名称：{basic_info['name']}")
            print(f"  行业：{basic_info['industry']}")
            print(f"  市值：{basic_info['market_cap']:,.0f}亿")

            # 2. 价格数据
            print("\n📈 Step 2: 分析价格数据...")
            price_data = self._get_price_data(stock_code)
            technical_analysis = self._analyze_technical(price_data)

            print(f"  最新价：{technical_analysis['current_price']:.2f}元")
            print(f"  5 日涨幅：{technical_analysis['change_5d']:.2f}%")
            print(f"  20 日涨幅：{technical_analysis['change_20d']:.2f}%")
            print(f"  支撑位：{technical_analysis['support']:.2f}元")
            print(f"  压力位：{technical_analysis['resistance']:.2f}元")

            # 3. 成交量分析
            print("\n💰 Step 3: 分析成交量...")
            volume_analysis = self._analyze_volume(price_data)
            print(f"  今日成交量：{volume_analysis['current_volume']:,.0f}手")
            print(f"  量比：{volume_analysis['volume_ratio']:.2f}")
            print(f"  资金流向：{volume_analysis['flow_direction']}")

            # 4. 新闻情绪
            print("\n📰 Step 4: 分析新闻情绪...")
            news_sentiment = self._get_news_sentiment(stock_code)
            print(f"  相关新闻：{news_sentiment['news_count']} 条")
            print(f"  情绪分数：{news_sentiment['sentiment_score']:.2f}")
            print(f"  情绪倾向：{news_sentiment['sentiment_label']}")

            # 5. 热点热度
            print("\n🔥 Step 5: 分析热点热度...")
            hot_analysis = self._get_hot_analysis(stock_code)
            print(f"  热度排名：{hot_analysis['hot_rank']}")
            print(f"  讨论量：{hot_analysis['mention_count']}")

            # 5.5 行业地位与前景（机会发现引擎，docs/soul.md）
            print("\n🎯 Step 5.5: 行业地位与前景（机会发现引擎 / docs/soul.md）...")
            if build_industry_opportunity_section:
                industry_opportunity_section = build_industry_opportunity_section(
                    basic_info.get("name", "未知"),
                    stock_code,
                    basic_info.get("industry", "未知"),
                )
                # 终端只展示标题与首段，避免刷屏；全文写入结果供报告使用
                preview = industry_opportunity_section.split("\n", 5)
                head = "\n".join(preview[:5]) if len(preview) > 5 else industry_opportunity_section[:400]
                print(f"  已生成固定分析框架段落（写入结果 industry_opportunity_section）\n  预览：\n{head}\n  …")
            else:
                industry_opportunity_section = ""
                print("  ⚠️ soul_framework 未加载，跳过固定段落")

            # 6. 综合判断
            print("\n💡 Step 6: 生成投资建议...")
            recommendation = self._generate_recommendation(
                basic_info, technical_analysis, volume_analysis,
                news_sentiment, hot_analysis
            )

            print(f"  评级：{recommendation['rating']} {'⭐' * recommendation['stars']}")
            print(f"  目标价：{recommendation['target_price']:.2f}元")
            print(f"  策略：{recommendation['strategy']}")

            # 7. 风险提示
            print("\n⚠️ Step 7: 风险提示...")
            risks = self._identify_risks(technical_analysis, news_sentiment)
            for i, risk in enumerate(risks, 1):
                print(f"  {i}. {risk}")

            # 合并结果
            result = {
                "code": stock_code,
                "name": basic_info['name'],
                "basic_info": basic_info,
                "technical": technical_analysis,
                "volume": volume_analysis,
                "news": news_sentiment,
                "hot": hot_analysis,
                "recommendation": recommendation,
                "risks": risks,
                "industry_opportunity_section": industry_opportunity_section,
            }

            return result

        finally:
            self.close()

    def _get_basic_info(self, stock_code: str) -> Dict:
        """获取基本信息"""
        query = """
        SELECT order_book_id, name, type
        FROM stocks
        WHERE order_book_id = ?
        """
        result = self.conn.execute(query, [stock_code]).fetchone()

        if not result:
            return {}

        return {
            "code": result[0],
            "name": result[1] or "未知",
            "industry": result[2] or "未知",
            "market_cap": 0  # 暂缺
        }

    def _get_price_data(self, stock_code: str, days: int = 60) -> List:
        """获取价格数据"""
        query = """
        SELECT trade_date, open, high, low, close, volume, total_turnover
        FROM daily_bars
        WHERE order_book_id = ?
        ORDER BY trade_date DESC
        LIMIT ?
        """
        result = self.conn.execute(query, [stock_code, days]).fetchall()
        return result

    def _analyze_technical(self, price_data: List) -> Dict:
        """技术分析"""
        if not price_data:
            return {}

        # 最新数据
        latest = price_data[0]
        current_price = latest[4]  # close

        # 计算涨幅
        if len(price_data) >= 5:
            price_5d_ago = price_data[4][4]
            change_5d = (current_price - price_5d_ago) / price_5d_ago * 100
        else:
            change_5d = 0

        if len(price_data) >= 20:
            price_20d_ago = price_data[19][4]
            change_20d = (current_price - price_20d_ago) / price_20d_ago * 100
        else:
            change_20d = 0

        # 计算支撑位和压力位（简化版）
        recent_highs = [row[2] for row in price_data[:10]]  # high
        recent_lows = [row[3] for row in price_data[:10]]   # low

        resistance = max(recent_highs) if recent_highs else current_price * 1.1
        support = min(recent_lows) if recent_lows else current_price * 0.9

        # 趋势判断
        if change_5d > 5 and change_20d > 10:
            trend = "强势上涨"
        elif change_5d > 0 and change_20d > 0:
            trend = "上涨趋势"
        elif change_5d < -5 and change_20d < -10:
            trend = "弱势下跌"
        else:
            trend = "震荡整理"

        return {
            "current_price": current_price,
            "change_5d": change_5d,
            "change_20d": change_20d,
            "support": support,
            "resistance": resistance,
            "trend": trend,
            "ma5": sum(row[4] for row in price_data[:5]) / min(5, len(price_data)),
            "ma20": sum(row[4] for row in price_data[:20]) / min(20, len(price_data))
        }

    def _analyze_volume(self, price_data: List) -> Dict:
        """成交量分析"""
        if not price_data:
            return {}

        current_volume = price_data[0][4]  # volume

        # 计算平均成交量
        avg_volume_5d = sum(row[4] for row in price_data[:5]) / min(5, len(price_data))
        avg_volume_20d = sum(row[4] for row in price_data[:20]) / min(20, len(price_data))

        # 量比
        volume_ratio = current_volume / avg_volume_5d if avg_volume_5d > 0 else 1

        # 资金流向判断
        current_price = price_data[0][4]
        prev_price = price_data[0][3] if len(price_data) > 0 else current_price

        if current_price > prev_price and volume_ratio > 1.5:
            flow_direction = "大幅流入"
        elif current_price > prev_price:
            flow_direction = "流入"
        elif current_price < prev_price and volume_ratio > 1.5:
            flow_direction = "大幅流出"
        else:
            flow_direction = "流出"

        return {
            "current_volume": current_volume,
            "avg_volume_5d": avg_volume_5d,
            "avg_volume_20d": avg_volume_20d,
            "volume_ratio": volume_ratio,
            "flow_direction": flow_direction
        }

    def _get_news_sentiment(self, stock_code: str) -> Dict:
        """获取新闻情绪（简化版）"""
        # TODO: 接入真实新闻 API
        # 临时返回模拟数据

        import random
        news_count = random.randint(3, 15)
        sentiment_score = random.uniform(-0.5, 0.8)

        if sentiment_score > 0.3:
            sentiment_label = "偏正面"
        elif sentiment_score > -0.3:
            sentiment_label = "中性"
        else:
            sentiment_label = "偏负面"

        return {
            "news_count": news_count,
            "sentiment_score": sentiment_score,
            "sentiment_label": sentiment_label,
            "recent_news": []
        }

    def _get_hot_analysis(self, stock_code: str) -> Dict:
        """热点热度分析（简化版）"""
        # TODO: 接入雪球 API

        import random
        hot_rank = random.randint(10, 500)
        mention_count = random.randint(50, 2000)

        return {
            "hot_rank": hot_rank,
            "mention_count": mention_count,
            "hot_level": "高" if hot_rank < 100 else "中" if hot_rank < 300 else "低"
        }

    def _generate_recommendation(self, basic_info, technical, volume, news, hot) -> Dict:
        """生成投资建议"""
        # 综合评分
        score = 0

        # 技术面（40%）
        if technical.get('change_5d', 0) > 5:
            score += 2
        elif technical.get('change_5d', 0) > 0:
            score += 1
        elif technical.get('change_5d', 0) < -5:
            score -= 2
        elif technical.get('change_5d', 0) < 0:
            score -= 1

        # 成交量（20%）
        if volume.get('volume_ratio', 1) > 2:
            score += 1
        elif volume.get('volume_ratio', 1) < 0.5:
            score -= 1

        # 新闻情绪（20%）
        if news.get('sentiment_score', 0) > 0.3:
            score += 1
        elif news.get('sentiment_score', 0) < -0.3:
            score -= 1

        # 热点热度（20%）
        if hot.get('hot_rank', 500) < 100:
            score += 1

        # 转换为评级
        if score >= 3:
            rating = "买入"
            stars = 5
        elif score >= 1:
            rating = "买入"
            stars = 4
        elif score >= -1:
            rating = "持有"
            stars = 3
        elif score >= -3:
            rating = "持有"
            stars = 2
        else:
            rating = "卖出"
            stars = 2

        # 目标价
        current_price = technical.get('current_price', 0)
        if rating == "买入":
            target_price = current_price * 1.1
        elif rating == "持有":
            target_price = current_price
        else:
            target_price = current_price * 0.9

        # 策略
        if rating == "买入" and stars == 5:
            strategy = "建议积极介入，仓位可提升至 7 成"
        elif rating == "买入":
            strategy = "建议逢低布局，仓位 5 成左右"
        elif rating == "持有":
            strategy = "建议持有观望，不宜追高"
        else:
            strategy = "建议逢高减仓，控制风险"

        return {
            "rating": rating,
            "stars": stars,
            "target_price": target_price,
            "strategy": strategy,
            "score": score
        }

    def _identify_risks(self, technical, news) -> List[str]:
        """识别风险"""
        risks = []

        # 技术风险
        if technical.get('change_5d', 0) > 15:
            risks.append("短期涨幅过大，可能回调")

        if technical.get('change_20d', 0) < -20:
            risks.append("中期趋势走坏，注意风险")

        # 情绪风险
        if news.get('sentiment_score', 0) < -0.5:
            risks.append("新闻情绪偏负面，可能有利空")

        # 通用风险
        risks.append("大盘波动风险")
        risks.append("行业政策变化风险")

        return risks[:3]  # 最多 3 条


def analyze_target_stocks(
    target_stocks: Optional[List[str]] = None,
    *,
    write_industry_md: bool = True,
    industry_md_path: Optional[str] = None,
) -> List[Dict]:
    """
    分析目标股票；可选将「行业地位与前景」深度段落写入独立 Markdown。

    Args:
        target_stocks: 股票代码列表，默认内置三只示例
        write_industry_md: 是否写入 personal_assistant/reports/deep_industry_YYYY-MM-DD.md
        industry_md_path: 指定完整输出路径时覆盖默认文件名
    """
    print("="*60)
    print("重点股票深度分析")
    print("="*60)

    if target_stocks is None:
        target_stocks = [
            "002701.XSHE",  # 奥瑞金
            "300212.XSHE",  # 易华录
            "600881.XSHG",  # 亚泰集团
        ]

    analyzer = DeepStockAnalyzer()

    results: List[Dict] = []
    for stock_code in target_stocks:
        result = analyzer.analyze_stock(stock_code)
        if result:
            results.append(result)

    print(f"\n{'='*60}")
    print(f"分析完成：{len(results)} 只股票")
    print(f"{'='*60}")

    if write_industry_md and ReportGenerator:
        try:
            out = ReportGenerator.write_deep_industry_markdown(
                results,
                output_path=industry_md_path,
            )
            print(f"\n📄 深度段落（机会发现引擎）已写入：{out}")
        except Exception as e:
            print(f"\n⚠️ 写入深度 Markdown 失败：{e}")

    return results


if __name__ == "__main__":
    analyze_target_stocks()
