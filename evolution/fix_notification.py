#!/usr/bin/env python3
"""Fix remaining logging issues in notification.py"""

from pathlib import Path

filepath = Path("strategy-engine/src/strategies/daily_stock_analysis/notification.py")
content = filepath.read_text(encoding='utf-8')

# Fix remaining f-string logging
content = content.replace(
    'self.logger.error(f"通知发送失败：{e}", exc_info=True)',
    'self.logger.error("通知发送失败：%s", e, exc_info=True)'
)
content = content.replace(
    'self.logger.info(f"Telegram 消息内容：{short_content[:100]}...")',
    'self.logger.info("Telegram 消息内容：%s...", short_content[:100])'
)
content = content.replace(
    'self.logger.info(f"邮件内容长度：{len(html_content)} 字符")',
    'self.logger.info("邮件内容长度：%d 字符", len(html_content))'
)

filepath.write_text(content, encoding='utf-8')
print("Fixed notification.py")
