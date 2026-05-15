#!/usr/bin/env python3
"""从 config/navigation_manifest.json 生成小程序 config/menu.generated.js（与 Web menu.ts 同源）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config" / "navigation_manifest.json"
OUT = (
    ROOT
    / "integrations"
    / "hongshan"
    / "wechat-miniprogram"
    / "config"
    / "menu.generated.js"
)


def main() -> int:
    if not MANIFEST.is_file():
        print(f"missing {MANIFEST}", file=sys.stderr)
        return 1
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    items = data.get("items") or []
    lines = [
        "/**",
        " * 由 scripts/gen_miniprogram_menu.py 从 config/navigation_manifest.json 生成，请勿手改。",
        " * Web 侧：frontend/src/config/menu.ts 从同一 JSON 派生。",
        f" * schemaVersion={data.get('schemaVersion', 0)}",
        " */",
        "module.exports.DESKTOP_SYNC = [",
    ]
    for it in items:
        label = str(it.get("labelZh") or "").replace("\\", "\\\\").replace("'", "\\'")
        mp = it.get("miniprogram") or {}
        mode = mp.get("mode")
        web_path = str(it.get("webPath") or "/")
        if mode == "native":
            route = mp.get("route")
            if not route:
                print(f"native item missing route: {it}", file=sys.stderr)
                return 1
            lines.append(f"  {{ label: '{label}', t: 'native', p: '{route}' }},")
        elif mode == "webview":
            p = web_path if web_path.startswith("/") else f"/{web_path}"
            lines.append(f"  {{ label: '{label}', t: 'web', p: '{p}' }},")
        else:
            print(f"unknown miniprogram.mode for {it}", file=sys.stderr)
            return 1
    lines.append("];")
    lines.append("")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
