#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的 Web 平台 - 使用 AKShare 数据源适配层
核心目标：让用户能够自主选择 A 股股票进行量化分析

架构：
- AKShare：数据供给层（全品类金融数据）
- RQAlpha：策略执行层（回测框架）
- Web 平台：用户界面（简化，只负责调用）
"""
from flask import Flask, render_template_string, request, jsonify
import os
import sys
import subprocess
import traceback

app = Flask(__name__)

# HTML 模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>量化交易平台 - AKShare + RQAlpha</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: #0a0e27; color: #e0e0e0; padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #0f9; margin-bottom: 30px; }
        .card {
            background: #1a1f3a; border: 1px solid #2a2a4a; border-radius: 8px;
            padding: 20px; margin-bottom: 20px;
        }
        .card h2 { color: #0f9; margin-bottom: 15px; font-size: 18px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; color: #aaa; }
        input, select, textarea {
            width: 100%; padding: 8px; background: #0f1419; border: 1px solid #2a2a4a;
            color: #e0e0e0; border-radius: 4px;
        }
        button {
            background: #0f9; color: #000; border: none; padding: 10px 20px;
            border-radius: 4px; cursor: pointer; font-weight: bold;
        }
        button:hover { background: #0cf; }
        button:disabled { background: #555; cursor: not-allowed; }
        #log {
            background: #0a0e27; border: 1px solid #2a2a4a; padding: 15px;
            border-radius: 4px; font-family: 'Courier New', monospace;
            font-size: 12px; white-space: pre-wrap; max-height: 500px; overflow-y: auto;
        }
        .status { padding: 5px 10px; border-radius: 4px; display: inline-block; }
        .status.running { background: #ff9; color: #000; }
        .status.success { background: #0f9; color: #000; }
        .status.error { background: #f99; color: #000; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 量化交易平台 - AKShare + RQAlpha</h1>
        
        <div class="card">
            <h2>📊 回测配置</h2>
            <div class="form-group">
                <label>策略文件:</label>
                <select id="strategy">
                    <option value="simple_akshare_strategy.py">简单移动平均策略</option>
                </select>
            </div>
            <div class="form-group">
                <label>股票代码 (如: 600745.XSHG 或 000001.XSHE):</label>
                <input type="text" id="stockCode" placeholder="600745.XSHG" value="600745.XSHG">
            </div>
            <div class="form-group">
                <label>开始日期:</label>
                <input type="date" id="startDate" value="2024-01-01">
            </div>
            <div class="form-group">
                <label>结束日期:</label>
                <input type="date" id="endDate" value="2024-12-31">
            </div>
            <div class="form-group">
                <label>初始资金:</label>
                <input type="number" id="initialCash" value="1000000">
            </div>
            <button onclick="runBacktest()">🚀 运行回测</button>
        </div>
        
        <div class="card">
            <h2>📝 回测日志</h2>
            <div id="status"></div>
            <div id="log"></div>
        </div>
    </div>
    
    <script>
        async function runBacktest() {
            const strategy = document.getElementById('strategy').value;
            const stockCode = document.getElementById('stockCode').value;
            const startDate = document.getElementById('startDate').value;
            const endDate = document.getElementById('endDate').value;
            const initialCash = document.getElementById('initialCash').value;
            
            const status = document.getElementById('status');
            const log = document.getElementById('log');
            
            status.innerHTML = '<span class="status running">运行中...</span>';
            log.textContent = '正在启动回测...\\n';
            
            try {
                const res = await fetch('/api/run_backtest', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        strategy, stockCode, startDate, endDate, initialCash
                    })
                });
                
                const data = await res.json().catch(() => ({}));
                
                if (!res.ok) {
                    status.innerHTML = '<span class="status error">错误</span>';
                    log.textContent = data.error || data.message || ('HTTP ' + res.status);
                    return;
                }
                
                if (data.success) {
                    status.innerHTML = '<span class="status success">回测完成</span>';
                    log.textContent = data.log || '回测完成！';
                } else {
                    status.innerHTML = '<span class="status error">回测失败</span>';
                    log.textContent = data.error || '回测失败';
                }
            } catch (e) {
                status.innerHTML = '<span class="status error">错误</span>';
                log.textContent = '错误: ' + e.message;
            }
        }
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    """主页"""
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/run_backtest", methods=["POST"])
def run_backtest():
    """运行回测 - 使用 AKShare 数据源"""
    try:
        if not request.json:
            return jsonify({"success": False, "error": "请求数据为空"}), 400

        data = request.json
        strategy = data.get("strategy")
        stock_code = data.get("stockCode")
        start_date = data.get("startDate")
        end_date = data.get("endDate")
        initial_cash = data.get("initialCash", "1000000")

        if not strategy or not stock_code or not start_date or not end_date:
            return jsonify({"success": False, "error": "参数不完整"}), 400

        strategy_path = os.path.join("strategies", strategy)
        if not os.path.exists(strategy_path):
            return jsonify({"success": False, "error": f"策略文件不存在: {strategy_path}"}), 404

        log_output = []
        log_output.append("=" * 60)
        log_output.append("🚀 量化回测 - AKShare 数据源")
        log_output.append("=" * 60)
        log_output.append(f"策略: {strategy}")
        log_output.append(f"股票: {stock_code}")
        log_output.append(f"日期: {start_date} 至 {end_date}")
        log_output.append(f"初始资金: {initial_cash}")
        log_output.append("")
        
        # 使用简化的回测脚本
        script = "run_backtest_akshare.py"
        cmd = [
            sys.executable,
            script,
            strategy_path,
            start_date,
            end_date,
            stock_code
        ]
        
        env = os.environ.copy()
        env["STOCK_CODE"] = stock_code
        env["PYTHONPATH"] = os.pathsep.join(sys.path)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                env=env,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            if result.stdout:
                log_output.append(result.stdout)
            
            if result.stderr:
                log_output.append("\n=== 错误信息 ===")
                log_output.append(result.stderr)
            
            if result.returncode == 0:
                log_output.append("\n✅ 回测完成！")
                return jsonify({"success": True, "log": "\n".join(log_output)})
            else:
                log_output.append(f"\n❌ 回测失败 (退出码: {result.returncode})")
                return jsonify({"success": False, "error": "\n".join(log_output)})
                
        except subprocess.TimeoutExpired:
            return jsonify({"success": False, "error": "回测超时（超过5分钟）"})
        except Exception as e:
            return jsonify({"success": False, "error": f"运行回测时出错: {str(e)}\n{traceback.format_exc()}"})

    except Exception as e:
        err_msg = f"服务器错误: {str(e)}\n{traceback.format_exc()}"
        return jsonify({"success": False, "error": err_msg})


if __name__ == "__main__":
    os.makedirs("strategies", exist_ok=True)
    os.makedirs("output", exist_ok=True)
    
    PORT = int(os.environ.get("PORT", 5050))
    print("=" * 60)
    print("🚀 量化交易平台启动中...")
    print(f"访问 http://127.0.0.1:{PORT} 使用平台")
    print("=" * 60)
    print("架构说明:")
    print("  - AKShare: 全品类金融数据供给引擎")
    print("  - RQAlpha: 策略全生命周期执行框架")
    print("  - Web 平台: 用户界面（简化版）")
    print("=" * 60)
    app.run(host="127.0.0.1", port=PORT, debug=True)
