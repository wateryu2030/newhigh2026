#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量化交易平台 Web 界面
整合 AKShare 和 RQAlpha
"""
from flask import Flask, render_template_string, request, jsonify, send_file
import os
import subprocess
import json
from datetime import datetime, timedelta
import glob

_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
app = Flask(__name__, static_folder=_static_dir)

# 注册 API 层（组合回测、TradingView K 线、股票池、机构组合、AI 推荐等）
try:
    from api import register_routes
    register_routes(app)
except Exception as e:
    import traceback
    print("WARNING: API routes not registered (机构组合/AI推荐等将 404):", e)
    traceback.print_exc()

# 添加 CORS 支持（简单版本）
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>量化交易平台 - AKShare + RQAlpha</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0a0e27; color: #e0e0e0; min-height: 100vh; }
    .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
    header { background: #16213e; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
    h1 { color: #0f9; margin-bottom: 8px; }
    .subtitle { color: #888; font-size: 14px; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
    .card { background: #16213e; border-radius: 8px; padding: 20px; border: 1px solid #2a2a4a; }
    .card h2 { color: #0f9; margin-bottom: 16px; font-size: 18px; }
    .form-group { margin-bottom: 16px; }
    label { display: block; color: #aaa; margin-bottom: 6px; font-size: 14px; }
    input, select, textarea { width: 100%; padding: 10px; background: #1a2744; border: 1px solid #2a2a4a; border-radius: 4px; color: #e0e0e0; font-size: 14px; }
    textarea { min-height: 200px; font-family: 'Courier New', monospace; }
    button { background: #0f9; color: #000; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: 600; }
    button:hover { background: #0cc; }
    button:disabled { background: #555; cursor: not-allowed; }
    .ext-action { padding: 8px 14px; background: #1a2744; border: 1px solid #2a2a4a; color: #0f9; border-radius: 4px; cursor: pointer; transition: opacity .2s; }
    .ext-action:hover:not(:disabled) { border-color: #0f9; }
    .ext-action.disabled { opacity: .5; cursor: not-allowed; color: #666; }
    .strategy-list { list-style: none; }
    .strategy-item { padding: 12px; background: #1a2744; margin-bottom: 8px; border-radius: 4px; cursor: pointer; border: 1px solid #2a2a4a; display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
    .strategy-item:hover { border-color: #0f9; }
    .strategy-item.active { border-color: #0f9; background: #1f3a5f; }
    .strategy-item-content { flex: 1; min-width: 0; }
    .strategy-desc { font-size: 12px; color: #888; display: block; margin-top: 4px; line-height: 1.3; }
    .strategy-delete-btn { flex-shrink: 0; width: 22px; height: 22px; padding: 0; line-height: 20px; font-size: 16px; color: #888; background: transparent; border: 1px solid #444; border-radius: 4px; cursor: pointer; }
    .strategy-delete-btn:hover { color: #f55; border-color: #f55; }
    .btn-clear { width: 32px; height: 36px; padding: 0; font-size: 14px; color: #888; background: #1a2744; border: 1px solid #2a2a4a; border-radius: 4px; cursor: pointer; flex-shrink: 0; }
    .btn-clear:hover { color: #f55; border-color: #666; }
    .log { background: #0a0e27; padding: 16px; border-radius: 4px; font-family: 'Courier New', monospace; font-size: 12px; max-height: 400px; overflow-y: auto; white-space: pre-wrap; color: #0f9; border: 1px solid #2a2a4a; }
    .status { padding: 8px 12px; border-radius: 4px; display: inline-block; margin-top: 8px; }
    .status.running { background: #0f9; color: #000; }
    .status.success { background: #0f9; color: #000; }
    .status.error { background: #f55; color: #fff; }
    .full-width { grid-column: 1 / -1; }
    @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }
    @media (max-width: 900px) { .result-layout { grid-template-columns: 1fr !important; } }
    .tabs { display: flex; gap: 0; margin-bottom: 16px; border-bottom: 1px solid #2a2a4a; }
    .tab-btn { padding: 12px 24px; background: transparent; color: #888; border: none; border-bottom: 3px solid transparent; cursor: pointer; font-size: 15px; font-weight: 600; }
    .tab-btn:hover { color: #0f9; }
    .tab-btn.active { color: #0f9; border-bottom-color: #0f9; }
    .tab-panel { display: none; }
    .tab-panel.active { display: block; }
    .badge-self { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; background: #1a2744; color: #0f9; border: 1px solid #0f9; margin-left: 6px; }
    .badge-ai { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; background: #2a1a4a; color: #c9f; border: 1px solid #c9f; margin-left: 6px; }
    .ai-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
    @media (max-width: 1000px) { .ai-cards { grid-template-columns: 1fr; } }
    /* === 回测布局：侧栏 + 主区（参考 Backtrader/OpenBB） === */
    .layout-backtest { display: flex; gap: 20px; margin-bottom: 20px; align-items: stretch; }
    .sidebar { width: 280px; flex-shrink: 0; display: flex; flex-direction: column; gap: 16px; }
    .sidebar .card { padding: 16px; }
    .sidebar .card h2 { font-size: 15px; margin-bottom: 12px; }
    .sidebar .form-group { margin-bottom: 12px; }
    .sidebar .form-group label { font-size: 12px; }
    .sidebar-row { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; }
    .sidebar-row label { flex: 0 0 60px; margin-bottom: 0; font-size: 12px; }
    .sidebar-row input, .sidebar-row select { flex: 1; padding: 8px 10px; font-size: 13px; }
    .main-backtest { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 16px; }
    .btn-run { width: 100%; padding: 14px; font-size: 16px; margin-top: 4px; margin-bottom: 8px; }
    .progress-wrap { height: 6px; background: #1a2744; border-radius: 3px; overflow: hidden; margin-bottom: 12px; }
    .progress-wrap .bar { height: 100%; background: #0f9; width: 0%; transition: width .2s; }
    .strategy-list-compact { max-height: 200px; overflow-y: auto; }
    .strategy-item { padding: 10px; font-size: 13px; }
    .strategy-item .strategy-desc { font-size: 11px; }
    .summary-sidebar { font-size: 12px; }
    .summary-sidebar .row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #2a2a4a; }
    .summary-sidebar .row:last-child { border-bottom: none; }
    .summary-sidebar .label { color: #888; }
    .summary-sidebar .value { font-weight: 600; }
    .summary-sidebar .value.positive { color: #0f9; }
    .summary-sidebar .value.negative { color: #f55; }
    .core-metrics-bar { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
    .core-metric { background: #16213e; border: 1px solid #2a2a4a; border-radius: 8px; padding: 14px 16px; text-align: center; }
    .core-metric .name { font-size: 12px; color: #888; margin-bottom: 4px; }
    .core-metric .num { font-size: 22px; font-weight: 700; }
    .core-metric .num.positive { color: #0f9; }
    .core-metric .num.negative { color: #f55; }
    .core-metric .num.neutral { color: #e0e0e0; }
    .result-chart-wrap { min-height: 280px; }
    .scan-progress-wrap { margin: 8px 0; }
    .scan-progress-bar { height: 8px; background: #1a2744; border-radius: 4px; overflow: hidden; }
    .scan-progress-fill { height: 100%; background: #0f9; transition: width 0.2s ease; }
    .scan-progress-msg { font-size: 12px; color: #888; margin-top: 6px; }
    @media (max-width: 900px) { .layout-backtest { flex-direction: column; } .sidebar { width: 100%; } .core-metrics-bar { grid-template-columns: repeat(2, 1fr); } }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>量化交易平台</h1>
      <div class="subtitle">策略回测 · 数据：DuckDB / AKShare | 访问 http://127.0.0.1:5050</div>
    </header>
    
    <div class="tabs">
      <button type="button" class="tab-btn active" id="tabSelf" data-tab="self">自己实测</button>
      <button type="button" class="tab-btn" id="tabAi" data-tab="ai">AI 推荐</button>
    </div>
    
    <div id="panelSelf" class="tab-panel active">
    <div class="layout-backtest">
      <aside class="sidebar">
        <div class="card">
          <h2>策略</h2>
          <input type="text" id="strategyFile" readonly placeholder="请从下方选择" style="background:#1a2744;padding:8px;margin-bottom:10px;font-size:13px;cursor:default;">
          <ul class="strategy-list strategy-list-compact" id="strategyList"></ul>
          <button type="button" onclick="loadStrategies()" style="margin-top:8px;padding:6px 12px;font-size:12px;">刷新列表</button>
        </div>
        <div class="card">
          <h2>回测配置</h2>
          <div class="form-group">
            <label>股票</label>
            <div style="display:flex;gap:6px;align-items:center;">
              <input type="text" id="customStockCode" placeholder="600519 / 000001" style="flex:1;padding:8px 10px;font-size:13px;">
              <button type="button" class="btn-clear" id="clearStockBtn" title="清空">✕</button>
            </div>
            <select id="stockCode" style="padding:8px 10px;font-size:13px;margin-top:6px;">
              <option value="">或从列表选</option>
            </select>
          </div>
          <div class="sidebar-row">
            <label>开始</label>
            <input type="date" id="startDate" value="{{ default_start }}">
          </div>
          <div class="sidebar-row">
            <label>结束</label>
            <input type="date" id="endDate" value="{{ default_end }}">
          </div>
          <div class="form-group">
            <label>初始资金（元）</label>
            <input type="number" id="initialCash" value="1000000" step="10000" style="padding:8px 10px;">
          </div>
          <div style="display:flex;gap:8px;">
            <div class="form-group" style="flex:1;">
              <label>周期</label>
              <select id="timeframe"><option value="D">日线</option><option value="W">周线</option><option value="M">月线</option></select>
            </div>
            <div class="form-group" style="flex:1;">
              <label>数据源</label>
              <select id="dataSource"><option value="database">数据库</option><option value="akshare">AKShare</option></select>
            </div>
          </div>
          <button type="button" onclick="runBacktest()" id="runBtn" class="btn-run">运行回测</button>
          <div class="progress-wrap" id="progressWrap" style="display:none;"><div class="bar" id="progressBar"></div></div>
          <div style="display:flex;flex-wrap:wrap;gap:6px;">
            <button type="button" onclick="syncStockData()" style="padding:6px 10px;font-size:11px;">同步股票</button>
            <button type="button" onclick="scanMarket()" id="scanBtn" class="ext-action" style="padding:6px 10px;font-size:11px;">扫描</button>
            <button type="button" onclick="optimizeParams()" id="optimizeBtn" class="ext-action" style="padding:6px 10px;font-size:11px;">优化</button>
            <button type="button" onclick="runPortfolioBacktest()" id="portfolioBtn" class="ext-action" style="padding:6px 10px;font-size:11px;">组合</button>
          </div>
          <div id="actionHint" style="font-size:11px;color:#666;margin-top:8px;min-height:16px;"></div>
          <div id="status"></div>
        </div>
        <div class="card" id="sidebarSummaryCard" style="display:none;">
          <h2>策略摘要</h2>
          <div class="summary-sidebar" id="sidebarSummary">
            <div class="row"><span class="label">期末资金</span><span class="value" id="ssCash">—</span></div>
            <div class="row"><span class="label">总收益</span><span class="value" id="ssProfit">—</span></div>
            <div class="row"><span class="label">交易次数</span><span class="value" id="ssTrades">—</span></div>
            <div class="row"><span class="label">盈利/亏损</span><span class="value" id="ssWonLost">—</span></div>
          </div>
        </div>
      </aside>
      <main class="main-backtest">
    
    <div class="card full-width" id="resultCard" style="display: none;">
      <h2>回测结果</h2>
      <div id="resultStrategyInfo" style="margin-bottom: 12px; padding: 8px 12px; background: #1a2744; border-radius: 4px; color: #888; font-size: 13px; display: none;"></div>
      <div id="coreMetricsBar" class="core-metrics-bar"></div>
      <div style="display: grid; grid-template-columns: 1fr 300px; gap: 20px; align-items: start;" class="result-layout">
        <div>
      <div id="resultSummary" style="display: none;"></div>
      <div id="resultCurve" class="result-chart-wrap" style="height: 280px; background: #0a0e27; border-radius: 6px; border: 1px solid #2a2a4a;"></div>
        <div id="resultCockpit" style="display: none; margin-top: 20px;">
        <h3 style="color: #0f9; margin-bottom: 12px;">📈 决策驾驶舱</h3>
        <div id="resultCockpitStats" style="margin-bottom: 12px; padding: 8px 12px; background: #1a2744; border-radius: 4px; color: #888; font-size: 13px; display: none;"></div>
        <div id="resultKline" style="height: 320px; background: #0a0e27; border-radius: 4px; border: 1px solid #2a2a4a;"></div>
        <div id="resultFutureTrend" style="margin-top: 12px; padding: 12px; background: #1a2744; border-radius: 4px; display: none;">
          <div style="color: #888; font-size: 12px; margin-bottom: 8px;">未来趋势（概率，非预测）</div>
          <div id="resultFutureProb" style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;"></div>
          <div id="resultFutureRange" style="margin-top: 8px; color: #0f9; font-size: 13px;"></div>
          <div style="margin-top: 12px;">
            <button type="button" id="btnFuture5Day" style="display: none; padding: 6px 14px; font-size: 12px; color: #0f9; background: transparent; border: 1px solid #0f9; border-radius: 4px; cursor: pointer;">查看未来5日走势与买卖点</button>
          </div>
          <div id="resultFuture5Day" style="display: none; margin-top: 12px; padding: 12px; background: #0a0e27; border-radius: 4px; border: 1px solid #2a2a4a;">
            <div id="resultFuture5DayChart" style="height: 180px;"></div>
            <div id="resultFuture5DaySignals" style="margin-top: 12px; font-size: 13px; color: #ccc;"></div>
          </div>
        </div>
        <div id="resultCurveCompare" style="height: 220px; margin-top: 12px; background: #0a0e27; border-radius: 4px; border: 1px solid #2a2a4a;"></div>
        <div id="resultSignalList" style="margin-top: 12px; display: flex; flex-wrap: wrap; gap: 8px;"></div>
        <div id="resultSignalReason" style="margin-top: 12px; padding: 12px; background: #1a2744; border-radius: 4px; min-height: 50px; color: #888; font-size: 13px;">点击下方买卖信号可查看原因</div>
      </div>
        </div>
        <div id="resultDecisionPanel" style="background: #1a2744; border-radius: 8px; padding: 16px; border: 1px solid #2a2a4a; position: sticky; top: 12px;">
          <h3 style="color: #0f9; font-size: 14px; margin-bottom: 12px;">📋 决策面板</h3>
          <div id="decisionCurrentPrice" style="color: #888; font-size: 12px; margin-bottom: 8px;">当前价格: —</div>
          <div id="decisionSignal" style="margin-bottom: 8px; font-size: 13px;"><span style="color: #888;">最新信号</span> <span id="decisionSignalValue" style="color: #fc0;">HOLD</span></div>
          <div id="decisionTrend" style="color: #888; font-size: 12px; margin-bottom: 8px;">趋势: —</div>
          <div id="decisionScore" style="margin-bottom: 8px;"><span style="color: #888; font-size: 12px;">策略评分</span> <span id="decisionScoreValue" style="color: #0f9; font-size: 18px;">—</span> <span id="decisionGradeValue" style="color: #888; font-size: 12px;"></span></div>
          <div id="decisionSuggestion" style="color: #888; font-size: 12px;">建议: 运行回测后显示</div>
        </div>
      </div>
    </div>
    
    <div class="card full-width">
      <h2>回测日志</h2>
      <div class="log" id="log">选择策略与股票后点击「运行回测」</div>
    </div>
    
    <div class="card full-width">
      <h2>策略代码编辑器</h2>
      <div class="form-group">
        <label>策略文件路径</label>
        <input type="text" id="editPath" placeholder="strategies/my_strategy.py">
      </div>
      <div class="form-group">
        <label>策略代码</label>
        <textarea id="strategyCode" placeholder="from rqalpha.apis import *&#10;def init(context):&#10;    context.s1 = &quot;000001.XSHE&quot;&#10;def handle_bar(context, bar_dict):&#10;    pass"></textarea>
      </div>
      <button onclick="saveStrategy()">保存策略</button>
      <button id="loadBtn" style="margin-left: 8px;">加载策略</button>
    </div>
    </main>
    </div>
    </div>
    
    <div id="panelAi" class="tab-panel">
      <p style="color: #888; font-size: 13px; margin-bottom: 12px;">以下为 AI 生成/推荐的组合、选股与资金分配，仅供参考，不构成投资建议。</p>
      <div class="card" style="margin-bottom: 16px; padding: 14px 18px; background: #1a2744; border: 1px solid #2a2a4a;">
        <div style="font-size: 12px; color: #0f9; margin-bottom: 8px;">使用顺序</div>
        <div style="font-size: 13px; color: #aaa;">① 确保本地数据充足（下方「数据状态」≥5000 只）→ ② 刷新市场状态 / 运行专业扫描 → ③ 加载机构组合或 AI 推荐列表 → ④ 可选：基金经理再平衡、交易建议、导出</div>
      </div>
      <div class="card" style="margin-bottom: 20px;">
        <h2>数据状态</h2>
        <p style="color: #888; font-size: 13px; margin-bottom: 10px;">AI 推荐与专业扫描均使用<strong>本地数据库</strong>，不实时拉取网络。建议先做全量 A 股同步，保证 5000+ 只个股日线已写入。</p>
        <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 12px;">
          <div id="dbStatsText" style="font-size: 14px; color: #e0e0e0;">加载中…</div>
          <button type="button" class="ext-action" id="btnRefreshDbStats" style="padding: 6px 12px;">刷新</button>
          <button type="button" class="ext-action" id="btnSyncAllAStocks" style="padding: 6px 12px;">全量 A 股同步</button>
        </div>
        <div id="dbStatsHint" style="margin-top: 8px; font-size: 12px; color: #888;"></div>
      </div>
      <div class="form-group" style="margin-bottom: 12px;">
        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
          <input type="checkbox" id="concentrateModeCheckbox" style="width: 18px; height: 18px; accent-color: #0f9;" />
          <span>短期集中交易</span>
        </label>
        <span style="color: #666; font-size: 12px; display: block; margin-top: 4px;">少品种、大仓位；开启后机构组合/交易建议最多约 10 只、单只上限 15%。</span>
      </div>
      <div class="form-group" style="margin-bottom: 16px;">
        <label>筛选描述（可选）</label>
        <input type="text" id="nlFilterInput" placeholder="如：低估值高分红、科技龙头、消费白马" style="width: 100%; max-width: 480px; padding: 8px 12px; background: #1a2744; border: 1px solid #2a2a4a; border-radius: 4px; color: #e0e0e0; font-size: 14px;" />
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px;">
        <div class="card">
          <h2>市场状态</h2>
          <p style="color: #888; font-size: 13px; margin-bottom: 8px;">当前市场牛熊/震荡（基于板块强度）。</p>
          <button type="button" class="ext-action" id="btnLoadMarketRegime">刷新市场状态</button>
          <div id="marketRegimeContent" style="margin-top: 12px; padding: 12px; background: #1a2744; border-radius: 4px; border: 1px solid #2a2a4a; min-height: 50px; color: #888; font-size: 13px;">点击刷新</div>
        </div>
        <div class="card">
          <h2>专业扫描</h2>
          <p style="color: #888; font-size: 13px; margin-bottom: 8px;">全市场→形态→热点→风险预算→AI 排序，输出买点概率与建议仓位（仅用本地数据）。</p>
          <button type="button" class="ext-action" id="btnProfessionalScan">运行专业扫描</button>
          <div id="professionalScanContent" style="margin-top: 12px; padding: 12px; background: #1a2744; border-radius: 4px; border: 1px solid #2a2a4a; min-height: 50px; color: #888; font-size: 13px;">点击运行</div>
        </div>
      </div>
      <div style="font-size: 12px; color: #0f9; margin-bottom: 8px;">推荐与组合</div>
      <div class="ai-cards">
        <div class="card" id="resultPortfolioCard">
          <h2>机构组合结果</h2>
          <p style="color: #888; font-size: 13px; margin-bottom: 12px;">多策略信号 + 风控 → 目标仓位与订单。</p>
          <button type="button" class="ext-action" id="btnLoadPortfolio">加载机构组合</button>
          <div id="resultPortfolioContent" style="margin-top: 16px; padding: 12px; background: #1a2744; border-radius: 4px; border: 1px solid #2a2a4a; min-height: 80px; color: #888; font-size: 13px;">点击加载</div>
        </div>
        <div class="card" id="resultAiRecommendCard">
          <h2>AI 推荐列表</h2>
          <p style="color: #888; font-size: 13px; margin-bottom: 12px;">当日 AI 选股 Top N（需已训练模型 + 本地数据）。</p>
          <button type="button" class="ext-action" id="btnLoadAiRecommend">加载 AI 推荐</button>
          <div id="resultAiRecommendContent" style="margin-top: 16px; padding: 12px; background: #1a2744; border-radius: 4px; border: 1px solid #2a2a4a; min-height: 80px; color: #888; font-size: 13px;">点击加载</div>
        </div>
        <div class="card" id="resultFundManagerCard">
          <h2>基金经理再平衡</h2>
          <p style="color: #888; font-size: 13px; margin-bottom: 12px;">按各策略夏普/回撤与风险预算分配资金，回撤超限自动降仓。</p>
          <button type="button" class="ext-action" id="btnFundManagerRebalance">执行再平衡</button>
          <button type="button" class="ext-action" id="btnFundManagerStrategyStocks" style="display: none; margin-left: 8px;">各策略建议股票</button>
          <div id="resultFundManagerContent" style="margin-top: 16px; padding: 12px; background: #1a2744; border-radius: 4px; border: 1px solid #2a2a4a; min-height: 80px; color: #888; font-size: 13px;">点击执行</div>
        </div>
        <div class="card" id="resultAiTradingAdviceCard">
          <h2>AI 交易建议</h2>
          <p style="color: #888; font-size: 13px; margin-bottom: 12px;">买卖时点与仓位：建议价位、止损、止盈。</p>
          <button type="button" class="ext-action" id="btnLoadAiTradingAdvice">加载交易建议</button>
          <div id="resultAiTradingAdviceContent" style="margin-top: 16px; padding: 12px; background: #1a2744; border-radius: 4px; border: 1px solid #2a2a4a; min-height: 80px; color: #888; font-size: 13px;">点击加载</div>
        </div>
      </div>
      <div class="card full-width" style="margin-top: 20px;">
        <h2>📤 导出与发送 <span class="badge-ai">AI 推荐</span></h2>
        <p style="color: #888; font-size: 13px; margin-bottom: 12px;">将上方已加载的结果导出为 PDF 或发送到飞书群/指定客户。</p>
        <div style="display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin-bottom: 12px;">
          <button type="button" class="ext-action" id="btnExportPdf">📄 导出 PDF</button>
          <button type="button" class="ext-action" id="btnSendFeishu">📱 发送到飞书</button>
          <input type="text" id="feishuWebhookInput" placeholder="飞书 webhook（可选，也可设环境变量 FEISHU_WEBHOOK_URL）" style="flex: 1; min-width: 200px; padding: 8px 12px; background: #1a2744; border: 1px solid #2a2a4a; border-radius: 4px; color: #e0e0e0; font-size: 13px;" />
          <input type="text" id="feishuAtUserIdInput" placeholder="@用户 user_id（可选）" style="width: 140px; padding: 8px 12px; background: #1a2744; border: 1px solid #2a2a4a; border-radius: 4px; color: #e0e0e0; font-size: 13px;" />
        </div>
        <div id="exportSendStatus" style="font-size: 12px; color: #888;"></div>
      </div>
    </div>
  </div>
  
  <script src="/static/app.js?v={{ version }}"></script>
</body>
</html>
"""


