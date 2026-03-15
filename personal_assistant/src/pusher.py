#!/usr/bin/env python3
"""
个人量化投资助手 - 消息推送模块
功能：通过微信、邮件、飞书发送报告
"""

import json
import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional
from datetime import datetime

# 从项目根目录加载 .env（在 personal_assistant 下执行时也能读到 newhigh/.env）
def _load_env():
    _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    _env = os.path.join(_root, ".env")
    if not os.path.isfile(_env):
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(_env)
        return
    except ImportError:
        pass
    # 无 dotenv 时简单解析 KEY=VALUE 行并写入 os.environ（去掉行尾 # 注释）
    with open(_env, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip()
                if "#" in v:
                    v = v.split("#")[0].strip()
                if k and v and not os.environ.get(k):
                    os.environ[k] = v.strip('"').strip("'")


_load_env()

# 飞书 API
FEISHU_TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
FEISHU_MESSAGE_URL = "https://open.feishu.cn/open-apis/im/v1/messages"


class WeChatPusher:
    """微信推送器（使用 Server 酱）"""
    
    def __init__(self, send_key: str = None):
        """
        初始化微信推送器
        
        Args:
            send_key: Server 酱的 SendKey
        """
        self.send_key = send_key or os.getenv("SERVERCHAN_SENDKEY")
        self.enabled = bool(self.send_key)
        
        if not self.enabled:
            print("⚠️ 未配置 Server 酱 SendKey，微信推送将不可用")
            print("   配置方法：https://sct.ftqq.com/")
    
    def send(self, title: str, content: str) -> bool:
        """
        发送微信消息
        
        Args:
            title: 消息标题
            content: 消息内容
            
        Returns:
            是否发送成功
        """
        if not self.enabled:
            print("⚠️ 微信推送未启用")
            return False
        
        try:
            url = f"https://sctapi.ftqq.com/{self.send_key}.send"
            data = {
                "title": title,
                "desp": content
            }
            
            response = requests.post(url, data=data, timeout=10)
            result = response.json()
            
            if result.get("code") == 0:
                print("✅ 微信推送成功")
                return True
            else:
                print(f"❌ 微信推送失败：{result.get('message')}")
                return False
                
        except Exception as e:
            print(f"❌ 微信推送异常：{e}")
            return False


class EmailPusher:
    """邮件推送器"""
    
    def __init__(
        self,
        smtp_server: str = None,
        smtp_port: int = None,
        username: str = None,
        password: str = None,
        from_addr: str = None,
        to_addrs: list = None
    ):
        """
        初始化邮件推送器
        
        Args:
            smtp_server: SMTP服务器地址（如 smtp.qq.com）
            smtp_port: SMTP端口（如 587）
            username: 邮箱用户名
            password: 邮箱密码/授权码
            from_addr: 发件人地址
            to_addrs: 收件人地址列表
        """
        self.smtp_server = smtp_server or os.getenv("SMTP_SERVER")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.username = username or os.getenv("SMTP_USERNAME")
        self.password = password or os.getenv("SMTP_PASSWORD")
        self.from_addr = from_addr or os.getenv("SMTP_FROM")
        self.to_addrs = to_addrs or (os.getenv("SMTP_TO") or "").split(",")
        
        self.enabled = all([
            self.smtp_server,
            self.username,
            self.password,
            self.from_addr,
            self.to_addrs
        ])
        
        if not self.enabled:
            print("⚠️ 邮件推送未完整配置，将不可用")
            print("   需要配置：SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM, SMTP_TO")
    
    def send(self, subject: str, html_content: str, text_content: str = None) -> bool:
        """
        发送邮件
        
        Args:
            subject: 邮件主题
            html_content: HTML内容
            text_content: 纯文本内容（备用）
            
        Returns:
            是否发送成功
        """
        if not self.enabled:
            print("⚠️ 邮件推送未启用")
            return False
        
        try:
            # 创建邮件
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_addr
            msg["To"] = ", ".join(self.to_addrs)
            
            # 添加纯文本版本
            if text_content:
                msg.attach(MIMEText(text_content, "plain", "utf-8"))
            
            # 添加HTML版本
            msg.attach(MIMEText(html_content, "html", "utf-8"))
            
            # 发送邮件
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.from_addr, self.to_addrs, msg.as_string())
            
            print("✅ 邮件发送成功")
            return True
            
        except Exception as e:
            print(f"❌ 邮件发送失败：{e}")
            return False


