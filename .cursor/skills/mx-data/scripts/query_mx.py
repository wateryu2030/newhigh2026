#!/usr/bin/env python3
"""妙想金融数据 API 调用示例：检查 MX_APIKEY 并可选执行一次查询。"""
import os
import sys
import json

# 尝试从项目根加载 .env（与 newhigh 项目根一致）
def _load_env():
    # 从 .cursor/skills/mx-data/scripts 上溯 4 级到项目根（newhigh）
    root = os.environ.get("NEWHIGH_ROOT") or os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
    )
    env_path = os.path.join(root, ".env")
    if os.path.isfile(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    k, v = k.strip(), v.strip()
                    if v and v.endswith("#"):
                        v = v[:-1].strip()
                    os.environ.setdefault(k, v)


_load_env()
apikey = os.environ.get("MX_APIKEY")

if not apikey:
    print("未设置 MX_APIKEY。请在 .env 或环境中配置后重试。", file=sys.stderr)
    sys.exit(1)

def query(tool_query: str):
    import urllib.request
    req = urllib.request.Request(
        "https://mkapi2.dfcfs.com/finskillshub/api/claw/query",
        data=json.dumps({"toolQuery": tool_query}).encode("utf-8"),
        headers={"Content-Type": "application/json", "apikey": apikey},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "东方财富最新价"
    print("查询:", q)
    try:
        out = query(q)
        print(json.dumps(out, ensure_ascii=False, indent=2))
    except Exception as e:
        print("请求失败:", e, file=sys.stderr)
        sys.exit(1)
