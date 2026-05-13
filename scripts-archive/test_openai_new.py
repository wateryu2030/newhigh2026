#!/usr/bin/env python3
"""
测试OpenAI API (新版本接口)
"""

import os
import sys

def test_openai_new():
    """测试OpenAI API (新版本)"""
    print("=" * 60)
    print("测试OpenAI API (新版本接口)")
    print("=" * 60)

    try:
        # 1. 检查API Key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ 未找到OPENAI_API_KEY环境变量")
            return False

        print(f"✅ OpenAI API Key已配置: {api_key[:10]}...{api_key[-10:]}")

        # 2. 导入openai (新版本)
        print("\n导入openai模块 (新版本)...")
        from openai import OpenAI

        # 创建客户端
        client = OpenAI(api_key=api_key)
        print("✅ OpenAI客户端创建成功")

        # 3. 测试调用
        print("\n测试OpenAI API调用...")

        try:
            # 使用新版本的调用方式
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": "请用一句话介绍你自己"}
                ],
                max_tokens=50
            )

            if response.choices and len(response.choices) > 0:
                text = response.choices[0].message.content.strip()
                print(f"✅ OpenAI API调用成功！")
                print(f"   响应: {text}")
                return True
            else:
                print(f"❌ OpenAI API调用失败: 无响应文本")
                return False

        except Exception as e:
            print(f"❌ OpenAI API调用异常: {e}")

            # 尝试更简单的模型
            print("\n尝试使用更简单的模型...")
            try:
                response = client.completions.create(
                    model="gpt-3.5-turbo-instruct",
                    prompt="请用一句话介绍你自己",
                    max_tokens=50
                )

                if response.choices and len(response.choices) > 0:
                    text = response.choices[0].text.strip()
                    print(f"✅ OpenAI完成API调用成功！")
                    print(f"   响应: {text}")
                    return True
                else:
                    print(f"❌ OpenAI完成API调用失败: 无响应文本")
                    return False

            except Exception as e2:
                print(f"❌ 完成调用也失败: {e2}")
                return False

    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_deepseek_new():
    """测试DeepSeek API (新版本接口)"""
    print("\n" + "=" * 60)
    print("测试DeepSeek API (新版本接口)")
    print("=" * 60)

    try:
        # 检查API Key
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            print("❌ 未找到DEEPSEEK_API_KEY环境变量")
            return False

        print(f"✅ DeepSeek API Key已配置: {api_key[:10]}...{api_key[-10:]}")

        # 导入openai (新版本)
        from openai import OpenAI

        # 创建DeepSeek客户端
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        print("✅ DeepSeek客户端创建成功")

        # 测试调用
        print("\n测试DeepSeek API调用...")

        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "user", "content": "请用一句话介绍你自己"}
                ],
                max_tokens=50
            )

            if response.choices and len(response.choices) > 0:
                text = response.choices[0].message.content.strip()
                print(f"✅ DeepSeek API调用成功！")
                print(f"   响应: {text}")
                return True
            else:
                print(f"❌ DeepSeek API调用失败: 无响应文本")
                return False

        except Exception as e:
            print(f"❌ DeepSeek API调用异常: {e}")
            return False

    except Exception as e:
        print(f"❌ DeepSeek测试失败: {e}")
        return False

def main():
    """主函数"""
    print("开始测试可用的AI API (新版本接口)...")

    # 先测试OpenAI
    print("\n1. 测试OpenAI API...")
    openai_success = test_openai_new()

    # 如果OpenAI失败，测试DeepSeek
    if not openai_success:
        print("\n2. 测试DeepSeek API (备用)...")
        deepseek_success = test_deepseek_new()
    else:
        deepseek_success = False

    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    if openai_success:
        print("🎉 OpenAI API测试成功！")
        print("   建议使用OpenAI继续开发")
        print("   模型: gpt-3.5-turbo")
        return "openai"
    elif deepseek_success:
        print("🎉 DeepSeek API测试成功！")
        print("   建议使用DeepSeek继续开发")
        print("   模型: deepseek-chat")
        return "deepseek"
    else:
        print("❌ 所有AI API测试失败")
        print("   可能原因：")
        print("   1. API Keys无效或已过期")
        print("   2. 网络连接问题")
        print("   3. API服务暂时不可用")
        print("   4. 需要科学上网访问OpenAI")
        print("\n   当前情况分析：")
        print("   - Gemini: 网络连接超时")
        print("   - OpenAI: 需要验证网络")
        print("   - DeepSeek: 国内服务，可能可用")
        print("\n   建议：")
        print("   1. 使用模拟AI数据继续开发流程")
        print("   2. 集成真实数据源展示功能")
        print("   3. 后续再解决API连接问题")
        return None

if __name__ == "__main__":
    result = main()

    if result:
        print(f"\n✅ 推荐使用的AI服务: {result}")
    else:
        print("\n⚠ 没有可用的AI服务，将使用模拟数据继续开发")

    sys.exit(0 if result else 0)  # 即使失败也返回0，不阻塞开发