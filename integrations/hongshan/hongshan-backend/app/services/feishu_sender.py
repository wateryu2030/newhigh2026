"""
飞书消息推送服务
"""
import requests
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class FeishuSender:
    """飞书消息发送器"""
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
    
    def send_text(self, content: str, receive_ids: Optional[list] = None) -> bool:
        """发送文本消息"""
        payload = {
            "msg_type": "text",
            "content": {
                "text": content
            }
        }
        
        if receive_ids:
            payload["receive_ids"] = receive_ids
        
        return self._send(payload)
    
    def send_post(self, title: str, content_items: list) -> bool:
        """发送富文本消息"""
        payload = {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": title,
                        "content": content_items
                    }
                }
            }
        }
        
        return self._send(payload)
    
    def send_interactive_card(self, card: Dict[str, Any]) -> bool:
        """发送互动卡片"""
        payload = {
            "msg_type": "interactive",
            "card": card
        }
        
        return self._send(payload)
    
    def _send(self, payload: Dict[str, Any]) -> bool:
        """发送消息"""
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            result = response.json()
            if result.get("code") == 0:
                logger.info("飞书消息发送成功")
                return True
            else:
                logger.error(f"飞书消息发送失败：{result}")
                return False
                
        except Exception as e:
            logger.error(f"飞书消息发送异常：{e}")
            return False
    
    def send_trade_notification(self, symbol: str, name: str, order_type: str, 
                                price: float, quantity: int, status: str) -> bool:
        """发送交易通知"""
        action_text = "买入" if order_type == "buy" else "卖出"
        color = "red" if order_type == "buy" else "green"
        
        card = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": "blue",
                "title": {
                    "content": f"{'✅' if status == 'filled' else '⏳'} 交易{'成交' if status == 'filled' else '委托'}通知",
                    "tag": "plain_text"
                }
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "content": f"**股票**: {name} ({symbol})\n**操作**: {action_text}\n**价格**: ¥{price:.2f}\n**数量**: {quantity} 股\n**状态**: {status}",
                        "tag": "lark_md"
                    }
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        }
                    ]
                }
            ]
        }
        
        return self.send_interactive_card(card)
    
    def send_risk_alert(self, alert_type: str, title: str, message: str, 
                        level: str = "warning") -> bool:
        """发送风险预警"""
        level_config = {
            "info": {"color": "blue", "icon": "ℹ️"},
            "warning": {"color": "orange", "icon": "⚠️"},
            "critical": {"color": "red", "icon": "🚨"}
        }
        
        config = level_config.get(level, level_config["warning"])
        
        card = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": config["color"],
                "title": {
                    "content": f"{config['icon']} 风险预警 - {alert_type}",
                    "tag": "plain_text"
                }
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "content": f"**{title}**\n\n{message}",
                        "tag": "lark_md"
                    }
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        }
                    ]
                }
            ]
        }
        
        return self.send_interactive_card(card)
    
    def send_daily_report(self, date: str, summary: Dict[str, Any]) -> bool:
        """发送日报"""
        card = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": "green",
                "title": {
                    "content": f"📊 交易日报 ({date})",
                    "tag": "plain_text"
                }
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "content": f"**总资产**: ¥{summary.get('total_assets', 0):,.2f}\n"
                                   f"**今日盈亏**: ¥{summary.get('today_profit', 0):,.2f}\n"
                                   f"**今日收益率**: {summary.get('today_profit_rate', 0):.2f}%\n"
                                   f"**持仓市值**: ¥{summary.get('market_value', 0):,.2f}\n"
                                   f"**可用资金**: ¥{summary.get('available_cash', 0):,.2f}",
                        "tag": "lark_md"
                    }
                },
                {
                    "tag": "divider"
                },
                {
                    "tag": "div",
                    "text": {
                        "content": f"**今日交易**: {summary.get('trades_today', 0)} 笔\n"
                                   f"**胜率**: {summary.get('win_rate', 0):.1f}%",
                        "tag": "lark_md"
                    }
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "newhigh-01 🚀"
                        }
                    ]
                }
            ]
        }
        
        return self.send_interactive_card(card)


# 单例
feishu_sender = FeishuSender()