@app.route("/health")
def health():
    """健康检查，用于确认服务已启动"""
    return jsonify({"status": "ok", "service": "astock-web-platform"})


@app.route("/")
def index():
    default_start = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    default_end = datetime.now().strftime("%Y-%m-%d")
    version = datetime.now().strftime("%Y%m%d%H%M")
    return render_template_string(HTML_TEMPLATE, default_start=default_start, default_end=default_end, version=version)


def _load_strategies_meta():
    """加载策略说明元数据"""
    meta_path = os.path.join("strategies", "strategies_meta.json")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


# 插件策略 id 列表（多周期回测）
PLUGIN_STRATEGY_IDS = [
    {"id": "ma_cross", "name": "MA均线", "description": "MA5/MA20 金叉死叉", "order": 0},
    {"id": "rsi", "name": "RSI", "description": "RSI 超买超卖", "order": 1},
    {"id": "macd", "name": "MACD", "description": "MACD 金叉死叉", "order": 2},
    {"id": "kdj", "name": "KDJ", "description": "KDJ 金叉/超卖买入", "order": 2.5},
    {"id": "breakout", "name": "Breakout突破", "description": "N 日高低点突破", "order": 3},
    {"id": "swing_newhigh", "name": "波段新高", "description": "新高突破+均线趋势+放量+市场过滤", "order": 3.5},
]


