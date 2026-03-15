#!/usr/bin/env python3
"""
快速检查DeepSeek API当前状态
"""

import os
import sys
from datetime import datetime

def check_deepseek():
    """检查DeepSeek API状态"""
    print("=" * 60)
    print(f"DeepSeek API状态检查 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        # 检查API Key
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            print("❌ 未找到DEEPSEEK_API_KEY环境变量")
            return False
        
        print(f"✅ API Key已配置: {api_key[:10]}...{api_key[-10:]}")
        
        # 导入openai
        from openai import OpenAI
        
        # 创建DeepSeek客户端
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        print("✅ DeepSeek客户端创建成功")
        
        # 快速测试调用
        print("\n进行快速API调用测试...")
        start_time = datetime.now()
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "user", "content": "请用一句话告诉我当前时间"}
            ],
            max_tokens=50,
            temperature=0.1
        )
        
        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds()
        
        if response.choices and len(response.choices) > 0:
            text = response.choices[0].message.content.strip()
            print(f"✅ DeepSeek API调用成功！")
            print(f"   响应时间: {response_time:.2f}秒")
            print(f"   响应内容: {text}")
            return True
        else:
            print(f"❌ DeepSeek API调用失败: 无响应文本")
            return False
            
    except Exception as e:
        print(f"❌ DeepSeek API检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_tushare():
    """检查Tushare状态"""
    print("\n" + "=" * 60)
    print("Tushare状态检查")
    print("=" * 60)
    
    try:
        # 检查Token
        token = os.getenv("TUSHARE_TOKEN")
        if not token:
            print("❌ 未找到TUSHARE_TOKEN环境变量")
            return False
        
        print(f"✅ Tushare Token已配置: {token[:10]}...{token[-10:]}")
        
        # 尝试导入tushare
        try:
            import tushare as ts
            print("✅ tushare模块可用")
            
            # 设置token
            ts.set_token(token)
            print("✅ Tushare Token设置成功")
            
            # 创建pro接口（不实际调用，避免网络请求）
            pro = ts.pro_api()
            print("✅ Tushare Pro接口创建成功")
            
            return True
            
        except ImportError:
            print("❌ tushare模块未安装")
            print("   使用: pip install tushare --break-system-packages")
            return False
            
    except Exception as e:
        print(f"❌ Tushare检查失败: {e}")
        return False

def main():
    """主函数"""
    print("开始检查项目当前状态...")
    
    # 检查DeepSeek
    deepseek_ok = check_deepseek()
    
    # 检查Tushare
    tushare_ok = check_tushare()
    
    print("\n" + "=" * 60)
    print("项目当前状态总结")
    print("=" * 60)
    
    print(f"DeepSeek API: {'✅ 可用' if deepseek_ok else '❌ 不可用'}")
    print(f"Tushare数据源: {'✅ 已配置' if tushare_ok else '❌ 需要安装tushare'}")
    
    print("\n📊 项目准备状态:")
    if deepseek_ok:
        print("   ✅ AI服务: DeepSeek可用，可以继续AI集成")
    else:
        print("   ❌ AI服务: 需要解决DeepSeek连接问题")
    
    if tushare_ok:
        print("   ✅ 数据源: Tushare已配置，可以获取真实股票数据")
    else:
        print("   ⚠ 数据源: 需要安装tushare包")
    
    print("\n🚀 下一步建议:")
    if deepseek_ok and tushare_ok:
        print("   1. 立即集成DeepSeek到ai_decision.py")
        print("   2. 集成Tushare到data_fetcher.py")
        print("   3. 创建完整的演示脚本")
    elif deepseek_ok:
        print("   1. 先集成DeepSeek到ai_decision.py")
        print("   2. 安装tushare: pip install tushare")
        print("   3. 然后集成数据源")
    else:
        print("   1. 解决DeepSeek连接问题")
        print("   2. 安装tushare包")
        print("   3. 使用模拟数据继续开发")
    
    return deepseek_ok and tushare_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)