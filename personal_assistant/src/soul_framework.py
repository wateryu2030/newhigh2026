#!/usr/bin/env python3
"""
docs/soul.md「机会发现引擎」— 深度分析、报告生成与 AI 提示词复用。
"""

import os
from typing import List

# personal_assistant/src -> personal_assistant -> 仓库根
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
_PA_ROOT = os.path.dirname(_SRC_DIR)
_PROJECT_ROOT = os.path.dirname(_PA_ROOT)

# soul.md 候选路径（仓库根 docs 优先）
_SOUL_CANDIDATES: List[str] = [
    os.path.join(_PROJECT_ROOT, "docs", "soul.md"),
    os.path.join(_PA_ROOT, "docs", "soul.md"),
]


def load_soul_markdown() -> str:
    """读取 docs/soul.md 全文；缺失或读失败返回空串。"""
    for path in _SOUL_CANDIDATES:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except OSError:
                continue
    return ""


# 文件不可用时仍保证报告/终端有可用的固定要点（与 soul.md 一致）
OPPORTUNITY_ENGINE_CHECKLIST_CN = """
机会发现引擎（永久规则摘要）：
1. 识别低效之处 — 信息不对称、技术颠覆、法规变化、定价错误、消费行为转变等。
2. 评估不对称性 — 下行有限、上行潜力大；聚焦高期望值。
3. 及早检测新兴趋势 — 新基建、大额资金、机构采用、社区增长等信号。
4. 规划变现路径 — 投资、工具/服务、信息套利、自动化、分销优势等。
5. 评估竞争格局 — 拥挤度、壁垒、可利用优势；高壁垒、低认知更宝贵。
6. 排序机会 — 期望值、执行难度、资本、时间跨度；优先风险/回报比。
7. 创意思考 — 非常规路径、技术组合、被忽略细分。
""".strip()


def soul_body_for_prompt() -> str:
    """用于拼入长提示：优先全文，否则摘要。"""
    full = load_soul_markdown()
    return full if full else OPPORTUNITY_ENGINE_CHECKLIST_CN


def build_industry_opportunity_section(
    name: str,
    code: str,
    industry: str,
) -> str:
    """
    深度分析结果中的固定段落：行业地位与前景 + 机会发现引擎全文/摘要。
    """
    body = soul_body_for_prompt()
    return (
        "### 行业地位与前景（机会发现引擎 / docs/soul.md）\n\n"
        f"**标的**：{name}（{code}）  \n"
        f"**数据侧行业**：{industry}\n\n"
        "以下框架须由人工或下游 AI 在定性报告中逐项回应（行业地位侧重低效、竞争格局、创意思考；"
        "行业前景侧重不对称性、新兴趋势、机会排序）：\n\n"
        "---\n\n"
        f"{body}\n\n"
        "---\n"
    )


def daily_report_methodology_footer_text() -> str:
    """每日推送/微信报告末尾固定方法论说明（精简版）。"""
    return (
        "━━━━━━━━━━━━━━━━━━\n"
        "📌 分析方法论（永久规则）\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "行业地位与前景须结合「机会发现引擎」（docs/soul.md）：\n"
        "识别低效 → 评估不对称性 → 检测新兴趋势 → 变现路径 → 竞争格局 → 排序机会 → 创意思考。\n"
        "完整条文见仓库 docs/soul.md。\n"
    )


def daily_report_methodology_footer_html() -> str:
    """邮件 HTML 报告中的方法论区块。"""
    return """
    <div class="section" style="border-left-color:#6c757d;">
        <h2>📌 分析方法论（永久规则 · 机会发现引擎）</h2>
        <p><strong>行业地位与前景</strong>须结合 <code>docs/soul.md</code> 中的框架：</p>
        <ol style="margin-left:1.2em;">
            <li>识别低效之处</li>
            <li>评估不对称性</li>
            <li>及早检测新兴趋势</li>
            <li>规划变现路径</li>
            <li>评估竞争格局</li>
            <li>排序机会</li>
            <li>创意思考</li>
        </ol>
        <p style="color:#666;font-size:14px;">完整条文见仓库 <code>docs/soul.md</code>。</p>
    </div>
"""