@app.route("/api/strategies")
def list_strategies():
    """列出所有策略：插件策略 + 策略文件"""
    try:
        strategies_dir = "strategies"
        if not os.path.exists(strategies_dir):
            os.makedirs(strategies_dir)

        strategies = []
        for p in PLUGIN_STRATEGY_IDS:
            strategies.append({
                "file": p["id"],
                "name": p["name"],
                "description": p["description"],
                "order": p["order"],
                "plugin": True,
            })

        meta = _load_strategies_meta()
        _exclude = {
            "__init__.py", "utils.py", "base.py", "ma_cross.py", "rsi_strategy.py",
            "macd_strategy.py", "kdj_strategy.py", "breakout.py",
            "market_regime.py", "stock_filter.py",
            "swing_newhigh.py",  # 已注册为插件策略
        }
        for f in sorted(glob.glob(os.path.join(strategies_dir, "*.py"))):
            rel_path = os.path.relpath(f, strategies_dir).replace(os.sep, "/")
            if rel_path in _exclude or rel_path.startswith(".tmp_"):
                continue
            info = meta.get(rel_path, {})
            strategies.append({
                "file": rel_path,
                "name": info.get("name", rel_path),
                "description": info.get("description", ""),
                "order": info.get("order", 99),
                "plugin": False,
            })

        strategies.sort(key=lambda x: (x["order"], x["file"]))
        return jsonify({"strategies": strategies})
    except Exception as e:
        return jsonify({"strategies": [], "error": str(e)}), 500


