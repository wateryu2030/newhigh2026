#!/usr/bin/env python3
"""
政策信息采集自动化脚本 v3
- 使用 Python requests 抓取网页
- AI 分类整理 + 情绪分析
- 通过 OpenClaw message 工具发送飞书推送
- 入库：主库 DuckDB ``news_items``（``symbol=__POLICY__``），与 Gateway 共用 ``QUANT_SYSTEM_DUCKDB_PATH``。

定时任务：每日 08:30
执行方式：`python3 integrations/hongshan/policy-news/news_collector.py`

依赖:
    pip install requests beautifulsoup4
"""

import json
import os
import subprocess
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urljoin

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("警告：requests/beautifulsoup4 未安装，使用简化模式")
    print("安装：pip install requests beautifulsoup4")

# 配置 - 扩展采集源
SOURCES = [
    {"name": "中国政府网", "url": "https://www.gov.cn/zhengce/", "type": "policy", "priority": 1},
    {"name": "新华网财经", "url": "https://www.xinhuanet.com/fortune/", "type": "news", "priority": 2},
]

# 政策影响领域分类
POLICY_DOMAINS = {
    "金融": ["金融", "银行", "保险", "证券", "货币", "利率", "信贷"],
    "房地产": ["房地产", "住房", "楼市", "土地", "住建", "购房"],
    "科技": ["科技", "创新", "AI", "人工智能", "芯片", "半导体", "数字经济"],
    "贸易": ["贸易", "出口", "进口", "关税", "外贸", "跨境电商"],
    "民生": ["民生", "社保", "医疗", "教育", "就业", "养老", "长护险"],
    "农业": ["农业", "农村", "农民", "土地", "承包", "粮食"],
    "环保": ["环保", "碳", "排放", "绿色", "能源", "双碳"],
}

# integrations/hongshan（日志与 policy-news 同级）
HS_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = HS_ROOT / "logs"

# 飞书 open_id：优先环境变量，避免把个人 ID 硬编码进仓库（未设置时沿用原默认值）
FEISHU_TARGET = os.environ.get(
    "FEISHU_POLICY_NOTIFY_OPEN_ID", "ou_7d2e5305dd8edefbbb7a12b1d72006bc"
)


