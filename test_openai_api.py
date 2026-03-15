#!/usr/bin/env python3
"""
测试OpenAI API
"""

import os
import sys

def test_openai_api():
    """测试OpenAI API"""
    print("=" * 60)
    print("测试OpenAI API")
    print("=" * 60)
    
    try:
        # 1. 检查API Key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ 未找到OPENAI_API_KEY环境变量")
            return False
        
        print(f"✅ OpenAI API Key已配置: {api_key[:10]}...{api_key[-10:]}")
        
        # 2. 尝试导入openai
        print("\n尝试导入openai模块...")
        try:
            import openai
            print("✅ openai模块可用")
            
            # 配置API Key
            openai.api_key = api_key
            print("✅ API Key配置成功")
            
            # 测试调用（使用较简单的模型，避免费用过高）
            print("\n测试OpenAI API调用...")
            
            # 先测试简单的完成调用
            try:
                response = openai.Completion.create(
                    model="gpt-3.5-turbo-instruct",
                    prompt="请用一句话介绍你自己",
                    max_tokens=50
                )
                
                if response.choices and len(response.choices) > 0:
                    text = response.choices[0].text.strip()
                    print(f"✅ OpenAI API调用成功！")
                    print(f"   响应: {text}")
                    return True
                else:
                    print(f"❌ OpenAI API调用失败: 无响应文本")
                    
            except Exception as e:
                print(f"⚠ 完成调用失败: {e}")
                print("尝试聊天调用...")
                
                # 尝试聊天调用
                try:
                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "user", "content": "请用一句话介绍你自己"}
                        ],
                        max_tokens=50
                    )
                    
                    if response.choices and len(response.choices) > 0:
                        text = response.choices[0].message.content.strip()
                        print(f"✅ OpenAI聊天API调用成功！")
                        print(f"   响应: {text}")
                        return True
                    else:
                        print(f"❌ OpenAI聊天API调用失败: 无响应文本")
                        return False
                        
                except Exception as e2:
                    print(f"❌ 聊天调用也失败: {e2}")
                    return False
                    
        except ImportError:
            print("❌ openai模块未安装")
            print("   使用: pip install openai --break-system-packages")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_deepseek_api():
    """测试DeepSeek API"""
    print("\n" + "=" * 60)
    print("测试DeepSeek API (备用)")
    print("=" * 60)
    
    try:
        # 检查API Key
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            print("❌ 未找到DEEPSEEK_API_KEY环境变量")
            return False
        
        print(f"✅ DeepSeek API Key已配置: {api_key[:10]}...{api_key[-10:]}")
        
        # DeepSeek通常也使用openai兼容的SDK
        print("\n尝试使用openai SDK调用DeepSeek...")
        try:
            import openai
            openai.api_key = api_key
            openai.base_url = "https://api.deepseek.com"  # DeepSeek的API地址
            
            response = openai.ChatCompletion.create(
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
            print(f"❌ DeepSeek调用失败: {e}")
            return False
            
    except Exception as e:
        print(f"❌ DeepSeek测试失败: {e}")
        return False

def main():
    """主函数"""
    print("开始测试可用的AI API...")
    
    # 先测试OpenAI
    print("\n1. 测试OpenAI API...")
    openai_success = test_openai_api()
    
    # 如果OpenAI失败，测试DeepSeek
    if not openai_success:
        print("\n2. 测试DeepSeek API (备用)...")
        deepseek_success = test_deepseek_api()
    else:
        deepseek_success = False
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    if openai_success:
        print("🎉 OpenAI API测试成功！")
        print("   建议使用OpenAI继续开发")
        print("   模型: gpt-3.5-turbo (性价比高)")
        return "openai"
    elif deepseek_success:
        print("🎉 DeepSeek API测试成功！")
        print("   建议使用DeepSeek继续开发")
        print("   模型: deepseek-chat (国内访问快)")
        return "deepseek"
    else:
        print("❌ 所有AI API测试失败")
        print("   可能原因：")
        print("   1. API Keys无效或已过期")
        print("   2. 网络连接问题（需要科学上网）")
        print("   3. API服务暂时不可用")
        print("\n   备用方案：")
        print("   1. 使用模拟AI数据继续开发")
        print("   2. 检查网络连接")
        print("   3. 验证API Keys有效性")
        return None

if __name__ == "__main__":
    result = main()
    
    if result:
        print(f"\n✅ 推荐使用的AI服务: {result}")
    else:
        print("\n❌ 没有可用的AI服务")
    
    sys.exit(0 if result else 1)