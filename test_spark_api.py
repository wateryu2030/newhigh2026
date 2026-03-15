#!/usr/bin/env python3
"""
测试讯飞Spark API Key
"""

import os
import sys


def test_spark_api_key():
    """测试讯飞Spark API Key"""
    print("=" * 60)
    print("测试讯飞Spark API Key")
    print("=" * 60)

    api_key = os.getenv("BAILIAN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")

    if not api_key:
        print("❌ 未找到API Key")
        return False

    print(f"API Key: {api_key[:10]}...{api_key[-10:]}")
    print(f"Key格式: sk-sp-开头，长度{len(api_key)}字符")

    # 检查Key格式
    if api_key.startswith("sk-sp-"):
        print("✅ Key格式正确（讯飞Spark格式）")

        # 尝试导入讯飞Spark
        try:
            from spark_ai_python import SparkAI

            print("✅ 讯飞Spark SDK可用")

            # 创建客户端测试
            # 注意：讯飞Spark需要app_id和api_secret，不仅仅是api_key
            # 这个格式的key可能是其他服务的

            print("\n⚠ 注意：sk-sp-格式的Key通常是讯飞Spark，但需要app_id和api_secret")
            print("   这个Key可能用于其他服务")

        except ImportError as e:
            print(f"❌ 讯飞Spark导入失败: {e}")

    else:
        print("❌ Key格式不是sk-sp-开头")

    # 测试其他可能性
    print("\n" + "=" * 60)
    print("API Key可能性分析")
    print("=" * 60)

    possibilities = [
        ("讯飞Spark", "需要app_id、api_key、api_secret三要素"),
        ("其他AI服务", "可能是自定义格式的API Key"),
        ("测试Key", "可能是测试环境的Key"),
        ("无效Key", "可能已经过期或无效"),
    ]

    for i, (service, note) in enumerate(possibilities, 1):
        print(f"{i}. {service}: {note}")

    print("\n建议：")
    print("1. 确认这个API Key是用于哪个AI服务的")
    print("2. 如果是讯飞Spark，需要app_id和api_secret")
    print("3. 如果是其他服务，需要对应的SDK和配置")
    print("4. 可以尝试在对应服务的控制台验证Key")

    return True


def check_other_api_keys():
    """检查其他API Keys"""
    print("\n" + "=" * 60)
    print("检查其他可用的API Keys")
    print("=" * 60)

    api_keys = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
        "DOUBAO_API_KEY": os.getenv("DOUBAO_API_KEY"),
    }

    available_keys = []

    for key_name, key_value in api_keys.items():
        if key_value:
            masked = f"{key_value[:8]}...{key_value[-8:]}" if len(key_value) > 16 else "***"
            print(f"✅ {key_name}: {masked}")
            available_keys.append(key_name)
        else:
            print(f"❌ {key_name}: 未配置")

    print(f"\n可用API Keys: {len(available_keys)}个")
    if available_keys:
        print("可以使用的AI服务:", ", ".join(available_keys))

    return available_keys


def main():
    """主函数"""
    print("开始API Key分析...")

    # 测试Spark API Key
    test_spark_api_key()

    # 检查其他API Keys
    available_keys = check_other_api_keys()

    print("\n" + "=" * 60)
    print("建议的下一步")
    print("=" * 60)

    if available_keys:
        print("✅ 发现其他可用的API Keys")
        print("   建议使用以下AI服务之一：")

        recommendations = {
            "OPENAI_API_KEY": "GPT-4/GPT-3.5，功能强大，文档完善",
            "GEMINI_API_KEY": "Gemini Pro，免费额度较高",
            "DEEPSEEK_API_KEY": "DeepSeek，性价比高，中文优化",
            "ANTHROPIC_API_KEY": "Claude，长文本处理优秀",
            "DOUBAO_API_KEY": "豆包/火山引擎，国内服务稳定",
        }

        for key in available_keys:
            if key in recommendations:
                print(f"   • {key}: {recommendations[key]}")

        print("\n   可以选择一个可用的AI服务继续开发")
    else:
        print("❌ 没有可用的API Keys")
        print("   需要：")
        print("   1. 确认sk-sp-开头的Key是哪个服务的")
        print("   2. 获取一个有效的AI服务API Key")
        print("   3. 更新.env文件中的配置")

    return len(available_keys) > 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