def log(message: str):
    """日志记录"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    
    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / "policy_collector.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")


_POLICY_LINK_NOISE = frozenset(
    {
        "首页",
        "更多",
        "下一页",
        "上一页",
        "关闭",
        "打开菜单",
        "关怀版",
        "无障碍",
        "繁体版",
        "注册",
        "登录",
        "网站地图",
        "联系我们",
    }
)


def fetch_soup(url: str, timeout: int = 30):
    """下载并解析 HTML；失败返回 None。"""
    if not HAS_REQUESTS:
        return None
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or response.encoding or "utf-8"
        return BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        log(f"抓取 {url} 失败：{e}")
        return None


def fetch_web_content(url: str, timeout: int = 30) -> Optional[str]:
    """纯文本（兜底关键词行解析）。"""
    soup = fetch_soup(url, timeout=timeout)
    if not soup:
        return None
    text = soup.get_text(separator="\n", strip=True)
    return text[:10000]


def _link_looks_like_policy_article(url: str, title: str, list_page: str = "") -> bool:
    """过滤导航链：正文链接通常含栏目路径或标题含政策语义。"""
    u = url.lower()
    lp = list_page.lower()
    if any(
        x in u
        for x in (
            "/zhengce/",
            "/content_",
            "gov.cn/lianbo",
            "gov.cn/xinwen",
            "xinhuanet.com/fortune/",
            "xinhuanet.com/politics/",
            "/202",
            "/2023/",
            "/2024/",
            "/2025/",
            "/2026/",
        )
    ):
        return True
    # 新华网财经列表以脚本/相对路径为主，放宽为同站 + 标题长度
    if "xinhuanet.com" in u and ("/fortune/" in lp or "fortune" in lp):
        return len(title) >= 14
    return any(
        kw in title
        for kw in ("国务院", "中共中央", "国办", "通知", "意见", "条例", "政策", "规划", "方案", "部署", "会议")
    )


def extract_items_from_policy_links(soup: BeautifulSoup, source: str, page_url: str, max_items: int = 12) -> List[Dict]:
    """从列表页 ``<a href>`` 抽标题+链接，比整页纯文本关键词更稳。"""
    items: List[Dict] = []
    seen: set[str] = set()
    for a in soup.select("a[href]"):
        href = (a.get("href") or "").strip()
        if not href or href.startswith("#") or "javascript:" in href.lower():
            continue
        full = urljoin(page_url, href).split("#")[0]
        title = " ".join((a.get_text() or "").split())
        if len(title) < 12 or len(title) > 180:
            continue
        if title in _POLICY_LINK_NOISE:
            continue
        if not any("\u4e00" <= c <= "\u9fff" for c in title):
            continue
        if not _link_looks_like_policy_article(full, title, page_url):
            continue
        key = title[:120]
        if key in seen:
            continue
        seen.add(key)
        items.append(
            {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "source": source,
                "title": title,
                "url": full,
                "category": "待分类",
                "sentiment": 0.0,
                "domains": [],
            }
        )
        if len(items) >= max_items:
            break
    return items


def extract_items_from_content(content: str, source: str) -> List[Dict]:
    """从网页内容中提取政策条目"""
    items = []
    
    if not content:
        return items
    
    lines = content.split('\n')
    date_pattern = r'(\d{4}-\d{2}-\d{2})'
    
    # 扩展关键词
    policy_keywords = [
        "政策", "意见", "通知", "决定", "批复", "条例", "规定", "办法", 
        "部署", "会议", "国务院", "中共中央", "国办", "发布", "印发",
        "经济", "金融", "市场", "发展", "改革", "创新", "支持", "推进"
    ]
    
    for line in lines:
        line = line.strip()
        # 放宽长度限制
        if len(line) < 10 or len(line) > 150:
            continue
        
        # 检查是否包含关键词
        for keyword in policy_keywords:
            if keyword in line:
                date_match = re.search(date_pattern, line)
                date = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")
                
                # 去重检查
                title_exists = any(item["title"] == line for item in items)
                if not title_exists:
                    items.append({
                        "date": date,
                        "source": source,
                        "title": line,
                        "url": "",
                        "category": "待分类",
                        "sentiment": 0.0,
                        "domains": []
                    })
                break
        
        # 限制数量
        if len(items) >= 8:
            break
    
    # 如果没提取到，返回一个通用条目
    if not items and len(content) > 100:
        items.append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "source": source,
            "title": f"{source}内容更新",
            "url": "",
            "category": "其他政策",
            "sentiment": 0.0,
            "domains": ["综合"]
        })
    
    return items[:8]


def ai_classify_item(item: Dict) -> Dict:
    """AI 智能分类单个条目"""
    title = item.get("title", "")
    
    # 分类
    if "国务院" in title or "中共中央" in title or "国办" in title or "常委" in title:
        item["category"] = "国务院政策"
    elif "金融" in title or "银行" in title or "证券" in title or "保险" in title:
        item["category"] = "金融政策"
    elif "经济" in title or "市场" in title or "增长" in title or "GDP" in title:
        item["category"] = "经济新闻"
    elif "住建" in title or "房地产" in title or "楼市" in title:
        item["category"] = "住建政策"
    elif "科技" in title or "创新" in title or "AI" in title or "芯片" in title:
        item["category"] = "科技政策"
    elif "农业" in title or "农村" in title or "土地" in title or "粮食" in title:
        item["category"] = "农业政策"
    elif "社保" in title or "医疗" in title or "养老" in title or "长护险" in title or "就业" in title:
        item["category"] = "民生政策"
    else:
        item["category"] = "其他政策"
    
    # 情绪分析
    positive_words = ["增长", "提升", "支持", "鼓励", "发展", "利好", "改善", "突破", "加快", "推进"]
    negative_words = ["下降", "限制", "收紧", "风险", "警告", "下滑", "压力", "放缓"]
    
    sentiment_score = 0.0
    for word in positive_words:
        if word in title:
            sentiment_score += 0.15
    for word in negative_words:
        if word in title:
            sentiment_score -= 0.15
    
    item["sentiment"] = max(-1.0, min(1.0, sentiment_score))
    
    # 影响领域
    domains = []
    for domain, keywords in POLICY_DOMAINS.items():
        for keyword in keywords:
            if keyword in title:
                domains.append(domain)
                break
    item["domains"] = domains if domains else ["综合"]
    
    return item


def generate_summary(items: List[Dict]) -> str:
    """生成政策摘要"""
    if not items:
        return "今日无重要政策更新"
    
    priority_order = {"国务院政策": 1, "金融政策": 2, "民生政策": 3, "科技政策": 4, 
                      "经济新闻": 5, "住建政策": 6, "农业政策": 7, "其他政策": 8}
    items_sorted = sorted(items, key=lambda x: priority_order.get(x.get("category", "其他政策"), 9))
    
    summary_lines = []
    for item in items_sorted[:3]:
        sentiment_emoji = "📈" if item.get("sentiment", 0) > 0.1 else "📉" if item.get("sentiment", 0) < -0.1 else "➡️"
        summary_lines.append(f"{sentiment_emoji} {item.get('title', '')[:50]}")
    
    return "\n".join(summary_lines)


def format_message(items: List[Dict]) -> str:
    """格式化飞书消息"""
    today = datetime.now().strftime("%Y-%m-%d")
    weekday = datetime.now().strftime("%A")
    
    summary = generate_summary(items)
    
    message = f"📰 **政策情报日报** | {today}\n\n"
    message += f"**🔍 今日摘要**\n{summary}\n\n---\n\n"
    
    by_category = {}
    for item in items:
        cat = item.get("category", "其他")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(item)
    
    category_icons = {
        "国务院政策": "🏛️", "金融政策": "💰", "经济新闻": "📊",
        "住建政策": "🏠", "科技政策": "💡", "农业政策": "🌾",
        "民生政策": "👥", "其他政策": "📄"
    }
    
    for category, cat_items in sorted(by_category.items()):
        icon = category_icons.get(category, "📄")
        message += f"## {icon} {category}\n\n"
        message += "| 日期 | 来源 | 标题 | 情绪 |\n"
        message += "|------|------|------|------|\n"
        for item in cat_items[:5]:
            sentiment_emoji = "📈" if item.get("sentiment", 0) > 0.1 else "📉" if item.get("sentiment", 0) < -0.1 else "➡️"
            domains = ", ".join(item.get("domains", ["综合"]))
            title = item.get("title", "")[:35] + "..." if len(item.get("title", "")) > 35 else item.get("title", "")
            message += f"| {item.get('date', '')} | {item.get('source', '')} | {title} | {sentiment_emoji} |\n"
        message += f"*影响领域：{domains}*\n\n"
    
    message += "---\n\n*来源：中国政府网、新华网 | newhigh-01 AI 采集*"
    
    return message


def save_to_database(items: List[Dict]) -> int:
    """保存新闻至主库 DuckDB ``news_items``（symbol=__POLICY__）。"""
    _here = Path(__file__).resolve().parent
    sys.path.insert(0, str(_here))
    try:
        from news_database import insert_news

        n = insert_news(items)
        log(f"✓ DuckDB news_items 写入 {n} 条")
        return n
    except Exception as e:
        log(f"✗ DuckDB 写入失败：{e}")
        return 0


def send_feishu_message(message: str) -> bool:
    """发送飞书消息"""
    # 通过 OpenClaw message 工具发送
    # 使用配置的 target 用户 ID
    safe_message = message.replace('"', '\\"').replace('\n', '\\n')
    
    cmd = f'openclaw message send --channel feishu --target "user:{FEISHU_TARGET}" --message "{safe_message}" 2>/dev/null'
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            log("✓ 飞书消息发送成功")
            return True
        else:
            log(f"✗ 发送返回码：{result.returncode}")
            if result.stderr:
                log(f"  错误：{result.stderr[:200]}")
            return False
    except Exception as e:
        log(f"✗ 发送异常：{e}")
        return False


def main():
    log("=" * 60)
    log("开始执行政策信息采集任务 (v3)")
    log(f"依赖状态：requests={HAS_REQUESTS}")
    
    all_items = []
    
    # 1. 抓取各来源（优先 DOM 链接，再兜底纯文本关键词）
    for source in SOURCES:
        log(f"抓取 {source['name']}...")
        soup = fetch_soup(source["url"])
        items: List[Dict] = []
        if soup:
            items = extract_items_from_policy_links(soup, source["name"], source["url"])
            if not items:
                text = soup.get_text(separator="\n", strip=True)
                items = extract_items_from_content(text[:10000], source["name"])
            for item in items:
                ai_classify_item(item)
            all_items.extend(items)
            log(f"  → 提取 {len(items)} 条")
        else:
            log(f"  → 抓取失败，使用预设数据")
            all_items.append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "source": source["name"],
                "title": f"{source['name']}内容更新",
                "category": "其他政策",
                "sentiment": 0.0,
                "domains": ["综合"],
                "url": "",
            })
    
    # 2. 去重
    seen_titles = set()
    unique_items = []
    for item in all_items:
        title = item.get("title", "")
        if title not in seen_titles:
            seen_titles.add(title)
            unique_items.append(item)
    
    log(f"去重后共 {len(unique_items)} 条信息")
    
    # 3. 保存到数据库
    if unique_items:
        save_to_database(unique_items)
    
    # 4. 格式化消息
    message = format_message(unique_items)
    
    # 5. 发送飞书
    if send_feishu_message(message):
        log("=" * 60)
        log("✓ 任务完成")
        return 0
    else:
        log("=" * 60)
        log("✗ 任务失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