class FeishuPusher:
    """飞书推送器（自建应用 + 群机器人）"""

    def __init__(self, app_id: str = None, app_secret: str = None, chat_id: str = None):
        """
        初始化飞书推送器。
        需在飞书开放平台创建自建应用，并配置 .env: FEISHU_APP_ID, FEISHU_APP_SECRET。
        若要推送到群，将机器人加入群后配置 FEISHU_CHAT_ID（群组 ID，群设置中可查）。
        """
        self.app_id = app_id or os.getenv("FEISHU_APP_ID")
        self.app_secret = app_secret or os.getenv("FEISHU_APP_SECRET")
        self.chat_id = chat_id or os.getenv("FEISHU_CHAT_ID")
        self.enabled = bool(self.app_id and self.app_secret and self.chat_id)

        if not self.app_id or not self.app_secret:
            print("⚠️ 未配置 FEISHU_APP_ID / FEISHU_APP_SECRET，飞书推送将不可用")
        elif not self.chat_id:
            print("⚠️ 未配置 FEISHU_CHAT_ID（群组 ID），飞书推送将不可用")
            print("   将机器人加入目标群后，在群设置中复制群组 ID 填入 .env")

    def _get_tenant_access_token(self) -> Optional[str]:
        """获取飞书 tenant_access_token（2 小时有效）。"""
        try:
            resp = requests.post(
                FEISHU_TOKEN_URL,
                json={"app_id": self.app_id, "app_secret": self.app_secret},
                timeout=10,
            )
            data = resp.json()
            if data.get("code") == 0:
                return data.get("tenant_access_token")
        except Exception as e:
            print(f"❌ 飞书获取 token 异常：{e}")
        return None

    def send(self, title: str, content: str) -> bool:
        """
        发送消息到飞书群。
        title 作为首行，content 为正文（支持换行）。
        """
        if not self.enabled:
            print("⚠️ 飞书推送未启用")
            return False

        token = self._get_tenant_access_token()
        if not token:
            print("❌ 飞书获取 token 失败")
            return False

        _cid = (self.chat_id or "")[-12:] if self.chat_id else ""
        print(f"📤 飞书推送目标群 ID 尾码: ...{_cid}（请确认机器人已加入该群）")

        text = f"{title}\n\n{content}" if title else content
        payload = {
            "receive_id": self.chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}),
        }

        try:
            resp = requests.post(
                FEISHU_MESSAGE_URL,
                params={"receive_id_type": "chat_id"},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=10,
            )
            data = resp.json()
            if data.get("code") == 0:
                print("✅ 飞书推送成功")
                return True
            err_msg = data.get("msg", str(data))
            err_code = data.get("code", "")
            print(f"❌ 飞书推送失败：{err_msg}")
            if "out of the chat" in err_msg.lower():
                print("   → 请在该群 群设置-添加机器人 里添加「自建应用」（与 .env 中 FEISHU_APP_ID 对应的应用）")
            return False
        except Exception as e:
            print(f"❌ 飞书推送异常：{e}")
            return False


class ReportPusher:
    """报告推送器（统一管理微信、邮件、飞书）"""

    def __init__(self):
        """初始化推送器"""
        self.wechat = WeChatPusher()
        self.email = EmailPusher()
        self.feishu = FeishuPusher()

    def push_report(self, wechat_content: str, email_subject: str, email_html: str, email_text: str = None) -> Dict:
        """
        推送报告

        Args:
            wechat_content: 微信/飞书正文内容
            email_subject: 邮件主题（同时用作飞书标题）
            email_html: 邮件HTML内容
            email_text: 邮件纯文本内容

        Returns:
            推送结果字典
        """
        results = {
            "wechat": False,
            "email": False,
            "feishu": False,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        print(f"\n📤 开始推送报告 - {results['timestamp']}")

        if self.wechat.enabled:
            title = email_subject.replace("📊", "").strip()
            results["wechat"] = self.wechat.send(title, wechat_content)

        if self.email.enabled:
            results["email"] = self.email.send(email_subject, email_html, email_text)

        if self.feishu.enabled:
            title = email_subject.replace("📊", "").strip()
            results["feishu"] = self.feishu.send(title, wechat_content)

        if results["wechat"] or results["email"] or results["feishu"]:
            print("✅ 报告推送完成")
        else:
            print("⚠️ 所有推送渠道都不可用，请检查 .env 配置（微信/邮件/飞书）")

        return results


def test_push():
    """测试推送功能"""
    print("=== 测试推送模块 ===")
    
    pusher = ReportPusher()
    
    # 测试内容
    wechat_content = """📊 每日股票分析 - 2026-03-14

━━━━━━━━━━━━━━━━━━
🔥 重点关注（买入评级）
━━━━━━━━━━━━━━━━━━

1. 贵州茅台 (600519)
   评级：买入 ⭐⭐⭐⭐⭐
   策略：趋势良好，可考虑介入
   理由：技术面突破，资金流入明显
   ⚠️ 风险：大盘波动

━━━━━━━━━━━━━━━━━━
💡 今日策略建议
━━━━━━━━━━━━━━━━━━
• 重点关注：1 只
• 总股票数：1 只

📌 提醒：投资有风险，决策需谨慎
"""
    
    email_html = """
<html>
<body>
    <h1>📊 每日股票分析报告</h1>
    <p>2026-03-14</p>
    <div style="padding: 10px; background: #f0f0f0;">
        <h2>🔥 重点关注</h2>
        <p><strong>贵州茅台 (600519)</strong></p>
        <p>评级：买入 ⭐⭐⭐⭐⭐</p>
        <p>策略：趋势良好，可考虑介入</p>
    </div>
</body>
</html>
"""
    
    # 推送测试
    results = pusher.push_report(
        wechat_content=wechat_content,
        email_subject="📊 每日股票分析 - 2026-03-14",
        email_html=email_html,
        email_text=wechat_content
    )
    
    print(f"\n推送结果:")
    print(f"  微信：{'✅' if results['wechat'] else '❌'}")
    print(f"  邮件：{'✅' if results['email'] else '❌'}")
    print(f"  飞书：{'✅' if results.get('feishu') else '❌'}")

    return results


if __name__ == "__main__":
    test_push()
