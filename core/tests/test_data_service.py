"""
core.data_service 模块单元测试
"""

import os
import tempfile
import unittest

# pylint: disable=consider-using-with  # NamedTemporaryFile with delete=False is intentional for DB tests



class TestBaseService(unittest.TestCase):
    """测试 BaseService 基类"""

    def setUp(self):
        """准备测试环境"""
        # 创建临时数据库
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.duckdb', delete=False)
        self.temp_db.close()
        os.environ['QUANT_DB_PATH'] = self.temp_db.name

        from core.data_service.base import BaseService
        self.service = BaseService()

    def tearDown(self):
        """清理测试环境"""
        self.service.close()
        os.unlink(self.temp_db.name)
        if original := os.environ.get('QUANT_DB_PATH'):
            os.environ['QUANT_DB_PATH'] = original

    def test_connection_property(self):
        """测试连接属性"""
        conn = self.service.connection
        self.assertIsNotNone(conn)

    def test_close(self):
        """测试关闭连接"""
        self.service.close()
        self.assertIsNone(self.service._connection)

    def test_context_manager(self):
        """测试上下文管理器"""
        with self.service as s:
            self.assertIsNotNone(s.connection)
        self.assertIsNone(self.service._connection)


class TestStockService(unittest.TestCase):
    """测试 StockService"""

    def setUp(self):
        """准备测试环境"""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.duckdb', delete=False)
        self.temp_db.close()
        os.environ['QUANT_DB_PATH'] = self.temp_db.name

        from core.data_service.stock_service import StockService
        self.service = StockService()

        # 插入测试数据
        self.service.execute("""
            INSERT INTO a_stock_basic (code, name, sector, industry)
            VALUES ('000001', '平安银行', '金融', '银行')
        """)

    def tearDown(self):
        """清理测试环境"""
        self.service.close()
        os.unlink(self.temp_db.name)
        if original := os.environ.get('QUANT_DB_PATH'):
            os.environ['QUANT_DB_PATH'] = original

    def test_get_all_stocks(self):
        """测试获取所有股票"""
        stocks = self.service.get_all_stocks()
        self.assertIsInstance(stocks, list)
        self.assertGreater(len(stocks), 0)

    def test_get_stock_by_code(self):
        """测试根据代码获取股票"""
        stock = self.service.get_stock_by_code('000001')
        self.assertIsNotNone(stock)
        self.assertEqual(stock['code'], '000001')
        self.assertEqual(stock['name'], '平安银行')

    def test_get_stock_not_found(self):
        """测试股票不存在"""
        stock = self.service.get_stock_by_code('999999')
        self.assertIsNone(stock)

    def test_get_stock_count(self):
        """测试获取股票总数"""
        count = self.service.get_stock_count()
        self.assertGreater(count, 0)

    def test_update_stocks(self):
        """测试批量更新股票"""
        stocks = [
            {'code': '000002', 'name': '万科 A', 'sector': '房地产', 'industry': '地产开发'},
            {'code': '000003', 'name': '测试股票', 'sector': '科技', 'industry': '软件'},
        ]
        count = self.service.update_stocks(stocks)
        self.assertEqual(count, 2)


class TestNewsService(unittest.TestCase):
    """测试 NewsService"""

    def setUp(self):
        """准备测试环境"""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.duckdb', delete=False)
        self.temp_db.close()
        os.environ['QUANT_DB_PATH'] = self.temp_db.name

        from core.data_service.news_service import NewsService
        self.service = NewsService()

        # 插入测试数据
        self.service.execute("""
            INSERT INTO news_items (title, content, source_site, sentiment_score, sentiment_label)
            VALUES ('测试新闻', '测试内容', 'test', 0.5, 'neutral')
        """)

    def tearDown(self):
        """清理测试环境"""
        self.service.close()
        os.unlink(self.temp_db.name)
        if original := os.environ.get('QUANT_DB_PATH'):
            os.environ['QUANT_DB_PATH'] = original

    def test_get_latest_news(self):
        """测试获取最新新闻"""
        news = self.service.get_latest_news(limit=10)
        self.assertIsInstance(news, list)
        self.assertGreater(len(news), 0)

    def test_get_news_count(self):
        """测试获取新闻总数"""
        count = self.service.get_news_count()
        self.assertGreater(count, 0)

    def test_get_news_sentiment_stats(self):
        """测试获取情感统计"""
        stats = self.service.get_news_sentiment_stats()
        self.assertIn('total', stats)
        self.assertIn('avg_sentiment', stats)
        self.assertIn('positive', stats)
        self.assertIn('negative', stats)


class TestSignalService(unittest.TestCase):
    """测试 SignalService"""

    def setUp(self):
        """准备测试环境"""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.duckdb', delete=False)
        self.temp_db.close()
        os.environ['QUANT_DB_PATH'] = self.temp_db.name

        from core.data_service.signal_service import SignalService
        self.service = SignalService()

        # 插入测试数据
        self.service.execute("""
            INSERT INTO trade_signals (code, signal_type, signal_score, confidence)
            VALUES ('000001', 'buy', 0.8, 0.9)
        """)

    def tearDown(self):
        """清理测试环境"""
        self.service.close()
        os.unlink(self.temp_db.name)
        if original := os.environ.get('QUANT_DB_PATH'):
            os.environ['QUANT_DB_PATH'] = original

    def test_get_trade_signals(self):
        """测试获取交易信号"""
        signals = self.service.get_trade_signals(limit=10)
        self.assertIsInstance(signals, list)
        self.assertGreater(len(signals), 0)

    def test_get_signal_count(self):
        """测试获取信号总数"""
        count = self.service.get_signal_count()
        self.assertGreater(count, 0)

    def test_insert_trade_signal(self):
        """测试插入交易信号"""
        result = self.service.insert_trade_signal('000002', 'sell', 0.7, 0.8)
        self.assertTrue(result)


class TestEmotionService(unittest.TestCase):
    """测试 EmotionService"""

    def setUp(self):
        """准备测试环境"""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.duckdb', delete=False)
        self.temp_db.close()
        os.environ['QUANT_DB_PATH'] = self.temp_db.name

        from core.data_service.emotion_service import EmotionService
        self.service = EmotionService()

        # 插入测试数据
        self.service.execute("""
            INSERT INTO market_emotion (trade_date, emotion_state, limitup_count, max_height, market_volume)
            VALUES ('2026-03-19', '退潮', 50, 5, 1000000.0)
        """)

    def tearDown(self):
        """清理测试环境"""
        self.service.close()
        os.unlink(self.temp_db.name)
        if original := os.environ.get('QUANT_DB_PATH'):
            os.environ['QUANT_DB_PATH'] = original

    def test_get_latest_emotion(self):
        """测试获取最新情绪"""
        emotion = self.service.get_latest_emotion()
        self.assertIsNotNone(emotion)
        self.assertEqual(emotion['emotion_state'], '退潮')

    def test_get_emotion_history(self):
        """测试获取历史情绪"""
        history = self.service.get_emotion_history(days=30)
        self.assertIsInstance(history, list)
        self.assertGreater(len(history), 0)

    def test_state_to_score(self):
        """测试状态转分数"""
        self.assertEqual(self.service.state_to_score('冰点'), 0.2)
        self.assertEqual(self.service.state_to_score('启动'), 0.4)
        self.assertEqual(self.service.state_to_score('主升'), 0.7)
        self.assertEqual(self.service.state_to_score('高潮'), 0.85)
        self.assertEqual(self.service.state_to_score('退潮'), 0.35)
        self.assertEqual(self.service.state_to_score('未知'), 0.5)


if __name__ == '__main__':
    unittest.main()
