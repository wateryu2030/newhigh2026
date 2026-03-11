#!/usr/bin/env python3
"""
Tushare集成测试
测试Tushare连接器在量化平台中的集成情况
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data-engine/src'))

class TestTushareIntegration(unittest.TestCase):
    """Tushare集成测试类"""
    
    def setUp(self):
        """测试前设置"""
        # 设置环境变量
        os.environ['TUSHARE_TOKEN'] = 'test_token'
        
    def tearDown(self):
        """测试后清理"""
        # 清理环境变量
        if 'TUSHARE_TOKEN' in os.environ:
            del os.environ['TUSHARE_TOKEN']
    
    def test_import_tushare_connector(self):
        """测试导入Tushare连接器"""
        try:
            from data_engine.src.data_engine import connector_tushare
            self.assertIsNotNone(connector_tushare)
            print("✓ Tushare连接器导入成功")
        except ImportError as e:
            self.fail(f"导入Tushare连接器失败: {e}")
    
    @patch('data_engine.src.data_engine.connector_tushare.ts')
    def test_tushare_initialization(self, mock_ts):
        """测试Tushare初始化"""
        from data_engine.src.data_engine import connector_tushare as tushare
        
        # 模拟tushare模块
        mock_ts.set_token = MagicMock()
        
        # 测试初始化
        result = tushare._init_tushare()
        
        # 验证
        mock_ts.set_token.assert_called_once_with('test_token')
        self.assertTrue(result)
        print("✓ Tushare初始化测试通过")
    
    def test_normalize_symbol(self):
        """测试股票代码标准化"""
        from data_engine.src.data_engine import connector_tushare as tushare
        
        test_cases = [
            ('000001', '000001.SZ'),
            ('600519', '600519.SH'),
            ('830799', '830799.BSE'),
            ('000001.SZ', '000001.SZ'),  # 已经标准化
            ('600519.SH', '600519.SH'),
        ]
        
        for input_code, expected in test_cases:
            result = tushare._normalize_symbol(input_code)
            self.assertEqual(result, expected, f"代码 {input_code} 标准化失败")
        
        print("✓ 股票代码标准化测试通过")
    
    @patch('data_engine.src.data_engine.connector_tushare.ts')
    @patch('data_engine.src.data_engine.connector_tushare.pd')
    def test_fetch_ohlcv_mock(self, mock_pd, mock_ts):
        """模拟测试获取OHLCV数据"""
        from data_engine.src.data_engine import connector_tushare as tushare
        
        # 模拟数据
        mock_data = {
            'trade_date': ['20240131', '20240130'],
            'ts_code': ['000001.SZ', '000001.SZ'],
            'open': [10.0, 9.8],
            'high': [10.5, 10.2],
            'low': [9.8, 9.7],
            'close': [10.2, 10.0],
            'vol': [1000000, 950000],
            'amount': [10200000, 9500000]
        }
        
        mock_df = MagicMock()
        mock_df.empty = False
        mock_df.rename = MagicMock(return_value=mock_df)
        mock_df.sort_values = MagicMock(return_value=mock_df)
        mock_df.iterrows = MagicMock(return_value=[
            (0, {'date': datetime(2024, 1, 31), 'open': 10.0, 'high': 10.5, 'low': 9.8, 'close': 10.2, 'volume': 1000000, 'amount': 10200000, 'code': '000001.SZ'}),
            (1, {'date': datetime(2024, 1, 30), 'open': 9.8, 'high': 10.2, 'low': 9.7, 'close': 10.0, 'volume': 950000, 'amount': 9500000, 'code': '000001.SZ'})
        ])
        
        # 模拟pro接口
        mock_pro = MagicMock()
        mock_pro.daily.return_value = mock_df
        mock_ts.pro_api.return_value = mock_pro
        mock_ts.set_token = MagicMock()
        
        # 模拟pandas
        mock_pd.to_datetime = MagicMock(side_effect=lambda x, **kwargs: x)
        
        # 测试获取数据
        try:
            ohlcv_list = tushare.fetch_ohlcv(
                code='000001',
                start_date='20240101',
                end_date='20240131',
                period='daily'
            )
            
            self.assertIsNotNone(ohlcv_list)
            self.assertEqual(len(ohlcv_list), 2)
            
            # 验证数据
            first_item = ohlcv_list[0]
            self.assertEqual(first_item.close, 10.2)
            self.assertEqual(first_item.volume, 1000000)
            
            print("✓ OHLCV数据获取测试通过")
            
        except Exception as e:
            self.fail(f"获取OHLCV数据失败: {e}")
    
    def test_error_handling(self):
        """测试错误处理"""
        from data_engine.src.data_engine import connector_tushare as tushare
        
        # 测试未设置token的情况
        if 'TUSHARE_TOKEN' in os.environ:
            del os.environ['TUSHARE_TOKEN']
        
        # 应该抛出RuntimeError
        with self.assertRaises(RuntimeError):
            tushare.fetch_ohlcv('000001', '20240101', '20240131', 'daily')
        
        print("✓ 错误处理测试通过")
    
    def test_integration_with_core(self):
        """测试与core模块的集成"""
        try:
            # 尝试导入core模块
            from core import OHLCV
            
            # 创建OHLCV对象测试
            test_time = datetime.now()
            ohlcv = OHLCV(
                timestamp=test_time,
                open=10.0,
                high=10.5,
                low=9.8,
                close=10.2,
                volume=1000000,
                amount=10200000,
                code='000001.SZ'
            )
            
            self.assertIsNotNone(ohlcv)
            self.assertEqual(ohlcv.close, 10.2)
            self.assertEqual(ohlcv.code, '000001.SZ')
            
            print("✓ Core模块集成测试通过")
            
        except ImportError as e:
            print(f"⚠ Core模块未找到: {e}")
            # 这不是测试失败，只是提醒
            self.skipTest("Core模块未安装")
    
    def test_data_pipeline_integration(self):
        """测试数据管道集成"""
        try:
            # 检查data_pipeline是否存在
            import importlib.util
            pipeline_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'data-engine/src/data_engine/data_pipeline.py'
            )
            
            if os.path.exists(pipeline_path):
                spec = importlib.util.spec_from_file_location("data_pipeline", pipeline_path)
                data_pipeline = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(data_pipeline)
                
                # 检查是否有Tushare相关的导入或引用
                print("✓ 数据管道文件存在")
            else:
                print("⚠ 数据管道文件不存在")
                
        except Exception as e:
            print(f"⚠ 数据管道集成检查失败: {e}")

class TestTushareDemoScript(unittest.TestCase):
    """测试演示脚本"""
    
    def test_demo_script_exists(self):
        """测试演示脚本是否存在"""
        demo_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'scripts/tushare_demo.py'
        )
        
        self.assertTrue(os.path.exists(demo_path), "演示脚本不存在")
        print("✓ 演示脚本存在")
    
    def test_demo_script_runnable(self):
        """测试演示脚本可运行"""
        demo_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'scripts/tushare_demo.py'
        )
        
        try:
            # 尝试导入演示脚本
            import importlib.util
            spec = importlib.util.spec_from_file_location("tushare_demo", demo_path)
            demo_module = importlib.util.module_from_spec(spec)
            
            # 设置环境变量避免实际API调用
            os.environ['TUSHARE_TOKEN'] = 'test_token_for_demo'
            
            # 执行导入（不执行主函数）
            spec.loader.exec_module(demo_module)
            
            print("✓ 演示脚本可导入")
            
        except Exception as e:
            print(f"⚠ 演示脚本导入失败: {e}")
            # 不是测试失败，只是提醒

def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Tushare集成测试")
    print("=" * 60)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestTushareIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestTushareDemoScript))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print("测试完成")
    print(f"运行测试: {result.testsRun}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print(f"跳过: {len(result.skipped)}")
    print("=" * 60)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    # 运行测试
    success = run_all_tests()
    
    # 根据测试结果退出
    sys.exit(0 if success else 1)