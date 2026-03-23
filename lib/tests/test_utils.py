"""
lib.utils 模块单元测试
"""

import unittest
from lib.utils import parse_symbol, is_ashare_symbol, normalize_code, format_number


class TestParseSymbol(unittest.TestCase):
    """测试 parse_symbol 函数"""
    
    def test_with_sh_exchange(self):
        code, exchange = parse_symbol('600000.SH')
        self.assertEqual(code, '600000')
        self.assertEqual(exchange, 'SH')
    
    def test_with_sz_exchange(self):
        code, exchange = parse_symbol('000001.SZ')
        self.assertEqual(code, '000001')
        self.assertEqual(exchange, 'SZ')
    
    def test_without_exchange_sh(self):
        code, exchange = parse_symbol('600000')
        self.assertEqual(code, '600000')
        self.assertEqual(exchange, 'SH')
    
    def test_without_exchange_sz(self):
        code, exchange = parse_symbol('000001')
        self.assertEqual(code, '000001')
        self.assertEqual(exchange, 'SZ')
    
    def test_without_exchange_300(self):
        code, exchange = parse_symbol('300001')
        self.assertEqual(code, '300001')
        self.assertEqual(exchange, 'SZ')


class TestIsAshareSymbol(unittest.TestCase):
    """测试 is_ashare_symbol 函数"""
    
    def test_valid_sh(self):
        self.assertTrue(is_ashare_symbol('600000'))
    
    def test_valid_sz(self):
        self.assertTrue(is_ashare_symbol('000001'))
    
    def test_valid_300(self):
        self.assertTrue(is_ashare_symbol('300001'))
    
    def test_invalid(self):
        self.assertFalse(is_ashare_symbol('invalid'))
        self.assertFalse(is_ashare_symbol('123'))


class TestNormalizeCode(unittest.TestCase):
    """测试 normalize_code 函数"""
    
    def test_pad_zeros(self):
        self.assertEqual(normalize_code('1'), '000001')
        self.assertEqual(normalize_code('12'), '000012')
    
    def test_already_normalized(self):
        self.assertEqual(normalize_code('000001'), '000001')
    
    def test_remove_exchange(self):
        self.assertEqual(normalize_code('000001.SZ'), '000001')
        self.assertEqual(normalize_code('600000.SH'), '600000')


class TestFormatNumber(unittest.TestCase):
    """测试 format_number 函数"""
    
    def test_normal_number(self):
        result = format_number(1234.56)
        self.assertIn('1,234.56', result)
    
    def test_ten_thousands(self):
        result = format_number(12345.67)
        self.assertIn('万', result)
    
    def test_hundred_millions(self):
        result = format_number(123456789.01)
        self.assertIn('亿', result)
    
    def test_none(self):
        self.assertEqual(format_number(None), 'N/A')


if __name__ == '__main__':
    unittest.main()