# 不允许删除的 core 策略文件
_STRATEGY_DELETE_PROTECTED = {
    "__init__.py", "utils.py", "base.py", "ma_cross.py", "rsi_strategy.py",
    "macd_strategy.py", "kdj_strategy.py", "breakout.py",
    "market_regime.py", "stock_filter.py", "swing_newhigh.py",
}


@app.route("/api/strategies/<path:filepath>", methods=["DELETE"])
def delete_strategy(filepath):
    """删除策略文件（仅限非插件、非 core 的文件策略）。"""
    if not filepath or ".." in filepath or filepath.startswith("/"):
        return jsonify({"success": False, "error": "无效的文件路径"}), 400
    basename = os.path.basename(filepath)
    if basename in _STRATEGY_DELETE_PROTECTED or basename.startswith(".tmp_"):
        return jsonify({"success": False, "error": "该策略为系统内置，不可删除"}), 403
    strategies_dir = "strategies"
    full_path = os.path.normpath(os.path.join(strategies_dir, filepath))
    if not full_path.startswith(strategies_dir) or ".." in full_path:
        return jsonify({"success": False, "error": "路径越界"}), 400
    if not os.path.exists(full_path):
        return jsonify({"success": False, "error": "文件不存在"}), 404
    if not full_path.endswith(".py"):
        return jsonify({"success": False, "error": "仅支持删除 .py 策略文件"}), 400
    try:
        os.remove(full_path)
        return jsonify({"success": True, "message": "已删除策略"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/stocks")
def list_stocks():
    """列出数据库中的所有股票"""
    try:
        from database.duckdb_backend import get_db_backend
        db = get_db_backend()
        stocks = db.get_stocks()
        
        stock_list = []
        for order_book_id, symbol, name in stocks:
            stock_list.append({
                "order_book_id": order_book_id,
                "symbol": symbol,
                "name": name or symbol
            })
        
        return jsonify({"stocks": stock_list})
    except Exception as e:
        # 如果数据库不存在或出错，返回空列表
        return jsonify({"stocks": [], "error": str(e)})


@app.route("/api/kline")
def api_kline():
    """K 线数据，供前端 TradingView 图表。数据来自已导入的数据库（get_db_backend）。GET ?symbol=000001.XSHE&start=2024-01-01&end=2025-01-01"""
    try:
        symbol = request.args.get("symbol", "").strip()
        start = request.args.get("start", "").strip()[:10]
        end = request.args.get("end", "").strip()[:10]
        if not symbol or not start or not end:
            return jsonify([])
        from database.duckdb_backend import get_db_backend
        db = get_db_backend()
        if not getattr(db, "db_path", None) or not os.path.exists(getattr(db, "db_path", "")):
            return jsonify([])
        df = db.get_daily_bars(symbol, start, end)
        if (df is None or len(df) == 0) and "." not in symbol and len(symbol) == 6 and symbol.isdigit():
            for suf in [".XSHE", ".XSHG"]:
                df = db.get_daily_bars(symbol + suf, start, end)
                if df is not None and len(df) > 0:
                    symbol = symbol + suf
                    break
        if df is None or len(df) == 0:
            return jsonify([])
        df = df.reset_index()
        df["time"] = df.get("trade_date", df.index.astype(str)).astype(str).str[:10]
        rows = []
        for _, r in df.iterrows():
            rows.append({
                "time": r.get("time", ""),
                "open": float(r.get("open", 0)),
                "high": float(r.get("high", 0)),
                "low": float(r.get("low", 0)),
                "close": float(r.get("close", 0)),
                "volume": float(r.get("volume", 0)) if r.get("volume") is not None else None,
            })
        return jsonify(rows)
    except Exception as e:
        return jsonify([])


@app.route("/api/signals")
def api_signals():
    """买卖点信号，供前端标记。GET ?symbol=000001.XSHE&strategy=ma_cross|rsi|macd|kdj|breakout（可选，默认 ma_cross）。数据来自已导入的数据库。"""
    try:
        symbol = request.args.get("symbol", "").strip()
        strategy_id = (request.args.get("strategy") or "ma_cross").strip().lower()
        if not symbol:
            return jsonify({"signals": []})
        from database.duckdb_backend import get_db_backend
        from strategies import get_plugin_strategy
        from core.timeframe import resample_kline, normalize_timeframe
        db = get_db_backend()
        if not getattr(db, "db_path", None) or not os.path.exists(getattr(db, "db_path", "")):
            return jsonify({"signals": []})
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        df = db.get_daily_bars(symbol, start_date, end_date)
        if df is None or len(df) < 20:
            return jsonify({"signals": []})
        df = resample_kline(df, normalize_timeframe("D"))
        if "date" not in df.columns and df.index is not None:
            df["date"] = df.index.astype(str).str[:10]
        strategy = get_plugin_strategy(strategy_id) or get_plugin_strategy("ma_cross") or get_plugin_strategy("rsi") or get_plugin_strategy("macd")
        if strategy is None:
            return jsonify({"signals": []})
        signals = strategy.generate_signals(df)
        out = []
        for s in (signals or []):
            out.append({
                "date": s.get("date", ""),
                "type": s.get("type", "BUY"),
                "price": float(s.get("price", 0)),
                "reason": s.get("reason", ""),
            })
        return jsonify({"signals": out})
    except Exception as e:
        return jsonify({"signals": []})


@app.route("/api/ai_score")
def api_ai_score():
    """AI 评分与建议。GET ?symbol=000001.XSHE"""
    try:
        symbol = request.args.get("symbol", "").strip()
        if not symbol:
            return jsonify({"symbol": "", "score": 50, "suggestion": "HOLD"})
        from database.duckdb_backend import get_db_backend
        from data.data_loader import load_kline
        db = get_db_backend()
        end = datetime.now().date()
        start = (end - timedelta(days=250)).strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")
        df = load_kline(symbol.replace(".XSHG", "").replace(".XSHE", ""), start, end_str, source="database")
        if df is None or len(df) < 60:
            return jsonify({"symbol": symbol, "score": 50, "suggestion": "HOLD"})
        try:
            from ai_models.model_manager import ModelManager
            mm = ModelManager()
            key = symbol if "." in symbol else (symbol + ".XSHG" if symbol.startswith("6") else symbol + ".XSHE")
            scores = mm.predict({key: df})
            if scores is not None and not scores.empty and "symbol" in scores.columns:
                row = scores[scores["symbol"].astype(str) == key].iloc[0] if len(scores) else None
                if row is not None:
                    sc = float(row.get("score", 0.5)) * 100
                    sug = "BUY" if sc >= 60 else "SELL" if sc < 40 else "HOLD"
                    return jsonify({
                        "symbol": symbol,
                        "score": round(sc, 1),
                        "suggestion": sug,
                        "position_pct": 10,
                        "risk_level": "NORMAL",
                        "latest_signal": sug,
                    })
        except Exception:
            pass
        return jsonify({"symbol": symbol, "score": 50, "suggestion": "HOLD"})
    except Exception as e:
        return jsonify({"symbol": "", "score": 50, "suggestion": "HOLD"})


@app.route("/api/backtest", methods=["POST"])
def api_backtest():
    """回测接口，供策略实验室。POST body: strategy, symbol, start, end"""
    try:
        data = request.json or {}
        strategy = (data.get("strategy") or "ma_cross").strip()
        symbol = (data.get("symbol") or "").strip()
        start = (data.get("start") or "").strip()[:10]
        end = (data.get("end") or "").strip()[:10]
        if not symbol or not start or not end:
            return jsonify({"error": "缺少 symbol/start/end"}), 400
        from database.duckdb_backend import get_db_backend
        from strategies import get_plugin_strategy
        from core.timeframe import resample_kline, normalize_timeframe
        db = get_db_backend()
        strategy_obj = get_plugin_strategy(strategy)
        if strategy_obj is None:
            return jsonify({"error": "策略不存在"}), 400
        df = db.get_daily_bars(symbol, start, end)
        if (df is None or len(df) < 20) and "." not in symbol and len(symbol) == 6 and symbol.isdigit():
            for suf in [".XSHE", ".XSHG"]:
                df = db.get_daily_bars(symbol + suf, start, end)
                if df is not None and len(df) >= 20:
                    symbol = symbol + suf
                    break
        if df is None or len(df) < 20:
            return jsonify({"equity_curve": [], "total_return": 0, "max_drawdown": 0, "sharpe_ratio": 0, "trades": [], "error": "标的无数据或数据不足，请检查代码与日期范围"})
        df = resample_kline(df, normalize_timeframe("D"))
        if "date" not in df.columns and df.index is not None:
            df["date"] = df.index.astype(str).str[:10]
        signals = strategy_obj.generate_signals(df)
        if not signals:
            return jsonify({"equity_curve": [], "total_return": 0, "max_drawdown": 0, "sharpe_ratio": 0, "trades": []})
        equity = 1.0
        curve = []
        trades = []
        for s in signals:
            d = s.get("date", "")
            p = float(s.get("price", 0))
            t = s.get("type", "BUY")
            equity = equity * (1 + (p / 100.0 if t == "BUY" else -p / 100.0))
            curve.append({"date": d, "value": equity * 1000000})
            trades.append({"date": d, "type": t, "price": p})
        total_return = (equity - 1.0) if curve else 0
        vals = [c["value"] for c in curve]
        peak = vals[0] if vals else 1
        max_dd = 0
        for v in vals:
            if v > peak:
                peak = v
            dd = (peak - v) / peak if peak else 0
            if dd > max_dd:
                max_dd = dd
        return jsonify({
            "equity_curve": curve,
            "total_return": total_return,
            "max_drawdown": max_dd,
            "sharpe_ratio": 0.5,
            "trades": trades,
            "monthly_heatmap": [],
        })
    except Exception as e:
        return jsonify({"error": str(e), "equity_curve": [], "trades": []}), 500


@app.route("/api/scan")
def api_scan_get():
    """市场扫描 GET，供前端扫描器。?mode=breakout|strong|ai"""
    try:
        mode = request.args.get("mode", "breakout").strip().lower()
        from scanner import scan_market_portfolio
        from scanner.scanner_pipeline import run_professional_scan
        # 引用既有策略：breakout=突破策略, strong=RSI强势, 其他=均线
        if mode == "breakout":
            strategies = [{"strategy_id": "breakout", "weight": 1.0}]
        elif mode == "strong":
            strategies = [{"strategy_id": "rsi", "weight": 1.0}]
        else:
            strategies = [{"strategy_id": "ma_cross", "weight": 1.0}]
        if mode == "ai":
            results = run_professional_scan(top_n=50, stock_limit=300, use_ai_rank=True)
        else:
            raw = scan_market_portfolio(strategies=strategies, timeframe="D", limit=300)
            results = [{"symbol": r.get("symbol", ""), "name": r.get("name", ""), "signal": r.get("signal"), "price": r.get("price"), "reason": r.get("reason", "")} for r in raw]
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"results": [], "error": str(e)})


