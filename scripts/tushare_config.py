#!/usr/bin/env python3
"""
Tushare配置工具
用于检查和管理Tushare配置
"""

import os
import sys
from pathlib import Path

def check_tushare_config():
    """检查Tushare配置"""
    print("=" * 60)
    print("Tushare配置检查")
    print("=" * 60)
    
    # 检查环境变量
    token = os.getenv('TUSHARE_TOKEN')
    if token:
        print(f"✓ 找到TUSHARE_TOKEN环境变量")
        # 检查token格式（基本验证）
        if len(token) > 10 and token.startswith(('tk', 'sk')):
            print(f"  Token格式看起来正确")
        else:
            print(f"  ⚠ Token格式可能不正确")
    else:
        print(f"✗ 未设置TUSHARE_TOKEN环境变量")
        print(f"  请设置: export TUSHARE_TOKEN='你的token'")
        print(f"  获取token: https://tushare.pro")
    
    # 检查其他配置
    configs = {
        'TUSHARE_REQUEST_INTERVAL': '请求间隔(秒)',
        'TUSHARE_MAX_RETRIES': '最大重试次数',
        'TUSHARE_CACHE_DIR': '缓存目录',
        'TUSHARE_ENABLE_CACHE': '启用缓存',
        'TUSHARE_CACHE_TTL': '缓存过期时间(小时)'
    }
    
    print("\n其他配置:")
    for key, desc in configs.items():
        value = os.getenv(key)
        if value:
            print(f"  {key}: {value} ({desc})")
        else:
            print(f"  {key}: 未设置 ({desc})")
    
    # 检查Python包
    print("\nPython包检查:")
    try:
        import tushare
        print(f"  ✓ tushare版本: {tushare.__version__}")
    except ImportError:
        print(f"  ✗ tushare未安装")
        print(f"    请运行: pip install tushare")
    
    try:
        import pandas
        print(f"  ✓ pandas版本: {pandas.__version__}")
    except ImportError:
        print(f"  ✗ pandas未安装")
        print(f"    请运行: pip install pandas")
    
    return token is not None

def create_env_template():
    """创建.env模板文件"""
    env_template = """# Tushare配置
# 获取Token: https://tushare.pro/user/token
TUSHARE_TOKEN=你的tushare_token

# Tushare API配置
# 请求间隔（秒），避免频率限制
TUSHARE_REQUEST_INTERVAL=1
# 最大重试次数
TUSHARE_MAX_RETRIES=3
# 数据缓存目录
TUSHARE_CACHE_DIR=/tmp/tushare_cache
# 启用数据缓存（true/false）
TUSHARE_ENABLE_CACHE=true
# 缓存过期时间（小时）
TUSHARE_CACHE_TTL=24

# 其他数据源配置
# 默认数据格式
TUSHARE_OUTPUT_FORMAT=csv  # csv, json, excel
# 默认复权类型
TUSHARE_DEFAULT_ADJUST=qfq  # qfq(前复权), hfq(后复权), ''(不复权)
"""
    
    env_path = Path(".env.tushare.example")
    env_path.write_text(env_template, encoding='utf-8')
    print(f"\n✓ 已创建配置文件模板: {env_path}")
    print(f"  请复制为.env并填入你的配置")
    
    return env_path

def test_tushare_connection():
    """测试Tushare连接"""
    print("\n" + "=" * 60)
    print("Tushare连接测试")
    print("=" * 60)
    
    token = os.getenv('TUSHARE_TOKEN')
    if not token:
        print("✗ 无法测试: 未设置TUSHARE_TOKEN")
        return False
    
    try:
        import tushare as ts
        ts.set_token(token)
        
        # 测试pro接口
        pro = ts.pro_api()
        
        # 尝试获取公开数据（不需要特殊权限）
        try:
            # 获取股票列表（基础信息）
            df = pro.stock_basic(
                exchange='', 
                list_status='L', 
                fields='ts_code,symbol,name,industry,list_date'
            )
            
            if not df.empty:
                print(f"✓ 连接成功!")
                print(f"  获取到 {len(df)} 只股票基本信息")
                print(f"  示例股票: {df.iloc[0]['name']} ({df.iloc[0]['ts_code']})")
                return True
            else:
                print("⚠ 连接成功但返回空数据")
                return False
                
        except Exception as e:
            print(f"✗ API调用失败: {e}")
            print("  可能原因:")
            print("  1. Token无效或已过期")
            print("  2. 网络连接问题")
            print("  3. Tushare服务暂时不可用")
            return False
            
    except ImportError:
        print("✗ tushare包未安装")
        return False
    except Exception as e:
        print(f"✗ 连接测试失败: {e}")
        return False

def main():
    """主函数"""
    print("Tushare配置管理工具")
    print("=" * 60)
    
    # 检查当前目录
    current_dir = Path.cwd()
    print(f"当前目录: {current_dir}")
    
    # 检查配置
    has_config = check_tushare_config()
    
    # 创建模板（如果需要）
    if not has_config:
        print("\n" + "=" * 60)
        print("配置缺失，创建模板...")
        create_env_template()
    
    # 测试连接（如果有配置）
    if has_config:
        print("\n" + "=" * 60)
        print("测试Tushare连接...")
        success = test_tushare_connection()
        
        if success:
            print("\n✓ Tushare配置正常，可以开始使用!")
            print("\n使用示例:")
            print("  1. 获取股票日线数据:")
            print("     from data_engine.src.data_engine.connector_tushare import fetch_ohlcv")
            print("     data = fetch_ohlcv('000001', '20240101', '20240131', 'daily')")
            print("")
            print("  2. 运行数据管道:")
            print("     from data_engine.src.data_engine.data_pipeline import run_pipeline_tushare")
            print("     count = run_pipeline_tushare(['000001', '600519'], '20240101', '20240131')")
        else:
            print("\n✗ Tushare配置有问题，请检查!")
    
    print("\n" + "=" * 60)
    print("完成!")
    print("=" * 60)

if __name__ == "__main__":
    main()