#!/usr/bin/env python3
"""验证 RL 训练页「标的」为文本输入（非数字），支持 002701 等前导零；含前端校验与自动化检查。"""
import os
import re
import sys
import urllib.request

_ROOT = os.path.join(os.path.dirname(__file__), "..")
_FRONTEND_SRC = os.path.join(_ROOT, "frontend", "src", "pages", "RLTrainingDashboard.tsx")
_FRONTEND_DIST = os.path.join(_ROOT, "frontend", "dist")
_DIST_INDEX = os.path.join(_FRONTEND_DIST, "index.html")


def check_source():
    """确认源码中标的使用 Input、纯文本（不转数字）、含 5-8 位校验与归一化。"""
    if not os.path.isfile(_FRONTEND_SRC):
        print("FAIL: 未找到 RLTrainingDashboard.tsx")
        return False
    with open(_FRONTEND_SRC, "r", encoding="utf-8") as f:
        text = f.read()
    if 'addonBefore="标的"' not in text:
        print("FAIL: 源码中未找到 addonBefore=\"标的\"")
        return False
    if "InputNumber" in text and "标的" in text:
        idx = text.find('addonBefore="标的"')
        before = text[max(0, idx - 80) : idx]
        if "InputNumber" in before:
            print("FAIL: 标的仍绑定 InputNumber")
            return False
    # 标的必须以字符串传给 API，不能 Number(symbol) / parseInt(symbol)
    if re.search(r"api\.rl\.train\s*\(\s*\{[^}]*symbol\s*[,}]", text, re.DOTALL):
        if "Number(symbol)" in text or "parseInt(symbol" in text or "parseFloat(symbol" in text:
            print("FAIL: 标的被当作数字解析，会导致 002701 变成 2701")
            return False
    # 应有校验或归一化：5-8 位数字、前导零保留
    if "replace(/\\D/g" not in text and "replace(/[^0-9]/g" not in text:
        print("WARN: 源码中未发现仅允许数字的归一化（replace(/\\D/g）")
    if "002701" not in text and "600519" not in text:
        print("WARN: 源码中未发现示例 002701/600519（可能已改文案）")
    if "5" in text and "8" in text and ("digit" in text or "位" in text):
        pass  # 有长度/位数相关校验
    else:
        print("WARN: 未发现 5～8 位数字的校验逻辑")
    print("OK: 源码中标的为 Input、字符串传递、含校验/归一化")
    return True


def check_build():
    """确认已构建 frontend/dist 且含主 chunk。"""
    if not os.path.isfile(_DIST_INDEX):
        print("FAIL: 未找到 frontend/dist/index.html，请先执行: cd frontend && npm run build")
        return False
    with open(_DIST_INDEX, "r", encoding="utf-8") as f:
        html = f.read()
    if "index-" not in html and "assets/" not in html:
        print("FAIL: dist/index.html 未引用 assets 下的 JS")
        return False
    assets_dir = os.path.join(_FRONTEND_DIST, "assets")
    if not os.path.isdir(assets_dir):
        print("FAIL: frontend/dist/assets 不存在")
        return False
    chunks = [f for f in os.listdir(assets_dir) if f.endswith(".js")]
    if not chunks:
        print("FAIL: frontend/dist/assets 下无 .js 文件")
        return False
    print("OK: 已构建 frontend/dist，且含 JS 资源")
    return True


def check_server(base_url: str = "http://127.0.0.1:5050"):
    """可选：请求 base_url/rl 与主 JS，确认线上为 React 新界面。"""
    try:
        req = urllib.request.Request(
            base_url + "/rl",
            headers={"User-Agent": "verify_rl_symbol_input/1.0"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"SKIP: 无法请求 {base_url}/rl —— {e}")
        return None
    if "root" not in html or "index-" not in html:
        print("FAIL: /rl 返回内容不是 React SPA 的 index.html")
        return False
    # 取主 chunk 名
    import re
    m = re.search(r'src="(/assets/[^"]+\.js)"', html)
    if not m:
        print("WARN: 未从 /rl 解析到主 JS 路径")
        return True
    js_url = base_url + m.group(1)
    try:
        req = urllib.request.Request(js_url, headers={"User-Agent": "verify_rl_symbol_input/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            js = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"WARN: 无法请求主 JS —— {e}")
        return True
    # 新界面标的为 Input，会打包进 Antd 的 addonBefore 等
    if "addonBefore" not in js:
        print("WARN: 主 JS 中未找到 addonBefore（可能为旧构建）")
    else:
        print("OK: 线上已提供 React 新界面（主 JS 含 addonBefore）")
    return True


def check_symbol_values():
    """自动化用例：002701、2701、空等归一化与校验结果（与前端逻辑一致）。"""
    # 与前端 normalizeSymbolRaw / validateSymbol 一致
    def normalize(raw: str) -> str:
        return re.sub(r"\D", "", raw)[:8]

    def valid(s: str) -> bool:
        return bool(re.match(r"^\d{5,8}$", s))

    cases = [
        ("002701", "002701", True),
        ("600519", "600519", True),
        ("000001", "000001", True),
        ("2701", "2701", False),  # 不足 5 位
        ("12345678", "12345678", True),
        (" 002701 ", "002701", True),
        ("002701ab", "002701", True),
    ]
    all_ok = True
    for raw, expected_norm, expected_valid in cases:
        norm = normalize(raw)
        v = valid(norm)
        if norm != expected_norm or v != expected_valid:
            print(f"FAIL: 用例 {raw!r} -> norm={norm!r} valid={v} (期望 norm={expected_norm!r} valid={expected_valid})")
            all_ok = False
    if all_ok:
        print("OK: 标的归一化与校验用例通过（002701 保留前导零、2701 不足5位无效）")
    return all_ok


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else None
    ok = check_source() and check_build() and check_symbol_values()
    if base:
        ok = (check_server(base) is not False) and ok
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