@app.route("/api/sync_stock", methods=["POST"])
def sync_stock():
    """同步股票数据到数据库"""
    try:
        if not request.json:
            return jsonify({"success": False, "error": "请求数据为空"}), 400
        
        data = request.json
        symbol = data.get("symbol")
        days = data.get("days", 365)
        
        if not symbol:
            return jsonify({"success": False, "error": "请提供股票代码"}), 400
        
        from database.data_fetcher import DataFetcher
        fetcher = DataFetcher()
        
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
        
        success = fetcher.fetch_stock_data(symbol, start_date, end_date)
        
        if success:
            return jsonify({"success": True, "message": f"成功同步 {symbol} 的数据"})
        else:
            return jsonify({"success": False, "error": f"同步 {symbol} 数据失败"}), 500
            
    except Exception as e:
        import traceback
        return jsonify({"success": False, "error": f"同步失败: {str(e)}\n{traceback.format_exc()}"}), 500


@app.route("/api/db_stats", methods=["GET"])
def db_stats():
    """返回当前数据库股票数、日线数，供前端显示与判断是否需全量同步。"""
    try:
        from database.duckdb_backend import get_db_backend
        db = get_db_backend()
        path = getattr(db, "db_path", None)
        if not path:
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "astock.db")
        if not os.path.exists(path):
            return jsonify({"stocks": 0, "daily_bars": 0, "backend": "none"})
        try:
            stocks = db.get_stocks()
            n_stocks = len(stocks) if stocks else 0
        except Exception:
            n_stocks = 0
        n_bars = 0
        if path.endswith(".duckdb"):
            try:
                if hasattr(db, "get_daily_bars_count"):
                    n_bars = db.get_daily_bars_count()
                else:
                    import duckdb
                    conn = duckdb.connect(path, read_only=True)
                    r = conn.execute("SELECT COUNT(*) FROM daily_bars").fetchone()
                    n_bars = int(r[0]) if r else 0
                    conn.close()
            except Exception:
                pass
            backend = "duckdb"
        else:
            try:
                import sqlite3
                conn = sqlite3.connect(path)
                r = conn.execute("SELECT COUNT(*) FROM daily_bars").fetchone()
                n_bars = int(r[0]) if r else 0
                conn.close()
            except Exception:
                pass
            backend = "sqlite"
        return jsonify({"stocks": n_stocks, "daily_bars": n_bars, "backend": backend})
    except Exception as e:
        return jsonify({"stocks": 0, "daily_bars": 0, "backend": "none", "error": str(e)})


