"""
通知发送模块
集成现有平台的通知系统
"""

import asyncio
import json
import logging
from typing import Dict, List, Any
from datetime import datetime

from .config import DailyStockConfig


class NotificationSender:
    """通知发送器"""

    def __init__(self, config: DailyStockConfig):
        self.config = config
        self.logger = logging.getLogger("daily_stock_analysis.notification")

        # 通知渠道处理器
        self.channel_handlers = {
            "telegram": self._send_telegram,
            "email": self._send_email,
            "webhook": self._send_webhook,
            "console": self._send_console,
            "file": self._send_to_file,
        }

    async def send_analysis_results(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送分析结果通知

        Args:
            analysis_results: 分析结果

        Returns:
            发送结果
        """
        self.logger.info("开始发送分析结果通知")

        try:
            # 准备通知内容
            notification_content = self._prepare_notification_content(analysis_results)

            # 发送到所有配置的渠道
            send_results = {}
            successful_channels = []
            failed_channels = []

            for channel in self.config.notification_channels:
                if channel in self.channel_handlers:
                    try:
                        self.logger.info("通过 %s 发送通知", channel)
                        result = await self.channel_handlers[channel](notification_content)
                        send_results[channel] = result
                        successful_channels.append(channel)
                        self.logger.info("%s 通知发送成功", channel)
                    except Exception as e:
                        self.logger.error("%s 通知发送失败: {e}", channel)
                        send_results[channel] = {"status": "error", "error": str(e)}
                        failed_channels.append(channel)
                else:
                    self.logger.warning("不支持的通知渠道: %s", channel)
                    send_results[channel] = {"status": "unsupported"}

            # 汇总结果
            summary = {
                "timestamp": datetime.now().isoformat(),
                "total_channels": len(self.config.notification_channels),
                "successful_channels": successful_channels,
                "failed_channels": failed_channels,
                "success_rate": (
                    len(successful_channels) / len(self.config.notification_channels)
                    if self.config.notification_channels
                    else 0
                ),
                "detailed_results": send_results,
                "status": "success" if successful_channels else "failed",
            }

            self.logger.info("通知发送完成: %s成功, %s失败", len(successful_channels), len(failed_channels))
            return summary

        except Exception as e:
            self.logger.error("通知发送失败: %s", e, exc_info=True)
            return {"timestamp": datetime.now().isoformat(), "error": str(e), "status": "error"}

    def _prepare_notification_content(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """准备通知内容"""
        # 提取关键信息
        recommendations = analysis_results.get("recommendations", {})
        top_picks = recommendations.get("top_picks", [])

        # 创建不同格式的内容
        content = {
            "timestamp": analysis_results.get("timestamp", datetime.now().isoformat()),
            "model_used": analysis_results.get("model_used", "unknown"),
            "summary": {
                "market_count": analysis_results.get("analysis_data_summary", {}).get(
                    "market_count", 0
                ),
                "total_symbols": analysis_results.get("analysis_data_summary", {}).get(
                    "total_symbols", 0
                ),
                "recommendation_count": len(top_picks),
            },
            "top_recommendations": top_picks[:5],  # 只取前5个
            "full_analysis": analysis_results,
            # 不同渠道的格式化内容
            "formatted": {
                "short": self._format_short_content(top_picks),
                "detailed": self._format_detailed_content(analysis_results),
                "html": self._format_html_content(analysis_results),
                "markdown": self._format_markdown_content(analysis_results),
            },
        }

        return content

    def _format_short_content(self, top_picks: List[Dict]) -> str:
        """格式化简短内容"""
        if not top_picks:
            return "今日无推荐股票"

        lines = ["📈 今日AI股票推荐:"]
        for i, pick in enumerate(top_picks[:3], 1):
            symbol = pick.get("symbol", "未知")
            name = pick.get("name", "")
            action = pick.get("action", "未知")
            reason = pick.get("reason", "")[:30]

            lines.append(f"{i}. {symbol} {name} - {action}")
            if reason:
                lines.append(f"   理由: {reason}")

        lines.append(f"\n共推荐 {len(top_picks)} 只股票")
        return "\n".join(lines)

    def _format_detailed_content(self, analysis_results: Dict[str, Any]) -> str:
        """格式化详细内容"""
        recommendations = analysis_results.get("recommendations", {})
        top_picks = recommendations.get("top_picks", [])
        analysis = recommendations.get("analysis", {})

        lines = [
            "=" * 50,
            "📊 AI股票分析报告",
            "=" * 50,
            f"生成时间: {analysis_results.get('timestamp', '未知')}",
            f"使用模型: {analysis_results.get('model_used', '未知')}",
            "",
        ]

        # 市场概况
        if analysis:
            lines.append("📈 市场概况:")
            lines.append(f"  市场情绪: {analysis.get('market_sentiment', '未知')}")
            lines.append(f"  风险等级: {analysis.get('risk_level', '未知')}")
            lines.append(f"  机会领域: {', '.join(analysis.get('opportunity_areas', []))}")
            lines.append("")

        # 推荐股票
        if top_picks:
            lines.append("🎯 推荐股票:")
            for i, pick in enumerate(top_picks, 1):
                symbol = pick.get("symbol", "未知")
                name = pick.get("name", "")
                action = pick.get("action", "未知")
                confidence = pick.get("confidence", 0)
                reason = pick.get("reason", "")

                lines.append(f"{i}. {symbol} {name}")
                lines.append(f"   操作: {action} (置信度: {confidence:.1%})")
                lines.append(f"   理由: {reason}")
                lines.append("")

        # 风险提示
        risk_warnings = recommendations.get("risk_warnings", [])
        if risk_warnings:
            lines.append("⚠️ 风险提示:")
            for warning in risk_warnings:
                lines.append(f"  • {warning}")
            lines.append("")

        lines.append("=" * 50)
        return "\n".join(lines)

    def _format_html_content(self, analysis_results: Dict[str, Any]) -> str:
        """格式化HTML内容"""
        recommendations = analysis_results.get("recommendations", {})
        top_picks = recommendations.get("top_picks", [])

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>AI股票分析报告</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .recommendation {{ border: 1px solid #ddd; }}
                .recommendation {{ padding: 15px; margin: 10px 0; border-radius: 5px; }}
                .buy {{ border-left: 5px solid #4CAF50; }}
                .hold {{ border-left: 5px solid #FFC107; }}
                .sell {{ border-left: 5px solid #F44336; }}
                .confidence {{ color: #666; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 AI股票分析报告</h1>
                <p>生成时间: {analysis_results.get('timestamp', '未知')}</p>
                <p>使用模型: {analysis_results.get('model_used', '未知')}</p>
            </div>
        """

        if top_picks:
            html += "<h2>🎯 推荐股票</h2>"
            for pick in top_picks:
                action = pick.get("action", "未知")
                action_class = "buy" if action == "买入" else "sell" if action == "卖出" else "hold"

                html += f"""
                <div class="recommendation {action_class}">
                    <h3>{pick.get('symbol', '未知')} - {pick.get('name', '')}</h3>
                    <p><strong>操作建议:</strong> {action}</p>
                    <p class="confidence">置信度: {pick.get('confidence', 0):.1%}</p>
                    <p><strong>理由:</strong> {pick.get('reason', '')}</p>
                </div>
                """

        html += """
            <div style="margin-top: 30px; padding: 15px; background-color: #fff3cd; border-radius: 5px;">
                <h3>⚠️ 免责声明</h3>
                <p>本报告仅为AI分析结果，不构成投资建议。投资有风险，入市需谨慎。</p>
            </div>
        </body>
        </html>
        """

        return html

    def _format_markdown_content(self, analysis_results: Dict[str, Any]) -> str:
        """格式化Markdown内容"""
        return self._format_detailed_content(analysis_results)

    async def _send_telegram(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """发送到Telegram（模拟）"""
        # 这里应该集成实际的Telegram Bot API

        await asyncio.sleep(0.2)

        short_content = content["formatted"]["short"]
        self.logger.info("Telegram消息内容: %s...", short_content[:100])

        return {
            "channel": "telegram",
            "status": "success",
            "message_id": "mock_telegram_message_id",
            "content_length": len(short_content),
            "timestamp": datetime.now().isoformat(),
        }

    async def _send_email(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """发送邮件（模拟）"""
        # 这里应该集成实际的邮件发送服务

        await asyncio.sleep(0.3)

        html_content = content["formatted"]["html"]
        self.logger.info("邮件内容长度: %s 字符", len(html_content))

        return {
            "channel": "email",
            "status": "success",
            "recipient_count": 1,
            "content_type": "html",
            "timestamp": datetime.now().isoformat(),
        }

    async def _send_webhook(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """发送Webhook（模拟）"""
        # 这里应该发送HTTP POST请求到配置的webhook URL

        await asyncio.sleep(0.1)

        return {
            "channel": "webhook",
            "status": "success",
            "url": "mock_webhook_url",
            "payload_size": len(str(content)),
            "timestamp": datetime.now().isoformat(),
        }

    async def _send_console(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """输出到控制台"""
        detailed_content = content["formatted"]["detailed"]
        print("\n" + "=" * 60)
        print("控制台通知:")
        print("=" * 60)
        print(detailed_content)
        print("=" * 60)

        return {
            "channel": "console",
            "status": "success",
            "output": "printed_to_console",
            "timestamp": datetime.now().isoformat(),
        }

    async def _send_to_file(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """保存到文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"daily_stock_analysis_{timestamp}.json"

        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False, indent=2)

            self.logger.info("分析结果已保存到文件: %s", filename)

            return {
                "channel": "file",
                "status": "success",
                "filename": filename,
                "file_size": len(json.dumps(content)),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error("保存到文件失败: %s", e)
            return {
                "channel": "file",
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def send_alert(
        self, alert_type: str, message: str, data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """发送警报"""
        self.logger.warning("发送警报: %s - {message}", alert_type)

        alert_content = {
            "type": alert_type,
            "message": message,
            "data": data or {},
            "timestamp": datetime.now().isoformat(),
            "severity": "warning",
        }

        # 发送到控制台（实际使用中应该发送到所有配置的渠道）
        console_result = await self._send_console(
            {"formatted": {"detailed": f"🚨 警报: {alert_type}\n{message}"}}
        )

        return {
            "alert": alert_content,
            "notification_result": console_result,
            "timestamp": datetime.now().isoformat(),
        }
