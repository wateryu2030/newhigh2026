#!/usr/bin/env python3
"""
配置工具 - 快速配置微信推送
"""

import os
import json
from pathlib import Path

ROOT = Path(__file__).parent
CONFIG_FILE = ROOT / "config.json"
ENV_FILE = ROOT / ".env"


def input_with_default(prompt, default=None):
    """带默认值的输入"""
    if default:
        user_input = input(f"{prompt} [{default}]: ").strip()
        return user_input if user_input else default
    else:
        return input(f"{prompt}: ").strip()


def configure_serverchan():
    """配置 Server 酱"""
    print("\n" + "="*60)
    print("配置 Server 酱（微信推送）")
    print("="*60)
    print()
    print("获取 SendKey 步骤：")
    print("1. 访问：https://sct.ftqq.com/")
    print("2. 微信扫码登录")
    print("3. 点击 'SendKey' 标签")
    print("4. 复制你的 SendKey（类似 SCTxxxxxxxx）")
    print()

    sendkey = input_with_default("请输入 SendKey", None)

    if not sendkey:
        print("⚠️ 跳过配置")
        return False

    # 保存到.env 文件
    env_line = f"SERVERCHAN_SENDKEY={sendkey}\n"

    # 读取现有.env
    env_content = ""
    if ENV_FILE.exists():
        with open(ENV_FILE, "r") as f:
            env_content = f.read()

        # 如果已有 SERVERCHAN_SENDKEY，替换
        if "SERVERCHAN_SENDKEY=" in env_content:
            lines = env_content.split("\n")
            new_lines = []
            for line in lines:
                if line.startswith("SERVERCHAN_SENDKEY="):
                    new_lines.append(env_line.strip())
                else:
                    new_lines.append(line)
            env_content = "\n".join(new_lines)
        else:
            env_content += env_line
    else:
        env_content = env_line

    # 写入.env
    with open(ENV_FILE, "w") as f:
        f.write(env_content)

    print(f"✅ Server 酱配置已保存到：{ENV_FILE}")
    return True


def configure_email():
    """配置邮件推送"""
    print("\n" + "="*60)
    print("配置邮件推送（可选）")
    print("="*60)
    print()

    use_email = input_with_default("是否配置邮件推送？(y/n)", "n")

    if use_email.lower() != "y":
        print("⚠️ 跳过邮件配置")
        return False

    print()
    print("以 QQ 邮箱为例：")
    print("1. 登录 QQ 邮箱")
    print("2. 设置 → 账户")
    print("3. 开启 POP3/SMTP 服务")
    print("4. 获取授权码")
    print()

    config = {}
    config["SMTP_SERVER"] = input_with_default("SMTP 服务器", "smtp.qq.com")
    config["SMTP_PORT"] = input_with_default("SMTP 端口", "587")
    config["SMTP_USERNAME"] = input_with_default("邮箱账号", "")
    config["SMTP_PASSWORD"] = input_with_default("邮箱授权码", "")
    config["SMTP_FROM"] = input_with_default("发件人邮箱", config["SMTP_USERNAME"])
    config["SMTP_TO"] = input_with_default("收件人邮箱", config["SMTP_USERNAME"])

    # 保存到.env
    env_content = ""
    if ENV_FILE.exists():
        with open(ENV_FILE, "r") as f:
            env_content = f.read()

    for key, value in config.items():
        if value:
            env_content += f"{key}={value}\n"

    with open(ENV_FILE, "w") as f:
        f.write(env_content)

    print(f"✅ 邮件配置已保存到：{ENV_FILE}")
    return True


def configure_stocks():
    """配置股票池"""
    print("\n" + "="*60)
    print("配置固定股票池")
    print("="*60)
    print()

    use_default = input_with_default("是否使用默认股票池（15 只行业龙头）？(y/n)", "y")

    if use_default.lower() == "y":
        print("✅ 使用默认股票池")
        return

    print()
    print("请输入股票代码（格式：600519.XSHG 或 000858.XSHE）")
    print("每行一个，输入空行结束")
    print()

    stocks = []
    while True:
        code = input(f"股票 {len(stocks)+1}: ").strip()
        if not code:
            break
        stocks.append(code)

    if stocks:
        # 保存到 config.json
        config = {}
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)

        config["fixed_stocks"] = stocks
        config["fixed_count"] = len(stocks)

        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)

        print(f"✅ 股票池已保存（{len(stocks)} 只）")


def test_push():
    """测试推送"""
    print("\n" + "="*60)
    print("测试推送")
    print("="*60)
    print()

    test_push = input_with_default("是否测试推送？(y/n)", "y")

    if test_push.lower() != "y":
        return

    # 运行测试
    import subprocess
    result = subprocess.run(
        ["python3", str(ROOT / "src" / "pusher.py")],
        cwd=str(ROOT)
    )

    if result.returncode == 0:
        print("\n✅ 推送测试完成")
    else:
        print("\n❌ 推送测试失败，请检查配置")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("📊 个人量化投资助手 - 配置工具")
    print("="*60)

    # 配置 Server 酱
    configure_serverchan()

    # 配置邮件（可选）
    configure_email()

    # 配置股票池
    configure_stocks()

    # 测试推送
    test_push()

    print("\n" + "="*60)
    print("✅ 配置完成")
    print("="*60)
    print()
    print("下一步：")
    print("1. 运行测试：python3 run_daily.py")
    print("2. 查看定时任务：crontab -l")
    print("3. 查看日志：tail -f logs/daily_run.log")
    print()


if __name__ == "__main__":
    main()