@app.route("/api/sync_all_a_stocks", methods=["POST"])
def sync_all_a_stocks():
    """全量 A 股同步：后台拉取沪深京全部股票日线写入数据库（DuckDB/SQLite），支持断点续传。"""
    import threading
    data = request.json or {}
    start_date = (data.get("startDate") or "").replace("-", "")[:8]
    end_date = (data.get("endDate") or "").replace("-", "")[:8]
    if not start_date or len(start_date) != 8:
        start_date = (datetime.now() - timedelta(days=365 * 2)).strftime("%Y%m%d")
    if not end_date or len(end_date) != 8:
        end_date = datetime.now().strftime("%Y%m%d")
    skip_existing = data.get("skip_existing", True)

    def _run():
        try:
            from database.data_fetcher import DataFetcher
            fetcher = DataFetcher()
            n = fetcher.fetch_all_a_stocks(
                start_date=start_date, end_date=end_date, delay=0.12, skip_existing=skip_existing
            )
            print(f"[sync_all_a_stocks] 全量 A 股同步完成: {n} 只")
        except Exception as e:
            import traceback
            print(f"[sync_all_a_stocks] 失败: {e}\n{traceback.format_exc()}")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return jsonify({
        "success": True,
        "message": "全量 A 股同步已在后台启动（断点续传，仅拉取缺失）。预计 1–3 小时，请稍后刷新「数据状态」查看股票数。",
    })


@app.route("/api/sync_pool", methods=["POST"])
def sync_pool():
    """全量同步股票池：根据 data/ 下策略 CSV 拉取所有标的日线并写入数据库"""
    import io
    import sys
    try:
        if not request.json:
            data = {}
        else:
            data = request.json
        start_date = data.get("startDate", "").replace("-", "")[:8]
        end_date = data.get("endDate", "").replace("-", "")[:8]
        if not start_date or len(start_date) != 8:
            start_date = (datetime.now() - timedelta(days=365 * 2)).strftime("%Y%m%d")
        if not end_date or len(end_date) != 8:
            end_date = datetime.now().strftime("%Y%m%d")

        from database.data_fetcher import DataFetcher
        buf = io.StringIO()
        old_stdout = sys.stdout
        try:
            sys.stdout = buf
            fetcher = DataFetcher()
            n = fetcher.fetch_pool_stocks(start_date=start_date, end_date=end_date, delay=0.15)
        finally:
            sys.stdout = old_stdout
        log = buf.getvalue()
        return jsonify({"success": True, "message": f"同步完成: {n} 只成功", "log": log})
    except Exception as e:
        import traceback
        return jsonify({"success": False, "error": str(e), "log": traceback.format_exc()}), 500


@app.route("/api/scan", methods=["POST"])
def api_scan():
    """扫描市场：单策略或组合策略，筛选最新 K 线出现信号的股票。Body 支持 strategy 或 strategies（组合）。"""
    try:
        data = request.json or {}
        timeframe = (data.get("timeframe") or "D").strip().upper() or "D"
        if timeframe not in ("D", "W", "M"):
            timeframe = "D"
        limit = data.get("limit")
        if limit is not None:
            try:
                limit = int(limit)
            except (TypeError, ValueError):
                limit = 50
        strategies = data.get("strategies")
        if strategies and isinstance(strategies, list) and len(strategies) > 0:
            from scanner import scan_market_portfolio
            results = scan_market_portfolio(strategies=strategies, timeframe=timeframe, limit=limit)
            return jsonify({"success": True, "results": results, "mode": "portfolio"})
        strategy_id = data.get("strategy")
        if not strategy_id:
            return jsonify({"success": False, "error": "请选择策略或传入 strategies 组合"}), 400
        plugin_ids = [p["id"] for p in PLUGIN_STRATEGY_IDS]
        if strategy_id not in plugin_ids:
            return jsonify({"success": False, "error": "仅支持插件策略（MA/RSI/MACD/KDJ/Breakout）"}), 400
        from scanner import scan_market
        results = scan_market(strategy_id=strategy_id, timeframe=timeframe, limit=limit)
        return jsonify({"success": True, "results": results})
    except Exception as e:
        import traceback
        return jsonify({"success": False, "error": str(e), "results": []}), 500


