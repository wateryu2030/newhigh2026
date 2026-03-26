#!/usr/bin/env python3
"""
LSTM 价格预测模型
使用历史 K 线数据预测未来 N 日价格走势

输入：过去 60 日的 OHLCV 数据
输出：未来 5 日的收盘价预测
"""

import os
import sys
import datetime
import numpy as np
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import pandas as pd
    import duckdb
    from sklearn.preprocessing import MinMaxScaler
    from sklearn.metrics import mean_squared_error, mean_absolute_error
    TORCH_AVAILABLE = False  # 默认不使用 PyTorch，使用简单实现
except ImportError as e:
    print(f"警告：依赖库未安装：{e}")
    print("安装命令：pip install pandas duckdb scikit-learn")


@dataclass
class PredictionResult:
    """预测结果"""
    code: str
    current_price: float
    predicted_prices: List[float]
    predicted_dates: List[str]
    confidence: float
    trend: str  # 'up', 'down', 'flat'
    created_at: str


class LSTMPricePredictor:
    """
    LSTM 价格预测模型

    简化版实现（不使用 PyTorch），使用移动平均和趋势外推
    实际生产环境应替换为真正的 LSTM 模型
    """

    def __init__(self, lookback: int = 60, forecast_days: int = 5):
        """
        初始化预测器

        Args:
            lookback: 历史数据天数
            forecast_days: 预测天数
        """
        self.lookback = lookback
        self.forecast_days = forecast_days
        self.scaler = MinMaxScaler()

    def fetch_stock_data(self, code: str, conn=None) -> Optional[pd.DataFrame]:
        """获取股票历史数据"""
        try:
            if conn is None:
                # Use environment variable or default path
                db_path = os.environ.get('QUANT_SYSTEM_DUCKDB_PATH', '')
                if not db_path:
                    # Try multiple possible paths
                    possible_paths = [
                        project_root / "data" / "quant_system.duckdb",
                        Path('/Users/apple/Ahope/newhigh/data/quant_system.duckdb'),
                    ]
                    for p in possible_paths:
                        if p.exists():
                            db_path = str(p)
                            break

                if not db_path or not Path(db_path).exists():
                    print(f"数据库路径错误：{db_path}")
                    return None

                conn = duckdb.connect(db_path)

            query = """
                SELECT date, open, high, low, close, volume
                FROM a_stock_daily
                WHERE code = ?
                ORDER BY date DESC
                LIMIT ?
            """

            df = conn.execute(query, [code, self.lookback]).fetchdf()

            if df.empty:
                return None

            # 按日期升序排列
            df = df.sort_values('date').reset_index(drop=True)
            return df

        except Exception as e:
            print(f"获取数据失败 {code}: {e}")
            return None

    def calculate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标特征"""
        df = df.copy()

        # 移动平均线
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma10'] = df['close'].rolling(window=10).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()

        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2

        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # 波动率
        df['volatility'] = df['close'].pct_change().rolling(window=10).std()

        # 成交量变化
        df['volume_change'] = df['volume'].pct_change()

        return df

    def predict_simple(self, df: pd.DataFrame) -> Tuple[List[float], float]:
        """
        简化版预测（趋势外推）

        返回：(预测价格列表，置信度)
        """
        if len(df) < 20:
            return [], 0.0

        closes = df['close'].values[-20:]  # 取最近 20 天

        # 计算趋势
        recent_trend = (closes[-1] - closes[0]) / closes[0]

        # 计算波动率
        volatility = np.std(np.diff(closes) / closes[:-1])

        # 生成预测
        last_price = closes[-1]
        predicted = []

        for i in range(self.forecast_days):
            # 趋势 + 随机波动
            daily_change = recent_trend / 20  # 日均变化
            noise = np.random.normal(0, volatility * 0.5)
            next_price = last_price * (1 + daily_change + noise)
            predicted.append(float(next_price))
            last_price = next_price

        # 置信度：基于趋势强度和波动率
        trend_strength = abs(recent_trend)
        confidence = min(0.9, trend_strength / (volatility + 0.01))

        return predicted, confidence

    def predict(self, code: str) -> Optional[PredictionResult]:
        """
        预测单只股票

        Returns:
            PredictionResult 或 None
        """
        # 获取数据
        df = self.fetch_stock_data(code)
        if df is None or len(df) < self.lookback:
            return None

        # 计算特征
        df = self.calculate_features(df)

        # 预测
        predicted_prices, confidence = self.predict_simple(df)

        if not predicted_prices:
            return None

        # 生成预测日期
        last_date = pd.to_datetime(df['date'].iloc[-1])
        predicted_dates = [
            (last_date + datetime.timedelta(days=i+1)).strftime('%Y-%m-%d')
            for i in range(self.forecast_days)
        ]

        # 判断趋势
        current_price = float(df['close'].iloc[-1])
        avg_predicted = np.mean(predicted_prices)

        if avg_predicted > current_price * 1.02:
            trend = 'up'
        elif avg_predicted < current_price * 0.98:
            trend = 'down'
        else:
            trend = 'flat'

        return PredictionResult(
            code=code,
            current_price=current_price,
            predicted_prices=predicted_prices,
            predicted_dates=predicted_dates,
            confidence=min(confidence, 0.95),
            trend=trend,
            created_at=datetime.datetime.now().isoformat()
        )

    def predict_batch(self, codes: List[str], limit: int = 50) -> List[PredictionResult]:
        """批量预测"""
        results = []

        # 只预测有足够数据的股票
        for i, code in enumerate(codes[:limit]):
            result = self.predict(code)
            if result:
                results.append(result)

            if (i + 1) % 10 == 0:
                print(f"已预测 {i+1}/{len(codes)} 只股票")

        return results

    def save_to_database(self, results: List[PredictionResult], conn=None):
        """保存预测结果到数据库"""
        if not results:
            return 0

        try:
            if conn is None:
                db_path = project_root / "data" / "quant_system.duckdb"
                conn = duckdb.connect(str(db_path))

            # 创建预测表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS price_predictions (
                    code VARCHAR,
                    current_price DOUBLE,
                    predicted_prices VARCHAR,  -- JSON 数组
                    predicted_dates VARCHAR,   -- JSON 数组
                    confidence DOUBLE,
                    trend VARCHAR,
                    created_at TIMESTAMP,
                    PRIMARY KEY (code, created_at)
                )
            """)

            # 插入数据
            for r in results:
                import json
                conn.execute("""
                    INSERT OR REPLACE INTO price_predictions
                    (code, current_price, predicted_prices, predicted_dates, confidence, trend, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, [
                    r.code,
                    r.current_price,
                    json.dumps(r.predicted_prices),
                    json.dumps(r.predicted_dates),
                    r.confidence,
                    r.trend,
                    r.created_at
                ])

            print(f"保存 {len(results)} 条预测结果到数据库")
            return len(results)

        except Exception as e:
            print(f"保存预测结果失败：{e}")
            return 0


def main():
    """主函数 - 测试预测"""
    import argparse

    parser = argparse.ArgumentParser(description='LSTM 价格预测')
    parser.add_argument('--code', type=str, default='000001', help='股票代码')
    parser.add_argument('--batch', action='store_true', help='批量预测')
    parser.add_argument('--limit', type=int, default=50, help='批量预测数量')

    args = parser.parse_args()

    predictor = LSTMPricePredictor(lookback=60, forecast_days=5)

    if args.batch:
        # 批量预测
        db_path = project_root / "data" / "quant_system.duckdb"
        conn = duckdb.connect(str(db_path))

        codes = conn.execute("SELECT code FROM a_stock_basic LIMIT ?", [args.limit]).fetchall()
        codes = [c[0] for c in codes]

        print(f"批量预测 {len(codes)} 只股票...")
        results = predictor.predict_batch(codes)
        predictor.save_to_database(results, conn)

        # 统计
        up_count = sum(1 for r in results if r.trend == 'up')
        down_count = sum(1 for r in results if r.trend == 'down')
        flat_count = sum(1 for r in results if r.trend == 'flat')

        print(f"\n预测结果统计:")
        print(f"  上涨：{up_count} 只")
        print(f"  下跌：{down_count} 只")
        print(f"  震荡：{flat_count} 只")

        conn.close()
    else:
        # 单只预测
        result = predictor.predict(args.code)

        if result:
            print(f"\n股票：{result.code}")
            print(f"当前价格：{result.current_price:.2f}")
            print(f"预测趋势：{result.trend}")
            print(f"置信度：{result.confidence:.2%}")
            print(f"\n未来 5 日预测:")
            for date, price in zip(result.predicted_dates, result.predicted_prices):
                print(f"  {date}: {price:.2f}")
        else:
            print(f"无法预测股票 {args.code}（数据不足）")


if __name__ == '__main__':
    main()
