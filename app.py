#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AKShare 数据网页展示 - 运行后访问 http://127.0.0.1:5000"""
from flask import Flask, render_template_string

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AKShare 数据展示</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; background: #1a1a2e; color: #eee; min-height: 100vh; }
    .layout { display: flex; min-height: 100vh; }
    /* 侧边栏 */
    .sidebar { width: 280px; flex-shrink: 0; background: #16213e; border-right: 1px solid #2a2a4a; padding: 20px; overflow-y: auto; }
    .sidebar h2 { color: #0f9; font-size: 1rem; margin: 0 0 12px 0; padding-bottom: 8px; border-bottom: 1px solid #2a2a4a; }
    .sidebar ul { list-style: none; padding: 0; margin: 0; }
    .sidebar li { margin-bottom: 8px; }
    .sidebar a { color: #7dd; text-decoration: none; }
    .sidebar a:hover { color: #0f9; text-decoration: underline; }
    .sidebar .block { margin-bottom: 24px; }
    .sidebar .meta { font-size: 13px; color: #888; line-height: 1.5; }
    .sidebar .version { color: #0f9; font-weight: 600; }
    /* 主内容区 */
    .main { flex: 1; padding: 24px; overflow-x: auto; }
    h1 { color: #0f9; margin: 0 0 8px 0; }
    .main .meta { color: #888; margin-bottom: 20px; font-size: 14px; }
    .table-wrap { overflow-x: auto; border-radius: 8px; background: #16213e; padding: 16px; margin-top: 16px; }
    .table-wrap table { width: 100%; border-collapse: collapse; font-size: 14px; }
    .table-wrap th, .table-wrap td { padding: 10px 12px; text-align: left; border: 1px solid #2a2a4a; }
    .table-wrap th { background: #0f3460; color: #0f9; font-weight: 600; white-space: nowrap; }
    .table-wrap td { color: #ddd; }
    .table-wrap tr:hover { background: #1f2f4a; }
    .table-wrap tr:nth-child(even) { background: #1a2744; }
    .table-wrap tr:nth-child(even):hover { background: #1f2f4a; }
    .err { color: #f55; }
    .ok { color: #0f9; }
  </style>
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      <div class="block">
        <h2>AKShare 版本</h2>
        <p class="meta"><span class="version">{{ version }}</span></p>
      </div>
      <div class="block">
        <h2>本页数据说明</h2>
        <p class="meta">接口：<code>stock_zh_a_hist</code><br>标的：{{ symbol }}（{{ name }}）<br>周期：日线<br>区间：{{ start_date }} ~ {{ end_date }}<br>展示：前 {{ rows }} 条</p>
      </div>
      <div class="block">
        <h2>相关链接</h2>
        <ul>
          <li><a href="https://github.com/akfamily/akshare" target="_blank" rel="noopener">AKShare GitHub</a></li>
          <li><a href="https://akshare.akfamily.xyz/" target="_blank" rel="noopener">AKShare 文档</a></li>
          <li><a href="https://pypi.org/project/akshare/" target="_blank" rel="noopener">PyPI - akshare</a></li>
        </ul>
      </div>
      <div class="block">
        <h2>本地运行</h2>
        <p class="meta">激活 venv 后执行：<br><code>python app.py</code><br>或：<br><code>./scripts/run.sh</code></p>
      </div>
    </aside>
    <main class="main">
      <h1>AKShare 数据展示</h1>
      <p class="meta">数据来源：东方财富 A 股日线 · 下方为行情表</p>
      <div class="table-wrap">
        {{ table_html | safe }}
      </div>
    </main>
  </div>
</body>
</html>
"""


@app.route("/")
def index():
    version = "—"
    symbol = "000001"
    name = "平安银行"
    start_date = "2025-01-01"
    end_date = "2025-06-01"
    rows = 15
    table_html = "<p class='err'>获取数据失败</p>"
    try:
        from akshare._version import __version__
        version = __version__
        from akshare.stock_feature.stock_hist_em import stock_zh_a_hist
        df = stock_zh_a_hist(symbol=symbol, period="daily", start_date="20250101", end_date="20250601", adjust="")
        table_html = df.head(rows).to_html(classes=None, index=False)
    except Exception as e:
        table_html = f"<p class='err'>错误: {e}</p>"
    return render_template_string(
        HTML,
        version=version,
        symbol=symbol,
        name=name,
        start_date=start_date,
        end_date=end_date,
        rows=rows,
        table_html=table_html,
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
