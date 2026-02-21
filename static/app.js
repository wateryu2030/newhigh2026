(function() {
  var selectedStrategy = '';
  var selectedIsPlugin = false;
  var cockpitKlineChart = null;
  var cockpitCurveChart = null;
  var cockpitFuture5Chart = null;
  var lastBacktestResult = null;

  var PLUGIN_IDS = ['ma_cross', 'rsi', 'macd', 'kdj', 'breakout', 'swing_newhigh'];

  function getStockCodeInput() {
    var custom = document.getElementById('customStockCode');
    var select = document.getElementById('stockCode');
    var raw = (custom && custom.value ? custom.value.trim() : '') || (select && select.value ? select.value : '');
    if (!raw) return '';
    raw = raw.split(/[,\s，；;]+/)[0].trim();
    if (!raw) return '';
    if (!raw.includes('.')) raw = raw + (raw.startsWith('6') ? '.XSHG' : '.XSHE');
    return raw;
  }

  function updateActionButtons() {
    var scanBtn = document.getElementById('scanBtn');
    var optimizeBtn = document.getElementById('optimizeBtn');
    var portfolioBtn = document.getElementById('portfolioBtn');
    var hintEl = document.getElementById('actionHint');
    var enabled = selectedIsPlugin;
    [scanBtn, optimizeBtn, portfolioBtn].forEach(function(btn) {
      if (btn) {
        btn.disabled = !enabled;
        btn.classList.toggle('disabled', !enabled);
      }
    });
    if (hintEl) {
      if (!selectedStrategy) {
        hintEl.innerHTML = '<span style="color:#888;">1）先在左侧选择策略 → 2）选择股票 → 3）运行回测</span>';
      } else if (enabled) {
        hintEl.innerHTML = '<span style="color:#0f9;">✓ 当前策略支持扫描市场、参数优化和组合回测</span>';
      } else {
        hintEl.innerHTML = '<span style="color:#888;">扫描/优化/组合需选择插件策略（MA、RSI、MACD、KDJ、Breakout、波段新高）</span>';
      }
    }
  }

  function handleError(error, context) {
    try {
      var log = document.getElementById('log');
      if (log) log.textContent = '错误: ' + (error.message || error.toString());
    } catch (e) {}
  }

  function renderFuture5Day(result) {
    var range = result.futurePriceRange;
    var prediction = result.prediction;
    var kline = result.kline || [];
    var lastClose = kline.length ? parseFloat(kline[kline.length - 1].close) : null;
    var low = range && range.low != null ? parseFloat(range.low) : null;
    var high = range && range.high != null ? parseFloat(range.high) : null;
    var trend = prediction && prediction.trend ? prediction.trend : 'SIDEWAYS';
    var chartEl = document.getElementById('resultFuture5DayChart');
    var signalsEl = document.getElementById('resultFuture5DaySignals');
    if (!chartEl || !signalsEl) return;
    var days = ['D+1', 'D+2', 'D+3', 'D+4', 'D+5'];
    var mid = (low != null && high != null) ? (low + high) / 2 : lastClose;
    var start = lastClose != null ? lastClose : mid;
    var target = start;
    if (trend === 'UP' && high != null) target = high * 0.95;
    else if (trend === 'DOWN' && low != null) target = low * 1.05;
    else if (mid != null) target = mid;
    var prices = [];
    for (var i = 0; i < 5; i++) {
      var t = (i + 1) / 5;
      prices.push(parseFloat((start + (target - start) * t).toFixed(2)));
    }
    var buyIdx = -1, sellIdx = -1;
    if (low != null && high != null) {
      var minP = Math.min.apply(null, prices), maxP = Math.max.apply(null, prices);
      for (var j = 0; j < 5; j++) { if (prices[j] <= low + (mid - low) * 0.5) buyIdx = j; }
      for (var k = 4; k >= 0; k--) { if (prices[k] >= mid + (high - mid) * 0.5) sellIdx = k; }
    }
    var lines = [];
    if (low != null && high != null) {
      lines.push('<span style="color:#0f9;">潜在买点：</span> 若价格回落至 <span style="color:#0f9;">' + low + ' — ' + mid.toFixed(2) + '</span> 区间（如 D+2～D+3）可能触发策略买点。');
      lines.push('<span style="color:#f55;">潜在卖点：</span> 若价格上行至 <span style="color:#f55;">' + mid.toFixed(2) + ' — ' + high + '</span> 区间（如 D+4～D+5）可能触发策略卖点。');
    }
    lines.push('（以上为基于当前趋势与区间的参考，非实际预测）');
    signalsEl.innerHTML = lines.join('<br/>');
    if (typeof echarts === 'undefined') return;
    try {
      if (cockpitFuture5Chart) { cockpitFuture5Chart.dispose(); cockpitFuture5Chart = null; }
      chartEl.innerHTML = '';
      cockpitFuture5Chart = echarts.init(chartEl);
      var markPointData = [];
      if (buyIdx >= 0) markPointData.push({ name: '买', coord: [days[buyIdx], prices[buyIdx]], value: '买', itemStyle: { color: '#0f9' }, symbol: 'triangle', symbolRotate: 0, symbolSize: 12 });
      if (sellIdx >= 0) markPointData.push({ name: '卖', coord: [days[sellIdx], prices[sellIdx]], value: '卖', itemStyle: { color: '#f55' }, symbol: 'triangle', symbolRotate: 180, symbolSize: 12 });
      cockpitFuture5Chart.setOption({
        backgroundColor: 'transparent',
        grid: { left: 44, right: 24, top: 16, bottom: 40 },
        xAxis: {
          type: 'category',
          data: days,
          axisLabel: { color: '#bbb', fontSize: 12 }
        },
        yAxis: { type: 'value', scale: true, axisLabel: { color: '#888' }, splitLine: { lineStyle: { color: '#2a2a4a' } } },
        series: [
          { type: 'line', data: prices, smooth: true, symbol: 'circle', symbolSize: 6, lineStyle: { color: '#0f9' }, itemStyle: { color: '#0f9' }, markPoint: markPointData.length ? { data: markPointData } : undefined }
        ]
      });
    } catch (e) {
      chartEl.innerHTML = '<div style="padding:12px;color:#f55;text-align:center;">未来5日图渲染失败</div>';
    }
  }

  function loadEChartsThenRender(result) {
    lastBacktestResult = result;
    var klineEl = document.getElementById('resultKline');
    var curveCompareEl = document.getElementById('resultCurveCompare');
    if (klineEl) klineEl.innerHTML = '<div style="padding:20px;color:#888;text-align:center;">正在加载图表库…</div>';
    if (curveCompareEl) curveCompareEl.innerHTML = '<div style="padding:20px;color:#888;text-align:center;">请稍候</div>';
    var script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js';
    script.async = true;
    script.onload = function() {
      requestAnimationFrame(function() { renderCockpit(lastBacktestResult); });
    };
    script.onerror = function() {
      if (klineEl) klineEl.innerHTML = '<div style="padding:20px;color:#f55;text-align:center;">图表库加载失败，请检查网络后刷新重试</div>';
      if (curveCompareEl) curveCompareEl.innerHTML = '';
    };
    document.head.appendChild(script);
  }

  function renderCockpit(result) {
    if (!result) return;
    var cockpitEl = document.getElementById('resultCockpit');
    var klineEl = document.getElementById('resultKline');
    var curveCompareEl = document.getElementById('resultCurveCompare');
    var signalReasonEl = document.getElementById('resultSignalReason');
    if (!cockpitEl || !klineEl || !curveCompareEl) return;
    try {
      if (cockpitKlineChart) { cockpitKlineChart.dispose(); cockpitKlineChart = null; }
      if (cockpitCurveChart) { cockpitCurveChart.dispose(); cockpitCurveChart = null; }
      if (cockpitFuture5Chart) { cockpitFuture5Chart.dispose(); cockpitFuture5Chart = null; }
    } catch (e) {}
    var hasKline = result.kline && result.kline.length > 0;
    var hasHold = result.holdCurve && result.holdCurve.length > 0 && result.curve && result.curve.length > 0;
    if (!hasKline && !hasHold) {
      cockpitEl.style.display = 'none';
      return;
    }
    cockpitEl.style.display = 'block';
    lastBacktestResult = result;
    if (typeof echarts === 'undefined') {
      loadEChartsThenRender(result);
      return;
    }
    klineEl.innerHTML = '';
    curveCompareEl.innerHTML = '';
    function drawCharts() {
      var dark = { backgroundColor: 'transparent', textStyle: { color: '#888' } };
      if (hasKline) {
        var kline = result.kline;
        var dates = [];
        var ohlc = [];
        for (var i = 0; i < kline.length; i++) {
          var k = kline[i];
          var o = Number(k.open), c = Number(k.close), l = Number(k.low), h = Number(k.high);
          if (isNaN(o)) o = 0; if (isNaN(c)) c = 0; if (isNaN(l)) l = 0; if (isNaN(h)) h = 0;
          dates.push(String(k.date != null ? k.date : ''));
          ohlc.push([o, c, l, h]);
        }
        if (dates.length === 0 || ohlc.length === 0) return;
        var dateToIdx = {};
        dates.forEach(function(d, i) { dateToIdx[d] = i; });
        var markArea = [];
        (result.buyZones || []).forEach(function(z) {
          var a = dateToIdx[z.start], b = dateToIdx[z.end];
          if (a != null && b != null) markArea.push([{ xAxis: a, itemStyle: { color: 'rgba(0,255,100,0.15)' } }, { xAxis: b }]);
        });
        (result.sellZones || []).forEach(function(z) {
          var a = dateToIdx[z.start], b = dateToIdx[z.end];
          if (a != null && b != null) markArea.push([{ xAxis: a, itemStyle: { color: 'rgba(255,80,80,0.15)' } }, { xAxis: b }]);
        });
        var markPointData = [];
        (result.markers || []).forEach(function(m) {
          var coord = m.coord;
          if (!coord || coord.length < 2) return;
          var isBuy = (m.name || m.value || '') === 'BUY';
          markPointData.push({
            name: m.name || (isBuy ? 'BUY' : 'SELL'),
            coord: [String(coord[0]), Number(coord[1])],
            value: isBuy ? '买' : '卖',
            itemStyle: { color: isBuy ? '#00d68f' : '#ff6b6b' },
            symbol: 'arrow',
            symbolRotate: isBuy ? 0 : 180,
            symbolSize: 14,
            label: {
              show: true,
              formatter: (m.reason || m.name) ? (m.name + ' ' + (m.reason || '')) : m.name,
              fontSize: 12,
              color: isBuy ? '#e0fff4' : '#ffe8e8',
              backgroundColor: isBuy ? 'rgba(0,80,50,0.92)' : 'rgba(100,20,20,0.92)',
              borderColor: isBuy ? '#00d68f' : '#ff6b6b',
              borderWidth: 1,
              padding: [4, 8],
              borderRadius: 4
            }
          });
        });
        var opt = {
          backgroundColor: 'transparent',
          tooltip: { trigger: 'axis', axisPointer: { type: 'cross' }, formatter: function(params) {
            if (!params || !params.length) return '';
            var p = params[0];
            var axisVal = p.axisValue;
            var idx = dates.indexOf(axisVal);
            var line = (axisVal || '') + '<br/>';
            if (idx >= 0 && kline[idx]) {
              var k = kline[idx];
              line += '开 ' + k.open + ' 高 ' + k.high + ' 低 ' + k.low + ' 收 ' + k.close;
            }
            (result.markers || []).forEach(function(m) {
              if (m.coord && m.coord[0] === axisVal) line += '<br/><span style="color:' + (m.name === 'BUY' ? '#0f9' : '#f55') + '">' + (m.name || '') + '</span> ' + (m.reason || '');
            });
            return line;
          }},
          grid: { left: 48, right: 24, top: 24, bottom: 52 },
          xAxis: {
            type: 'category',
            data: dates,
            axisLabel: {
              color: '#bbb',
              fontSize: 12,
              rotate: 45,
              formatter: function(value) { return value ? value.substring(5) : value; }
            },
            splitLine: { show: false }
          },
          yAxis: { type: 'value', scale: true, axisLabel: { color: '#888' }, splitLine: { lineStyle: { color: '#2a2a4a' } } },
          series: [
            { type: 'candlestick', data: ohlc, itemStyle: { color: '#0f9', borderColor: '#0f9', color0: '#f55', borderColor0: '#f55' }, markArea: markArea.length ? { silent: true, data: markArea } : undefined, markPoint: markPointData.length ? { data: markPointData, symbolSize: 14 } : undefined }
          ]
        };
        try {
          if (!cockpitKlineChart) cockpitKlineChart = echarts.init(klineEl);
          cockpitKlineChart.setOption(opt, true);
        } catch (e) {
          if (klineEl) klineEl.innerHTML = '<div style="padding:20px;color:#f55;text-align:center;">K线图渲染失败，请刷新重试</div>';
        }
      }
      if (hasHold) {
        var curve = result.curve;
        var holdCurve = result.holdCurve;
        var curveDates = curve.map(function(p) { return String(p.date != null ? p.date : ''); });
        var curveVals = curve.map(function(p) { var v = Number(p.value); return isNaN(v) ? null : v; });
        var holdMap = {};
        (holdCurve || []).forEach(function(p) { var v = Number(p.value); if (!isNaN(v)) holdMap[String(p.date)] = v; });
        var holdVals = curveDates.map(function(d) { return holdMap[d] != null ? holdMap[d] : null; });
        try {
          if (!cockpitCurveChart) cockpitCurveChart = echarts.init(curveCompareEl);
          cockpitCurveChart.setOption({
            backgroundColor: 'transparent',
            grid: { left: 48, right: 24, top: 24, bottom: 52 },
            legend: { data: ['策略净值', '持有净值'], textStyle: { color: '#888' }, top: 0 },
            xAxis: {
              type: 'category',
              data: curveDates,
              axisLabel: {
                color: '#bbb',
                fontSize: 12,
                rotate: 45,
                formatter: function(value) { return value ? value.substring(5) : value; }
              }
            },
            yAxis: { type: 'value', scale: true, axisLabel: { color: '#888' }, splitLine: { lineStyle: { color: '#2a2a4a' } } },
            series: [
              { name: '策略净值', type: 'line', data: curveVals, smooth: true, symbol: 'none', lineStyle: { color: '#0f9' } },
              { name: '持有净值', type: 'line', data: holdVals, smooth: true, symbol: 'none', lineStyle: { color: '#f90' } }
            ]
          }, true);
        } catch (e) {
          if (curveCompareEl) curveCompareEl.innerHTML = '<div style="padding:20px;color:#f55;text-align:center;">净值曲线渲染失败，请刷新重试</div>';
        }
      }
    }
    if (klineEl.offsetParent === null || klineEl.offsetWidth === 0) {
      requestAnimationFrame(function() { requestAnimationFrame(drawCharts); });
    } else {
      requestAnimationFrame(drawCharts);
    }
    var futureTrendEl = document.getElementById('resultFutureTrend');
    var futureProbEl = document.getElementById('resultFutureProb');
    var futureRangeEl = document.getElementById('resultFutureRange');
    if (futureTrendEl && futureProbEl && futureRangeEl) {
      var prob = result.futureProbability;
      var range = result.futurePriceRange;
      var prediction = result.prediction;
      var hasProb = prob && (prob.up != null || prob.sideways != null || prob.down != null);
      var hasRange = range && range.low != null && range.high != null;
      var hasPred = prediction && prediction.trend;
      if (hasProb || hasRange || hasPred) {
        futureTrendEl.style.display = 'block';
        if (hasPred) {
          var trendText = prediction.trend === 'UP' ? '上涨' : (prediction.trend === 'DOWN' ? '下跌' : '震荡');
          var trendColor = prediction.trend === 'UP' ? '#0f9' : (prediction.trend === 'DOWN' ? '#f55' : '#888');
          var conf = prediction.score != null ? Math.round(Math.min(1, Math.max(0, (prediction.score + 0.3) / 1.0)) * 100) : 50;
          futureProbEl.innerHTML = '<span style="color:' + trendColor + ';">未来趋势：' + trendText + '</span> <span style="color:#888;">置信度 ' + conf + '%</span>';
        } else if (hasProb) {
          var up = (prob.up != null ? Math.round(prob.up * 100) : 0);
          var side = (prob.sideways != null ? Math.round(prob.sideways * 100) : 0);
          var down = (prob.down != null ? Math.round(prob.down * 100) : 0);
          futureProbEl.innerHTML = '<span style="color:#0f9;">上涨 ' + up + '%</span> <span style="color:#888;">震荡 ' + side + '%</span> <span style="color:#f55;">下跌 ' + down + '%</span>';
        } else futureProbEl.innerHTML = '';
        if (hasRange) {
          futureRangeEl.textContent = '预计区间（' + (range.horizonDays || 5) + ' 日）: ' + range.low + ' — ' + range.high;
        } else futureRangeEl.textContent = '';
        var btn5 = document.getElementById('btnFuture5Day');
        var box5 = document.getElementById('resultFuture5Day');
        if (btn5 && box5) {
          btn5.style.display = (hasRange || hasPred) ? 'inline-block' : 'none';
          var r = range || {};
          var lo = r.low != null ? parseFloat(r.low).toFixed(2) : null;
          var hi = r.high != null ? parseFloat(r.high).toFixed(2) : null;
          var md = (lo != null && hi != null) ? ((parseFloat(lo) + parseFloat(hi)) / 2).toFixed(2) : null;
          var priceHint = (lo != null && hi != null && md) ? '（买点约 ' + lo + '–' + md + ' / 卖点约 ' + md + '–' + hi + '）' : '';
          btn5.textContent = '查看未来5日走势与买卖点' + priceHint;
          btn5.title = priceHint ? '买点区间：' + lo + '–' + md + '，卖点区间：' + md + '–' + hi : '展开查看买卖点价格';
          btn5.onclick = function() {
            var visible = box5.style.display === 'block';
            box5.style.display = visible ? 'none' : 'block';
            if (!visible) renderFuture5Day(result);
          };
          box5.style.display = 'none';
        }
      } else {
        futureTrendEl.style.display = 'none';
        var btn5 = document.getElementById('btnFuture5Day');
        if (btn5) btn5.style.display = 'none';
      }
    }
    var statsEl = document.getElementById('resultCockpitStats');
    if (statsEl && result.stats) {
      var st = result.stats;
      var parts = [];
      if (st.tradeCount != null) parts.push('交易次数 ' + st.tradeCount);
      if (st.winRate != null) parts.push('胜率 ' + (st.winRate * 100).toFixed(0) + '%');
      if (st.maxDrawdown != null) parts.push('最大回撤 ' + (st.maxDrawdown * 100).toFixed(2) + '%');
      if (st.return != null) parts.push('总收益 ' + (st.return * 100).toFixed(2) + '%');
      statsEl.innerHTML = parts.length ? parts.join('　') : '';
      statsEl.style.display = parts.length ? 'block' : 'none';
    }
    var signalListEl = document.getElementById('resultSignalList');
    if (signalListEl) {
      signalListEl.innerHTML = '';
      var signals = result.signals || [];
      if (signals.length > 0) {
        signals.forEach(function(sig, idx) {
          var btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'signal-pill';
          btn.style.cssText = 'padding:6px 12px;border-radius:4px;font-size:12px;cursor:pointer;border:1px solid ' + (sig.type === 'buy' ? '#0f9' : '#f55') + ';background:transparent;color:' + (sig.type === 'buy' ? '#0f9' : '#f55') + ';';
          btn.textContent = sig.date + ' ' + (sig.type === 'buy' ? 'BUY' : 'SELL');
          btn.onclick = (function(s) {
            return function() {
              var reasonEl = document.getElementById('resultSignalReason');
              if (!reasonEl) return;
              var parts = [];
              parts.push((s.type === 'buy' ? '买入' : '卖出') + '  ' + s.date + '  价格 ' + (s.price != null ? s.price : '-'));
              var reasonText = s.reason || (s.reasons && s.reasons.length ? s.reasons.join('；') : '');
              if (reasonText) parts.push('原因: ' + reasonText);
              if (s.winRate != null) parts.push('历史胜率: ' + (s.winRate * 100).toFixed(1) + '%');
              if (s.avgReturn != null) parts.push('平均收益: ' + (s.avgReturn * 100).toFixed(2) + '%');
              if (s.score != null) parts.push('评分: ' + s.score);
              reasonEl.innerHTML = parts.join('<br>');
            };
          })(sig);
          signalListEl.appendChild(btn);
        });
      }
    }
    if (signalReasonEl) {
      if (!result.signals || result.signals.length === 0) signalReasonEl.textContent = '暂无买卖信号记录';
      else signalReasonEl.textContent = '点击上方买卖信号可查看原因';
    }
  }

  function updateDecisionPanel(result) {
    if (!result) return;
    var priceEl = document.getElementById('decisionCurrentPrice');
    var signalEl = document.getElementById('decisionSignalValue');
    var trendEl = document.getElementById('decisionTrend');
    var scoreEl = document.getElementById('decisionScoreValue');
    var gradeEl = document.getElementById('decisionGradeValue');
    var suggestEl = document.getElementById('decisionSuggestion');
    var kline = result.kline || [];
    var lastClose = kline.length ? kline[kline.length - 1].close : null;
    if (priceEl) priceEl.textContent = lastClose != null ? '当前价格: ' + lastClose : '当前价格: —';
    var signals = result.signals || [];
    var lastSig = signals.length ? signals[signals.length - 1] : null;
    var sigText = 'HOLD';
    var sigColor = '#fc0';
    if (lastSig) {
      sigText = (lastSig.type === 'buy' ? 'BUY' : 'SELL');
      sigColor = lastSig.type === 'buy' ? '#0f9' : '#f55';
    }
    if (signalEl) { signalEl.textContent = sigText; signalEl.style.color = sigColor; }
    var pred = result.prediction || {};
    var trend = pred.trend || '—';
    var trendLabel = trend === 'UP' ? '上涨' : (trend === 'DOWN' ? '下跌' : '震荡');
    if (trendEl) trendEl.textContent = '趋势: ' + trendLabel;
    var score = result.strategy_score;
    var grade = result.strategy_grade || '';
    if (scoreEl) scoreEl.textContent = score != null ? (score + ' / 100') : '—';
    if (gradeEl) gradeEl.textContent = grade ? '（' + grade + '）' : '';
    var suggest = '运行回测后显示';
    if (lastSig && lastSig.type === 'buy') suggest = '最新信号为买入，可参考区间与趋势';
    else if (lastSig && lastSig.type === 'sell') suggest = '最新信号为卖出，注意风险';
    else if (signals.length === 0) suggest = '暂无买卖信号';
    else suggest = '当前无新信号，观望';
    if (suggestEl) suggestEl.textContent = '建议: ' + suggest;
  }

  async function scanMarket() {
    var strategyInput = document.getElementById('strategyFile');
    var strategy = strategyInput ? (strategyInput.getAttribute('data-file') || strategyInput.value.split('(')[1]) : '';
    if (strategy && strategy.indexOf(')') >= 0) strategy = strategy.replace(')', '').trim();
    var timeframe = (document.getElementById('timeframe') && document.getElementById('timeframe').value) || 'D';
    var log = document.getElementById('log');
    if (!strategy) {
      alert('请先在左侧选择策略');
      return;
    }
    if (PLUGIN_IDS.indexOf(strategy) < 0) {
      alert('扫描市场需选择插件策略（MA、RSI、MACD、KDJ、Breakout）');
      return;
    }
    if (log) log.textContent = '正在扫描市场（' + strategy + ' ' + timeframe + '）…\n';
    var btn = document.getElementById('scanBtn');
    if (btn) btn.disabled = true;
    try {
      var res = await fetch('/api/scan', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({strategy: strategy, timeframe: timeframe, limit: 50})
      });
      var data = await res.json();
      if (data.success && data.results && data.results.length > 0) {
        var lines = ['扫描完成，共 ' + data.results.length + ' 只出现最新信号：\n'];
        data.results.forEach(function(r) {
          lines.push(r.symbol + ' ' + (r.name || '') + ' ' + r.signal + ' @ ' + r.price + ' ' + (r.trend || ''));
        });
        if (log) log.textContent = lines.join('\n');
      } else if (data.success) {
        if (log) log.textContent = '扫描完成，当前无最新信号股票。';
      } else {
        if (log) log.textContent = '扫描失败: ' + (data.error || '未知错误');
      }
    } catch (e) {
      if (log) log.textContent = '扫描请求失败: ' + e.message;
    }
    if (btn) btn.disabled = false;
  }

  async function optimizeParams() {
    var strategyInput = document.getElementById('strategyFile');
    var strategy = strategyInput ? (strategyInput.getAttribute('data-file') || '') : '';
    if (!strategy && strategyInput && strategyInput.value) strategy = strategyInput.value.split('(')[1]; if (strategy && strategy.indexOf(')') >= 0) strategy = strategy.replace(')', '').trim();
    var stockCode = getStockCodeInput();
    var startDate = document.getElementById('startDate').value;
    var endDate = document.getElementById('endDate').value;
    var timeframe = (document.getElementById('timeframe') && document.getElementById('timeframe').value) || 'D';
    var log = document.getElementById('log');
    if (!strategy || PLUGIN_IDS.indexOf(strategy) < 0) {
      alert('参数优化需选择插件策略（MA、RSI、MACD、KDJ、Breakout）并选择股票');
      return;
    }
    if (!stockCode) {
      alert('请选择或输入股票代码');
      return;
    }
    if (log) log.textContent = '参数优化中（约 1–2 分钟）…\n';
    var btn = document.getElementById('optimizeBtn');
    if (btn) btn.disabled = true;
    try {
      var res = await fetch('/api/optimize', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({strategy: strategy, stockCode: stockCode, startDate: startDate, endDate: endDate, timeframe: timeframe})
      });
      var data = await res.json();
      if (data.success) {
        var msg = '优化完成。最佳评分: ' + data.bestScore + '\n最佳参数: ' + JSON.stringify(data.bestParams || {});
        if (log) log.textContent = msg;
      } else {
        if (log) log.textContent = '优化失败: ' + (data.error || '未知错误');
      }
    } catch (e) {
      if (log) log.textContent = '优化请求失败: ' + e.message;
    }
    if (btn) btn.disabled = false;
  }

  async function runPortfolioBacktest() {
    var stockCode = getStockCodeInput();
    var startDate = document.getElementById('startDate').value;
    var endDate = document.getElementById('endDate').value;
    var timeframe = (document.getElementById('timeframe') && document.getElementById('timeframe').value) || 'D';
    var log = document.getElementById('log');
    if (!stockCode) {
      alert('请选择或输入股票代码');
      return;
    }
    var strategies = [
      { strategy_id: 'ma_cross', weight: 0.5 },
      { strategy_id: 'rsi', weight: 0.5 }
    ];
    var btn = document.getElementById('portfolioBtn');
    if (btn) btn.disabled = true;
    if (log) log.textContent = '组合策略回测中（MA + RSI 等权）…\n';
    try {
      var res = await fetch('/api/portfolio', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ strategies: strategies, stockCode: stockCode, startDate: startDate, endDate: endDate, timeframe: timeframe })
      });
      var data = await res.json();
      if (data.success && data.result) {
        if (log) log.textContent = '组合策略回测完成。\n';
        var card = document.getElementById('resultCard');
        card.style.display = 'block';
        var infoEl = document.getElementById('resultStrategyInfo');
        if (infoEl) {
          infoEl.textContent = '策略: ' + (data.result.strategy_name || '组合') + '　周期: ' + (data.result.timeframe === 'W' ? '周线' : (data.result.timeframe === 'M' ? '月线' : '日线'));
          infoEl.style.display = 'block';
        }
        var s = data.result.summary || {};
        var sumEl = document.getElementById('resultSummary');
        sumEl.innerHTML = '<div style="background:#1a2744;padding:10px;border-radius:4px;"><span style="color:#888;">总收益</span><br><span style="color:#0f9;">' + ((s.total_returns != null || s.return_rate != null) ? ((s.return_rate != null ? s.return_rate * 100 : (s.total_returns || 0) * 100).toFixed(2) + '%') : '—') + '</span></div>' +
          '<div style="background:#1a2744;padding:10px;border-radius:4px;"><span style="color:#888;">最大回撤</span><br><span style="color:#0f9;">' + (s.max_drawdown != null ? (s.max_drawdown * 100).toFixed(2) + '%' : '—') + '</span></div>';
        var curveEl = document.getElementById('resultCurve');
        var curve = data.result.curve || [];
        var vals = curve.map(function(p) { return p.value; }).filter(function(v) { return v != null && v === v; });
        if (curve.length > 0 && vals.length > 0) {
          var min = Math.min.apply(null, vals);
          var max = Math.max.apply(null, vals);
          var range = max - min || 1;
          var w = curveEl.offsetWidth || 600;
          var h = 200;
          var pad = 20;
          var points = curve.map(function(p, i) {
            var x = pad + (w - 2 * pad) * (i / (curve.length - 1 || 1));
            var v = p.value != null && p.value === p.value ? p.value : vals[0];
            var y = h - pad - (h - 2 * pad) * ((v - min) / range);
            return x + ',' + y;
          }).join(' ');
          curveEl.innerHTML = '<svg width="100%" height="' + h + '" viewBox="0 0 ' + w + ' ' + h + '"><polyline fill="none" stroke="#0f9" stroke-width="1.5" points="' + points + '"/></svg>';
        } else {
          curveEl.innerHTML = '<div style="padding:20px;color:#888;">无净值曲线</div>';
        }
        renderCockpit(data.result);
        updateDecisionPanel(data.result);
      } else {
        if (log) log.textContent = '组合回测失败: ' + (data.error || '未知错误');
      }
    } catch (e) {
      if (log) log.textContent = '请求失败: ' + e.message;
    }
    if (btn) btn.disabled = false;
  }

  async function deleteStrategy(filepath) {
    if (!filepath) return;
    try {
      var res = await fetch('/api/strategies/' + encodeURIComponent(filepath), { method: 'DELETE' });
      var data = await res.json().catch(function() { return {}; });
      if (data.success) {
        if (selectedStrategy === filepath) {
          selectedStrategy = '';
          selectedIsPlugin = false;
          document.getElementById('strategyFile').value = '';
          document.getElementById('strategyFile').removeAttribute('data-file');
          updateActionButtons();
        }
        loadStrategies();
        var log = document.getElementById('log');
        if (log) log.textContent = '已删除策略: ' + filepath + '\n' + (log.textContent || '');
      } else {
        alert(data.error || '删除失败');
      }
    } catch (e) {
      alert('删除失败: ' + (e.message || '网络错误'));
    }
  }

  async function loadStrategies() {
    try {
      var res = await fetch('/api/strategies', { cache: 'no-store' });
      if (!res.ok) {
        throw new Error('HTTP ' + res.status + ': ' + res.statusText);
      }
      var data = await res.json();
      var list = document.getElementById('strategyList');
      var select = document.getElementById('strategyFile');
      if (!list || !select) return;

      list.innerHTML = '';
      select.innerHTML = '<option value="">请选择策略</option>';

      var strategies = (data && Array.isArray(data.strategies)) ? data.strategies : [];
      strategies.forEach(function(s) {
        var file = s.file || s;
        var name = s.name || file;
        var desc = s.description || '';
        var isPlugin = s.plugin === true || PLUGIN_IDS.indexOf(file) >= 0;
        var li = document.createElement('li');
        li.className = 'strategy-item';
        li.title = desc;
        li.setAttribute('data-plugin', isPlugin ? '1' : '0');
        var safeName = (name || '').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        var safeDesc = (desc + '').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        var delBtn = isPlugin ? '' : ' <button type="button" class="strategy-delete-btn" title="删除策略" data-file="' + String(file).replace(/"/g, '&quot;') + '">×</button>';
        li.innerHTML = '<span class="strategy-item-content"><strong>' + safeName + '</strong>' + (isPlugin ? ' <span style="color:#0f9;font-size:11px;">插件</span>' : '') + (desc ? '<br><span class="strategy-desc">' + safeDesc + '</span>' : '') + '</span>' + delBtn;
        li.onclick = function(e) {
          if (e.target && e.target.classList.contains('strategy-delete-btn')) return;
          document.querySelectorAll('.strategy-item').forEach(function(el) { el.classList.remove('active'); });
          li.classList.add('active');
          selectedStrategy = file;
          selectedIsPlugin = isPlugin;
          document.getElementById('strategyFile').value = name + ' (' + file + ')';
          document.getElementById('strategyFile').setAttribute('data-file', file);
          updateActionButtons();
        };
        var delBtnEl = li.querySelector('.strategy-delete-btn');
        if (delBtnEl) {
          delBtnEl.onclick = function(e) {
            e.stopPropagation();
            if (confirm('确定要删除策略「' + name + '」吗？此操作不可恢复。')) {
              deleteStrategy(file);
            }
          };
        }
        list.appendChild(li);
      });
      updateActionButtons();
    } catch (e) {
      handleError(e, 'loadStrategies');
      var list = document.getElementById('strategyList');
      if (list) list.innerHTML = '<li style="color:#f55;padding:12px;">策略加载失败，请确认服务已启动（python web_platform.py）并访问 http://127.0.0.1:5050</li>';
    }
  }

  async function loadStocks() {
    try {
      var res = await fetch('/api/stocks');
      if (!res.ok) {
        throw new Error('HTTP ' + res.status + ': ' + res.statusText);
      }
      var data = await res.json();
      var select = document.getElementById('stockCode');
      if (!select) return;

      select.innerHTML = '<option value="">或从列表选择</option>';

      if (data.stocks && data.stocks.length > 0) {
        data.stocks.forEach(function(stock) {
          var option = document.createElement('option');
          option.value = stock.order_book_id || stock.symbol;
          option.textContent = stock.name ? (stock.symbol + ' - ' + stock.name) : stock.symbol;
          select.appendChild(option);
        });
      } else {
        var option = document.createElement('option');
        option.value = '';
        option.textContent = '暂无股票数据，请先同步数据';
        select.appendChild(option);
      }
    } catch (e) {
      handleError(e, 'loadStocks');
    }
  }

  async function runBacktest() {
    var strategyInput = document.getElementById('strategyFile');
    var strategy = strategyInput.getAttribute('data-file') || '';
    if (!strategy && strategyInput.value) {
      var parts = strategyInput.value.split('(');
      strategy = (parts[1] ? parts[1].replace(')', '').trim() : '') || '';
    }
    var stockCode = getStockCodeInput();
    var startDate = document.getElementById('startDate').value;
    var endDate = document.getElementById('endDate').value;
    var initialCash = document.getElementById('initialCash').value;
    var dataSource = document.getElementById('dataSource').value;

    if (!strategy) {
      alert('请选择策略文件');
      return;
    }

    if (!stockCode) {
      alert('请选择或输入股票代码');
      return;
    }

    var btn = document.getElementById('runBtn');
    var status = document.getElementById('status');
    var log = document.getElementById('log');

    btn.disabled = true;
    status.innerHTML = '<span class="status running">运行中...</span>';
    log.textContent = '正在启动回测...\n策略: ' + strategy + '\n股票: ' + stockCode + '\n数据源: ' + dataSource + '\n';

    try {
      var res = await fetch('/api/run_backtest', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          strategy: strategy,
          stockCode: stockCode,
          startDate: startDate,
          endDate: endDate,
          timeframe: (document.getElementById('timeframe') && document.getElementById('timeframe').value) || 'D',
          initialCash: initialCash,
          dataSource: dataSource
        })
      });

      var data = await res.json().catch(function() { return {}; });
      if (!res.ok) {
        status.innerHTML = '<span class="status error">错误</span>';
        log.textContent = (data.error || data.message || ('HTTP ' + res.status + ': ' + res.statusText));
        return;
      }
      if (data.success) {
        status.innerHTML = '<span class="status success">回测完成</span>';
        log.textContent = data.log || '回测完成！';
        if (data.result) {
          var card = document.getElementById('resultCard');
          var sumEl = document.getElementById('resultSummary');
          var curveEl = document.getElementById('resultCurve');
          var infoEl = document.getElementById('resultStrategyInfo');
          card.style.display = 'block';
          if (infoEl) {
            var sn = data.result.strategy_name || '';
            var tf = data.result.timeframe || 'D';
            var tfLabel = tf === 'W' ? '周线' : (tf === 'M' ? '月线' : '日线');
            var isPortfolio = data.result.is_portfolio === true;
            var stockCodes = data.result.stock_codes;
            var line1 = '策略: ' + sn + '　周期: ' + tfLabel;
            if (isPortfolio) {
              line1 += '　多股票组合';
              if (stockCodes && stockCodes.length > 0) {
                infoEl.innerHTML = line1 + '<br><span style="color:#888;font-size:12px;">标的: ' + stockCodes.slice(0, 10).join(', ') + (stockCodes.length > 10 ? ' ...' : '') + '</span>';
              } else {
                infoEl.textContent = line1;
              }
            } else {
              infoEl.textContent = line1;
            }
            infoEl.style.display = (sn || tf) ? 'block' : 'none';
          }
          var s = data.result.summary || {};
          var showKeys = [
            ['return_rate', '总收益率', true], ['annualized_returns', '年化收益', true], ['max_drawdown', '最大回撤', true], ['sharpe_ratio', '夏普比率', false]
          ];
          var seen = {};
          sumEl.innerHTML = showKeys.map(function(arr) {
            var k = arr[0], label = arr[1], pct = arr[2];
            if (seen[label]) return '';
            var v = s[k];
            if (v == null && k === 'return_rate') v = s['total_returns'];
            if (v == null) return '';
            seen[label] = true;
            if (typeof v === 'number' && pct) v = (v * 100).toFixed(2) + '%';
            else if (typeof v === 'number') v = (v).toFixed(3);
            return '<div style="background:#1a2744;padding:10px;border-radius:4px;"><span style="color:#888;font-size:12px;">' + label + '</span><br><span style="color:#0f9;">' + v + '</span></div>';
          }).join('');
          var curve = data.result.curve || [];
          var vals = curve.map(function(p) { return p.value; }).filter(function(v) { return v != null && v === v; });
          if (curve.length > 0 && vals.length > 0) {
            var min = Math.min.apply(null, vals);
            var max = Math.max.apply(null, vals);
            var range = max - min || 1;
            var w = curveEl.offsetWidth || 600;
            var h = 200;
            var pad = 20;
            var points = curve.map(function(p, i) {
              var x = pad + (w - 2 * pad) * (i / (curve.length - 1 || 1));
              var v = p.value != null && p.value === p.value ? p.value : (vals[0]);
              var y = h - pad - (h - 2 * pad) * ((v - min) / range);
              return x + ',' + y;
            }).join(' ');
            curveEl.innerHTML = '<svg width="100%" height="' + h + '" viewBox="0 0 ' + w + ' ' + h + '"><polyline fill="none" stroke="#0f9" stroke-width="1.5" points="' + points + '"/></svg>';
          } else {
            curveEl.innerHTML = '<div style="padding:20px;color:#888;">无净值曲线数据</div>';
          }
          renderCockpit(data.result);
          updateDecisionPanel(data.result);
        } else {
          var card = document.getElementById('resultCard');
          if (card) card.style.display = 'none';
        }
      } else {
        status.innerHTML = '<span class="status error">回测失败</span>';
        log.textContent = data.error || '回测失败';
      }
    } catch (e) {
      status.innerHTML = '<span class="status error">错误</span>';
      log.textContent = '错误: ' + e.message;
    } finally {
      btn.disabled = false;
    }
  }

  async function loadStrategy() {
    try {
      var path = document.getElementById('editPath').value;
      if (!path) {
        alert('请输入策略文件路径');
        return;
      }

      var res = await fetch('/api/strategy/' + encodeURIComponent(path));
      if (!res.ok) {
        throw new Error('HTTP ' + res.status);
      }
      var data = await res.json();

      if (data.success) {
        document.getElementById('strategyCode').value = data.content;
      } else {
        alert('加载失败: ' + (data.error || '未知错误'));
      }
    } catch (e) {
      handleError(e, 'loadStrategy');
      alert('加载失败: ' + e.message);
    }
  }

  async function saveStrategy() {
    try {
      var path = document.getElementById('editPath').value;
      var code = document.getElementById('strategyCode').value;

      if (!path || !code) {
        alert('请填写文件路径和代码');
        return;
      }

      var res = await fetch('/api/strategy', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({path: path, content: code})
      });

      if (!res.ok) {
        throw new Error('HTTP ' + res.status);
      }

      var data = await res.json();
      if (data.success) {
        alert('保存成功！');
        loadStrategies();
      } else {
        alert('保存失败: ' + (data.error || '未知错误'));
      }
    } catch (e) {
      handleError(e, 'saveStrategy');
      alert('保存失败: ' + e.message);
    }
  }

  async function syncStockData() {
    var stockCode = getStockCodeInput();
    if (!stockCode) {
      alert('请选择或输入股票代码');
      return;
    }

    var symbol = stockCode.split('.')[0];
    var log = document.getElementById('log');
    log.textContent = '正在同步 ' + symbol + ' 的数据...\n';

    try {
      var res = await fetch('/api/sync_stock', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({symbol: symbol, days: 730})
      });
      var data = await res.json();
      if (data.success) {
        log.textContent = data.message ? (data.message + '\n') : '同步成功\n';
        if (typeof loadStocks === 'function') loadStocks();
      } else {
        log.textContent = (data.error || '失败') + '\n';
      }
    } catch (e) {
      log.textContent = '同步失败: ' + (e.message || e) + '\n';
    }
  }

  async function syncPoolStocks() {
    var log = document.getElementById('log');
    var btn = document.getElementById('syncPoolBtn');
    var startDate = document.getElementById('startDate').value.replace(/-/g, '');
    var endDate = document.getElementById('endDate').value.replace(/-/g, '');
    log.textContent = '正在全量同步股票池（根据 data/ 下 CSV），请稍候…\n';
    if (btn) btn.disabled = true;
    try {
      var res = await fetch('/api/sync_pool', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({startDate: startDate || null, endDate: endDate || null})
      });
      var data = await res.json();
      if (data.success) {
        log.textContent = (data.log || '') + '\n' + (data.message || '✅ 完成');
        if (typeof loadStocks === 'function') loadStocks();
      } else {
        log.textContent = (data.log || '') + '\n❌ ' + (data.error || '失败');
      }
    } catch (e) {
      log.textContent = '❌ 请求失败: ' + e.message;
    }
    if (btn) btn.disabled = false;
  }

  window.loadStrategies = loadStrategies;
  window.loadStocks = loadStocks;
  window.runBacktest = runBacktest;
  window.scanMarket = scanMarket;
  window.optimizeParams = optimizeParams;
  window.runPortfolioBacktest = runPortfolioBacktest;
  window.syncStockData = syncStockData;
  window.syncPoolStocks = syncPoolStocks;
  window.loadStrategy = loadStrategy;
  window.saveStrategy = saveStrategy;

  window.addEventListener('resize', function() {
    if (cockpitKlineChart) cockpitKlineChart.resize();
    if (cockpitCurveChart) cockpitCurveChart.resize();
  });

  function setupStockInputHandlers() {
    var custom = document.getElementById('customStockCode');
    var select = document.getElementById('stockCode');
    var clearBtn = document.getElementById('clearStockBtn');
    if (clearBtn && custom) {
      clearBtn.onclick = function() {
        custom.value = '';
        if (select) select.value = '';
        custom.focus();
      };
    }
    if (select && custom) {
      select.addEventListener('change', function() {
        var v = select.value;
        if (v && v.indexOf('.') >= 0) custom.value = v.split('.')[0];
      });
    }
    if (custom) {
      custom.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
          e.preventDefault();
          if (typeof runBacktest === 'function') runBacktest();
        }
      });
    }
  }

  function init() {
    try {
      var loadBtn = document.getElementById('loadBtn');
      if (loadBtn) loadBtn.addEventListener('click', loadStrategy);
      setupStockInputHandlers();
      loadStrategies();
      loadStocks();
    } catch (e) {
      console.error('init error', e);
      var log = document.getElementById('log');
      if (log) log.textContent = '页面初始化异常: ' + (e.message || e);
    }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    setTimeout(init, 0);
  }
})();
