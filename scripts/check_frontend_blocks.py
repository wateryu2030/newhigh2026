#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前端区块检测：请求平台首页，检查「机构组合结果」「AI 推荐列表」等是否存在于 HTML 中。
不依赖 OpenClaw/浏览器，可用于 CI 或本地验证。
用法: python3 scripts/check_frontend_blocks.py [--base-url http://127.0.0.1:5050]
"""
from __future__ import annotations
import argparse
import sys
import urllib.request
import urllib.error


REQUIRED = [
    ("机构组合结果", "机构组合结果 标题"),
    ("AI 推荐列表", "AI 推荐列表 标题"),
    ("resultPortfolioCard", "机构组合卡片 id"),
    ("resultAiRecommendCard", "AI 推荐卡片 id"),
    ("btnLoadPortfolio", "加载机构组合按钮 id"),
    ("btnLoadAiRecommend", "加载 AI 推荐按钮 id"),
]
OPTIONAL_API = [
    ("/api/portfolio_result", "POST", "机构组合 API"),
    ("/api/ai_recommendations", "GET", "AI 推荐 API"),
]


def main() -> int:
    p = argparse.ArgumentParser(description="Check astock frontend for 机构组合 & AI 推荐 blocks")
    p.add_argument("--base-url", default="http://127.0.0.1:5050", help="Base URL of web platform")
    args = p.parse_args()
    base = args.base_url.rstrip("/")
    errors: list[str] = []

    # 1) 拉取首页 HTML
    try:
        req = urllib.request.Request(base + "/", headers={"User-Agent": "check_frontend_blocks/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as e:
        errors.append(f"无法请求首页: {e}")
        for msg in errors:
            print("FAIL:", msg)
        return 1
    except Exception as e:
        errors.append(f"请求首页异常: {e}")
        for msg in errors:
            print("FAIL:", msg)
        return 1

    # 2) 检查必备字符串
    for s, label in REQUIRED:
        if s not in html:
            errors.append(f"页面中未找到: {label} ({s!r})")
        else:
            print("OK:", label)

    # 3) 可选：快速探测 API
    for path, method, label in OPTIONAL_API:
        try:
            req = urllib.request.Request(
                base + path,
                data=b"{}" if method == "POST" else None,
                method=method,
                headers={"Content-Type": "application/json", "User-Agent": "check_frontend_blocks/1.0"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                code = resp.getcode()
                if 200 <= code < 400:
                    print("OK:", label, f"(HTTP {code})")
                else:
                    errors.append(f"{label} 返回 HTTP {code}")
        except urllib.error.HTTPError as e:
            if e.code == 405:
                errors.append(f"{label} 方法不允许 (GET/POST)")
            else:
                errors.append(f"{label} HTTP {e.code}")
        except Exception as e:
            errors.append(f"{label} 请求异常: {e}")

    if errors:
        print()
        for msg in errors:
            print("FAIL:", msg)
        return 1
    print()
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