@app.route("/api/optimize", methods=["POST"])
def api_optimize():
    """策略参数优化：在给定参数空间内搜索最优参数。"""
    try:
        data = request.json or {}
        strategy_id = data.get("strategy")
        stock_code = data.get("stockCode")
        start_date = data.get("startDate")
        end_date = data.get("endDate")
        timeframe = (data.get("timeframe") or "D").strip().upper() or "D"
        if timeframe not in ("D", "W", "M"):
            timeframe = "D"
        param_space = data.get("paramSpace")
        generations = data.get("generations", 20)
        population_per_gen = data.get("populationPerGen", 20)
        if not strategy_id or not stock_code or not start_date or not end_date:
            return jsonify({"success": False, "error": "参数不完整"}), 400
        if not param_space or not isinstance(param_space, dict):
            if strategy_id == "ma_cross":
                param_space = {"fast": [5, 20], "slow": [20, 60]}
            elif strategy_id == "rsi":
                param_space = {"period": [10, 20], "oversold": [25, 35], "overbought": [65, 80]}
            elif strategy_id == "macd":
                param_space = {"fast": [8, 15], "slow": [20, 30], "signal": [7, 12]}
            elif strategy_id == "breakout":
                param_space = {"period": [10, 30]}
            elif strategy_id == "kdj":
                param_space = {"n": [9, 14], "oversold": [15, 30], "overbought": [70, 85]}
            else:
                return jsonify({"success": False, "error": "请提供 paramSpace 或使用支持的策略"}), 400
        from optimizer import optimize_strategy_simple
        best_params, best_score = optimize_strategy_simple(
            strategy_id=strategy_id,
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date,
            param_space=param_space,
            timeframe=timeframe,
            generations=int(generations) if generations else 20,
            population_per_gen=int(population_per_gen) if population_per_gen else 20,
        )
        return jsonify({"success": True, "bestParams": best_params, "bestScore": best_score})
    except Exception as e:
        import traceback
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/run_backtest", methods=["POST"])
def run_backtest():
    """运行回测"""
    try:
        if not request.json:
            return jsonify({"success": False, "error": "请求数据为空"}), 400

        data = request.json
        strategy = data.get("strategy")
        stock_code_raw = data.get("stockCode", "").strip()
        start_date = data.get("startDate")
        end_date = data.get("endDate")
        timeframe = (data.get("timeframe") or "D").strip().upper() or "D"
        if timeframe not in ("D", "W", "M"):
            timeframe = "D"
        initial_cash = data.get("initialCash", "1000000")
        data_source = data.get("dataSource", "database")

        if not strategy or not stock_code_raw or not start_date or not end_date:
            return jsonify({"success": False, "error": "参数不完整"}), 400

        stock_codes_list = [x.strip() for x in stock_code_raw.replace("，", ",").split(",") if x.strip()]
        stock_code = stock_codes_list[0] if stock_codes_list else stock_code_raw
        if "." not in stock_code and len(stock_code) >= 6:
            stock_code = stock_code + (".XSHG" if stock_code.startswith("6") else ".XSHE")

        # swing_newhigh.py 与 swing_newhigh 等价（已注册为插件）
        if strategy == "swing_newhigh.py":
            strategy = "swing_newhigh"

        # 插件策略：多周期回测（不走 RQAlpha）
        plugin_ids = [p["id"] for p in PLUGIN_STRATEGY_IDS]
        if strategy in plugin_ids:
            try:
                from run_backtest_plugins import run_plugin_backtest
                result = run_plugin_backtest(strategy, stock_code, start_date, end_date, timeframe)
                if result.get("error"):
                    return jsonify({"success": False, "error": result["error"]}), 400
                os.makedirs("output", exist_ok=True)
                json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "last_backtest_result.json")
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                return jsonify({
                    "success": True,
                    "log": f"插件策略回测完成：{result.get('strategy_name', strategy)}，周期：{result.get('timeframe', timeframe)}",
                    "result": result,
                })
            except Exception as e:
                import traceback
                return jsonify({"success": False, "error": f"插件回测失败: {str(e)}\n{traceback.format_exc()}"})

        strategy_path = os.path.join("strategies", strategy)
        if not os.path.exists(strategy_path):
            return jsonify({"success": False, "error": f"策略文件不存在: {strategy_path}"}), 404

        os.makedirs("output", exist_ok=True)

        import subprocess
        import sys
        
        log_output = []
        log_output.append(f"回测配置:")
        log_output.append(f"策略: {strategy}")
        if len(stock_codes_list) > 1:
            log_output.append(f"股票: {stock_code} 等 {len(stock_codes_list)} 只（多股票组合）")
        else:
            log_output.append(f"股票: {stock_code}")
        log_output.append(f"日期: {start_date} 至 {end_date}")
        log_output.append(f"初始资金: {initial_cash}")
        log_output.append(f"数据源: {data_source}")
        log_output.append("")
        
        # 自动补齐策略所需的数据文件
        try:
            from database.auto_fix_strategy_data import ensure_data_files
            missing = ensure_data_files(strategy_path, stock_code)
            if missing:
                log_output.append(f"✅ 已自动补齐策略所需数据文件: {', '.join(missing)}")
            else:
                log_output.append("✅ 策略所需数据文件已完整")
        except Exception as e:
            log_output.append(f"⚠️  数据文件检查失败: {e}")
        log_output.append("")
        
        # 统一使用数据库数据源回测（避免 bundle 无数据报错）
        # database：有数据直接用，无数据则按需拉取
        # akshare：强制从网络拉取后写入 DB，再回测
        symbol = stock_code.split(".")[0] if "." in stock_code else stock_code
        start_ymd = start_date.replace("-", "")[:8]
        end_ymd = end_date.replace("-", "")[:8]
        
        # 检查策略是否需要额外历史数据（如动量策略需要60日历史）
        strategy_needs_extra_days = 0
        if "momentum" in strategy.lower() or "strategy2" in strategy.lower():
            strategy_needs_extra_days = 60  # 动量策略需要60日历史
        elif "ma" in strategy.lower() or "均线" in strategy.lower():
            strategy_needs_extra_days = 20  # 均线策略需要20日历史
        
        try:
            from database.duckdb_backend import get_db_backend
            from database.data_fetcher import DataFetcher
            from datetime import datetime, timedelta
            import pandas as pd
            
            # 提前定义，避免后续分支未赋值时引用（os 已在文件顶部 import）
            start_dt = pd.to_datetime(start_date)
            earliest_needed = (start_dt - timedelta(days=120)).strftime("%Y-%m-%d")
            fetch_start_ymd = start_ymd
            
            db = get_db_backend()
            bars = db.get_daily_bars(stock_code, start_date, end_date)
            
            # 检查是否需要拉取更早的数据（策略需要历史数据）
            need_fetch_extra = False
            if strategy_needs_extra_days > 0:
                # 计算需要的最早日期（交易日，约60日*1.5=90自然日）
                earliest_needed = (start_dt - timedelta(days=strategy_needs_extra_days * 2)).strftime("%Y-%m-%d")
                fetch_start_ymd = (start_dt - timedelta(days=strategy_needs_extra_days * 2)).strftime("%Y%m%d")
                early_bars = db.get_daily_bars(stock_code, earliest_needed, start_date)
                early_len = len(early_bars) if hasattr(early_bars, '__len__') else 0
                if early_bars is None or early_len < strategy_needs_extra_days:
                    need_fetch_extra = True
                    log_output.append(f"策略需要 {strategy_needs_extra_days} 日历史数据，将拉取更早数据…")
            
            # 对于多股票策略（如 strategy2），需要确保股票池中的所有股票都有数据
            need_fetch_pool_stocks = False
            pool_stocks_to_fetch = []
            if "strategy2" in strategy.lower() or "strategy1" in strategy.lower():
                # 检查股票池文件
                pool_files = []
                if "strategy2" in strategy.lower():
                    pool_files = ["data/tech_leader_stocks.csv", "data/consume_leader_stocks.csv"]
                elif "strategy1" in strategy.lower():
                    # 策略1需要从行业映射中提取股票
                    pass  # 暂时跳过，策略1较复杂
                
                for pool_file in pool_files:
                    if os.path.exists(pool_file):
                        try:
                            pool_df = pd.read_csv(pool_file, encoding="utf-8-sig")
                            if "代码" in pool_df.columns:
                                for stock in pool_df["代码"].dropna().astype(str).str.strip():
                                    if not stock or stock == stock_code:
                                        continue
                                    try:
                                        pool_bars = db.get_daily_bars(stock, start_date, end_date)
                                        if pool_bars is None or (hasattr(pool_bars, '__len__') and len(pool_bars) < 10):
                                            pool_stocks_to_fetch.append(stock)
                                    except Exception:
                                        pool_stocks_to_fetch.append(stock)
                        except Exception:
                            pass
                
                if pool_stocks_to_fetch:
                    need_fetch_pool_stocks = True
                    log_output.append(f"股票池中有 {len(pool_stocks_to_fetch)} 只股票缺少数据，将一并拉取…")
            
            need_fetch = (data_source == "akshare") or (bars is None or (hasattr(bars, '__len__') and len(bars) < 10)) or need_fetch_extra
            
            if need_fetch:
                if data_source == "akshare":
                    log_output.append(f"数据源为 AKShare，正在从网络拉取 {stock_code} 数据…")
                elif need_fetch_extra:
                    log_output.append(f"为满足策略历史数据需求，拉取更早数据…")
                else:
                    log_output.append(f"本地无 {stock_code} 数据或数据不足，正在按需拉取…")
                
                fetcher = DataFetcher()
                # 如果需要额外历史数据，从更早日期开始拉取
                ok = fetcher.fetch_stock_data(symbol, fetch_start_ymd, end_ymd)
                if ok:
                    log_output.append(f"已拉取 {stock_code} 并写入数据库。")
                else:
                    log_output.append(f"拉取 {stock_code} 失败，请检查网络或股票代码。")
            else:
                log_output.append(f"本地已有 {stock_code} 数据，直接回测。")
            
            # 拉取股票池中其他股票的数据（确保所有股票都有足够历史数据）
            if need_fetch_pool_stocks and pool_stocks_to_fetch:
                log_output.append(f"正在拉取股票池中其他股票的数据（确保有足够历史数据）…")
                fetcher = DataFetcher()  # 确保 fetcher 已初始化
                for pool_stock in pool_stocks_to_fetch[:10]:  # 限制数量，避免拉取过多
                    pool_symbol = pool_stock.split(".")[0] if "." in pool_stock else pool_stock
                    try:
                        # 检查是否需要更早的数据
                        pool_early_bars = db.get_daily_bars(pool_stock, earliest_needed, start_date) if strategy_needs_extra_days > 0 else None
                        pool_fetch_start = fetch_start_ymd if (strategy_needs_extra_days > 0 and (pool_early_bars is None or len(pool_early_bars) < strategy_needs_extra_days)) else start_ymd
                        pool_ok = fetcher.fetch_stock_data(pool_symbol, pool_fetch_start, end_ymd)
                        if pool_ok:
                            log_output.append(f"  ✅ {pool_stock}")
                        else:
                            log_output.append(f"  ⚠️  {pool_stock} 拉取失败")
                    except Exception as e:
                        log_output.append(f"  ⚠️  {pool_stock} 拉取异常: {e}")
            
            # 对于多股票策略，确保股票池中所有股票都有足够历史数据
            if ("strategy2" in strategy.lower() or "strategy1" in strategy.lower()) and strategy_needs_extra_days > 0:
                pool_files = []
                if "strategy2" in strategy.lower():
                    pool_files = ["data/tech_leader_stocks.csv", "data/consume_leader_stocks.csv"]
                
                all_pool_stocks = []
                for pool_file in pool_files:
                    if os.path.exists(pool_file):
                        try:
                            pool_df = pd.read_csv(pool_file, encoding="utf-8-sig")
                            if "代码" in pool_df.columns:
                                all_pool_stocks.extend(pool_df["代码"].dropna().astype(str).str.strip().tolist())
                        except Exception:
                            pass
                
                if all_pool_stocks:
                    log_output.append(f"检查股票池中 {len(all_pool_stocks)} 只股票的历史数据…")
                    fetcher = DataFetcher()
                    for pool_stock in set(s for s in all_pool_stocks if isinstance(s, str) and str(s).strip()):  # 去重并过滤无效
                        try:
                            pool_early_bars = db.get_daily_bars(pool_stock, earliest_needed, start_date)
                            plen = len(pool_early_bars) if hasattr(pool_early_bars, '__len__') else 0
                            if pool_early_bars is None or plen < strategy_needs_extra_days:
                                pool_symbol = pool_stock.split(".")[0] if "." in pool_stock else pool_stock
                                log_output.append(f"  拉取 {pool_stock} 的历史数据…")
                                fetcher.fetch_stock_data(pool_symbol, fetch_start_ymd, end_ymd)
                        except Exception:
                            pass
        except Exception as e:
            log_output.append(f"数据准备检查失败: {e}")
            import traceback
            log_output.append(traceback.format_exc())
        log_output.append("")
        
        # 多股票组合策略（strategy2/strategy1）使用自有股票池，不注入单股票代码
        is_portfolio_strategy = "strategy2" in strategy.lower() or "strategy1" in strategy.lower() or "行业轮动" in strategy or "momentum" in strategy.lower()
        temp_strategy_path = None
        if not is_portfolio_strategy and "universal" not in strategy.lower():
            try:
                from web_platform_helper import inject_stock_code_to_strategy
                import glob
                old_tmp_files = glob.glob(os.path.join("strategies", ".tmp_*"))
                for old_file in old_tmp_files:
                    try:
                        if os.path.exists(old_file):
                            os.remove(old_file)
                    except Exception:
                        pass
                temp_strategy_path = inject_stock_code_to_strategy(strategy_path, stock_code)
                strategy_path = temp_strategy_path
                log_output.append(f"已生成临时策略文件: {os.path.basename(temp_strategy_path)}")
            except ImportError:
                pass
        elif is_portfolio_strategy:
            log_output.append("多股票组合策略，使用策略自带股票池进行回测")
        log_output.append("正在运行回测...")
        
        # 始终使用数据库数据源执行回测（bundle 无数据会报错，已统一走 DB）
        script = "run_backtest_db.py"
        cmd = [
            sys.executable,
            script,
            strategy_path,
            start_date,
            end_date
        ]
        env = os.environ.copy()
        env["STOCK_CODE"] = stock_code
        env["PYTHONPATH"] = os.pathsep.join(sys.path)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5分钟超时
                env=env,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            if result.stdout:
                log_output.append("\n=== 回测输出 ===")
                log_output.append(result.stdout)
            
            if result.stderr:
                log_output.append("\n=== 错误信息 ===")
                log_output.append(result.stderr)
            
            if result.returncode == 0:
                log_output.append("\n✅ 回测完成！")
                resp = {"success": True, "log": "\n".join(log_output)}
                json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "last_backtest_result.json")
                if os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            resp["result"] = json.load(f)
                        if "strategy_name" not in resp["result"]:
                            resp["result"]["strategy_name"] = strategy
                        if "timeframe" not in resp["result"]:
                            resp["result"]["timeframe"] = timeframe
                        if is_portfolio_strategy:
                            resp["result"]["is_portfolio"] = True
                            resp["result"]["stock_codes"] = stock_codes_list[:20]
                            if "strategy2" in strategy.lower() or "momentum" in strategy.lower():
                                resp["result"]["strategy_name"] = "动量+均值回归混合（多标的组合）"
                            elif "strategy1" in strategy.lower():
                                resp["result"]["strategy_name"] = "行业轮动（多标的组合）"
                            elif "行业轮动" in strategy:
                                resp["result"]["strategy_name"] = "行业轮动（多标的组合）"
                        if "strategy_score" not in resp["result"] and resp["result"].get("stats"):
                            try:
                                from core.scoring import score_strategy
                                sc, gr = score_strategy(resp["result"]["stats"])
                                resp["result"]["strategy_score"] = sc
                                resp["result"]["strategy_grade"] = gr
                            except Exception:
                                pass
                    except Exception:
                        pass
                return jsonify(resp)
            else:
                log_output.append(f"\n❌ 回测失败 (退出码: {result.returncode})")
                return jsonify({"success": False, "error": "\n".join(log_output)})
                
        except subprocess.TimeoutExpired:
            return jsonify({"success": False, "error": "回测超时（超过5分钟）"})
        except Exception as e:
            return jsonify({"success": False, "error": f"运行回测时出错: {str(e)}"})
        finally:
            # 仅清理临时策略文件（.tmp_ 开头），勿删原策略文件
            if temp_strategy_path and ".tmp_" in temp_strategy_path and os.path.exists(temp_strategy_path):
                try:
                    os.remove(temp_strategy_path)
                except Exception:
                    pass

    except Exception as e:
        import traceback
        err_msg = f"服务器错误: {str(e)}\n{traceback.format_exc()}"
        # 返回 200 + success:false，便于前端在日志区显示完整错误信息
        return jsonify({"success": False, "error": err_msg})


