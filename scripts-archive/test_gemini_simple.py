#!/usr/bin/env python3
"""
简单的Gemini API测试
"""

import os
import sys

def test_gemini_simple():
    """简单测试Gemini API"""
    print("=" * 60)
    print("简单Gemini API测试")
    print("=" * 60)

    try:
        # 1. 检查API Key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ 未找到GEMINI_API_KEY环境变量")
            return False

        print(f"✅ API Key已配置: {api_key[:10]}...{api_key[-10:]}")

        # 2. 尝试导入新版本的google.genai
        print("\n尝试导入google.genai (新版本)...")
        try:
            import google.genai as genai
            print("✅ google.genai模块可用 (新版本)")
            genai.configure(api_key=api_key)
            print("✅ API Key配置成功")

            # 测试调用
            print("\n测试Gemini API调用...")
            model = genai.GenerativeModel('gemini-1.5-pro')
            response = model.generate_content("请用一句话介绍你自己")

            if response.text:
                print(f"✅ Gemini API调用成功！")
                print(f"   响应: {response.text}")
                return True
            else:
                print(f"❌ Gemini API调用失败: 无响应文本")
                return False

        except ImportError:
            print("⚠ google.genai不可用，尝试旧版本...")

            # 3. 尝试导入旧版本的google.generativeai
            try:
                import google.generativeai as genai_old
                print("✅ google.generativeai模块可用 (旧版本)")
                genai_old.configure(api_key=api_key)
                print("✅ API Key配置成功")

                # 测试调用
                print("\n测试Gemini API调用 (旧版本)...")
                model = genai_old.GenerativeModel('gemini-pro')
                response = model.generate_content("请用一句话介绍你自己")

                if response.text:
                    print(f"✅ Gemini API调用成功！")
                    print(f"   响应: {response.text}")
                    return True
                else:
                    print(f"❌ Gemini API调用失败: 无响应文本")
                    return False

            except Exception as e:
                print(f"❌ 旧版本调用失败: {e}")
                return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("开始Gemini API简单测试...")

    success = test_gemini_simple()

    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    if success:
        print("🎉 Gemini API测试成功！")
        print("   可以继续集成到daily_stock_analysis模块")
    else:
        print("❌ Gemini API测试失败")
        print("   可能原因：")
        print("   1. API Key无效或已过期")
        print("   2. 网络连接问题")
        print("   3. Gemini服务暂时不可用")
        print("   4. 需要更新SDK版本")

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)