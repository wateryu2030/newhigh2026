"""
集成测试

测试整个系统的协同工作能力
"""

import pytest
import unittest

pytestmark = pytest.mark.integration
import os
import tempfile
import time


class TestSystemIntegration(unittest.TestCase):
    """系统集成测试"""

    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        # 使用真实数据库
        cls.original_db = os.environ.get('QUANT_DB_PATH')
        cls.test_db = '/Users/apple/Ahope/newhigh/data/quant_system.duckdb'
        os.environ['QUANT_DB_PATH'] = cls.test_db

    @classmethod
    def tearDownClass(cls):
        """清理测试环境"""
        if cls.original_db:
            os.environ['QUANT_DB_PATH'] = cls.original_db

    def test_lib_database_connection(self):
        """测试 lib 数据库连接"""
        from lib.database import get_connection

        conn = get_connection()
        self.assertIsNotNone(conn)

        result = conn.execute('SELECT 1').fetchone()
        self.assertEqual(result[0], 1)

        conn.close()

    def test_data_service_stock_service(self):
        """测试 StockService 集成"""
        from core.data_service.stock_service import StockService

        with StockService() as service:
            count = service.get_stock_count()
            self.assertGreater(count, 0)

            stocks = service.get_all_stocks()
            self.assertGreater(len(stocks), 0)

    def test_data_service_news_service(self):
        """测试 NewsService 集成"""
        from core.data_service.news_service import NewsService

        with NewsService() as service:
            count = service.get_news_count()
            self.assertGreater(count, 0)

            stats = service.get_news_sentiment_stats()
            self.assertIn('total', stats)

    def test_data_service_signal_service(self):
        """测试 SignalService 集成"""
        from core.data_service.signal_service import SignalService

        with SignalService() as service:
            count = service.get_signal_count()
            self.assertGreaterEqual(count, 0)

    def test_data_service_emotion_service(self):
        """测试 EmotionService 集成"""
        from core.data_service.emotion_service import EmotionService

        with EmotionService() as service:
            emotion = service.get_latest_emotion()
            if emotion:
                self.assertIn('emotion_state', emotion)

            score = service.state_to_score('退潮')
            self.assertEqual(score, 0.35)

    def test_scanner_module_import(self):
        """测试 scanner 模块导入"""
        import sys
        sys.path.insert(0, 'scanner/src')

        from market_scanner import limit_up_scanner
        self.assertTrue(hasattr(limit_up_scanner, 'run_limit_up_scanner'))

    def test_strategy_module_import(self):
        """测试 strategy 模块导入"""
        import sys
        sys.path.insert(0, 'strategy/src')

        from strategy_engine import ai_fusion_strategy
        self.assertTrue(hasattr(ai_fusion_strategy, '_get_emotion_state'))

    def test_ai_module_import(self):
        """测试 ai 模块导入"""
        import sys
        sys.path.insert(0, 'ai/src')

        import ai
        self.assertIn('EmotionCycleModel', ai.__all__)

    def test_data_module_import(self):
        """测试 data 模块导入"""
        import sys
        sys.path.insert(0, 'data/src')

        import data
        self.assertIn('collectors', data.__all__)

    def test_full_workflow(self):
        """测试完整工作流程"""
        # 1. 获取股票数据
        from core.data_service.stock_service import StockService

        with StockService() as stock_service:
            stocks = stock_service.get_all_stocks()
            self.assertGreater(len(stocks), 0)

        # 2. 获取新闻数据
        from core.data_service.news_service import NewsService

        with NewsService() as news_service:
            news = news_service.get_latest_news(limit=5)
            self.assertIsInstance(news, list)

        # 3. 获取情绪状态
        from core.data_service.emotion_service import EmotionService

        with EmotionService() as emotion_service:
            emotion = emotion_service.get_latest_emotion()
            if emotion:
                self.assertIn('emotion_state', emotion)


class TestPerformanceBenchmark(unittest.TestCase):
    """性能基准测试"""

    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        cls.original_db = os.environ.get('QUANT_DB_PATH')
        cls.test_db = '/Users/apple/Ahope/newhigh/data/quant_system.duckdb'
        os.environ['QUANT_DB_PATH'] = cls.test_db

    @classmethod
    def tearDownClass(cls):
        """清理测试环境"""
        if cls.original_db:
            os.environ['QUANT_DB_PATH'] = cls.original_db

    def test_database_connection_speed(self):
        """测试数据库连接速度"""
        from lib.database import get_connection

        start = time.time()
        for _ in range(100):
            conn = get_connection()
            conn.close()
        elapsed = time.time() - start

        avg_time = elapsed / 100 * 1000  # 毫秒
        print(f"\n数据库连接平均耗时：{avg_time:.2f}ms")
        self.assertLess(avg_time, 100)  # 要求 < 100ms

    def test_stock_query_speed(self):
        """测试股票查询速度"""
        from core.data_service.stock_service import StockService

        start = time.time()
        with StockService() as service:
            for _ in range(10):
                service.get_all_stocks()
        elapsed = time.time() - start

        avg_time = elapsed / 10 * 1000  # 毫秒
        print(f"\n股票查询平均耗时：{avg_time:.2f}ms")
        self.assertLess(avg_time, 200)  # 要求 < 200ms

    def test_news_query_speed(self):
        """测试新闻查询速度"""
        from core.data_service.news_service import NewsService

        start = time.time()
        with NewsService() as service:
            for _ in range(10):
                service.get_latest_news(limit=20)
        elapsed = time.time() - start

        avg_time = elapsed / 10 * 1000  # 毫秒
        print(f"\n新闻查询平均耗时：{avg_time:.2f}ms")
        self.assertLess(avg_time, 200)  # 要求 < 200ms

    def test_concurrent_connections(self):
        """测试并发连接"""
        from lib.database import get_connection
        import threading

        results = []

        def connect_and_query():
            try:
                conn = get_connection()
                result = conn.execute('SELECT 1').fetchone()
                results.append(result[0])
                conn.close()
            except Exception as e:
                results.append(None)

        threads = []
        for _ in range(10):
            t = threading.Thread(target=connect_and_query)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        success_count = sum(1 for r in results if r == 1)
        print(f"\n并发连接成功率：{success_count}/10")
        self.assertGreater(success_count, 8)  # 要求 > 80% 成功率


if __name__ == '__main__':
    unittest.main()