@app.route("/api/strategy/<path:filepath>")
def get_strategy(filepath):
    """获取策略文件内容"""
    try:
        # 安全检查：防止路径遍历攻击
        if ".." in filepath or filepath.startswith("/"):
            return jsonify({"success": False, "error": "无效的文件路径"}), 400
        
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            return jsonify({"success": True, "content": content})
        else:
            return jsonify({"success": False, "error": "文件不存在"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/strategy", methods=["POST"])
def save_strategy():
    """保存策略文件"""
    try:
        if not request.json:
            return jsonify({"success": False, "error": "请求数据为空"}), 400
        
        data = request.json
        filepath = data.get("path")
        content = data.get("content")
        
        if not filepath or content is None:
            return jsonify({"success": False, "error": "参数不完整"}), 400
        
        # 安全检查：防止路径遍历攻击
        if ".." in filepath or filepath.startswith("/"):
            return jsonify({"success": False, "error": "无效的文件路径"}), 400
        
        # 确保目录存在
        dirname = os.path.dirname(filepath) if os.path.dirname(filepath) else "."
        os.makedirs(dirname, exist_ok=True)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({"success": False, "error": "接口不存在"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"success": False, "error": "服务器内部错误"}), 500

if __name__ == "__main__":
    # 确保必要的目录存在
    os.makedirs("strategies", exist_ok=True)
    os.makedirs("output", exist_ok=True)
    
    PORT = int(os.environ.get("PORT", 5050))
    HOST = os.environ.get("HOST", "127.0.0.1")
    print("量化交易平台启动中...")
    print("访问 http://{}:{} 使用平台（或 http://localhost:{}）".format(HOST, PORT, PORT))
    print("按 Ctrl+C 停止服务。若 5050 被占用可: PORT=8080 python web_platform.py")
    app.run(host=HOST, port=PORT, debug=True)
