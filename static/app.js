(function() {
  var selectedStrategy = '';
  var cockpitKlineChart = null;
  var cockpitCurveChart = null;

  function handleError(error, context) {
    try {
      var log = document.getElementById('log');
      if (log) log.textContent = '错误: ' + (error.message || error.toString());
    } catch (e) {}
  }

  function renderCockpit(result) {
    if (!result) return;
    var cockpitEl = document.getElementById('resultCockpit');
    var klineEl = document.getElementById('resultKline');
    var curveCompareEl = document.getElementById('resultCurveCompare');
    var signalReasonEl = document.getElementById('resultSignalReason');
    if (!cockpitEl || !klineEl || !curveCompareEl) return;
    if (cockpitKlineChart) { cockpitKlineChart.dispose(); cockpitKlineChart = null; }
    if (cockpitCurveChart) { cockpitCurveChart.dispose(); cockpitCurveChart = null; }
    var hasKline = result.kline && result.kline.length > 0;
    var hasHold = result.holdCurve && result.holdCurve.length > 0 && result.curve && result.curve.length > 0;
    if (!hasKline && !hasHold) {
      cockpitEl.style.display = 'none';
      return;
    }
    cockpitEl.style.display = 'block';
    if (typeof echarts === 'undefined') return;
    var dark = { backgroundColor: 'transparent', textStyle: { color: '#888' } };
    if (hasKline) {
      var kline = result.kline;
      var dates = kline.map(function(k) { return k.date; });
      var ohlc = kline.map(function(k) { return [k.open, k.close, k.low, k.high]; });
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
      var opt = {
        backgroundColor: 'transparent',
        grid: { left: 48, right: 24, top: 24, bottom: 32 },
        xAxis: { type: 'category', data: dates, axisLabel: { color: '#888', fontSize: 10 }, splitLine: { show: false } },
        yAxis: { type: 'value', scale: true, axisLabel: { color: '#888' }, splitLine: { lineStyle: { color: '#2a2a4a' } } },
        series: [
          { type: 'candlestick', data: ohlc, itemStyle: { color: '#0f9', borderColor: '#0f9', color0: '#f55', borderColor0: '#f55' }, markArea: markArea.length ? { silent: true, data: markArea } : undefined }
        ]
      };
      cockpitKlineChart = echarts.init(klineEl);
      cockpitKlineChart.setOption(opt);
    }
    if (hasHold) {
      var curve = result.curve;
      var holdCurve = result.holdCurve;
      var curveDates = curve.map(function(p) { return p.date; });
      var curveVals = curve.map(function(p) { return p.value; });
      var holdMap = {};
      (holdCurve || []).forEach(function(p) { holdMap[p.date] = p.value; });
      var holdVals = curveDates.map(function(d) { return holdMap[d] != null ? holdMap[d] : null; });
      cockpitCurveChart = echarts.init(curveCompareEl);
      cockpitCurveChart.setOption({
        backgroundColor: 'transparent',
        grid: { left: 48, right: 24, top: 24, bottom: 32 },
        legend: { data: ['策略净值', '持有净值'], textStyle: { color: '#888' }, top: 0 },
        xAxis: { type: 'category', data: curveDates, axisLabel: { color: '#888', fontSize: 10 } },
        yAxis: { type: 'value', scale: true, axisLabel: { color: '#888' }, splitLine: { lineStyle: { color: '#2a2a4a' } } },
        series: [
          { name: '策略净值', type: 'line', data: curveVals, smooth: true, symbol: 'none', lineStyle: { color: '#0f9' } },
          { name: '持有净值', type: 'line', data: holdVals, smooth: true, symbol: 'none', lineStyle: { color: '#f90' } }
        ]
      });
    }
    var futureTrendEl = document.getElementById('resultFutureTrend');
    var futureProbEl = document.getElementById('resultFutureProb');
    var futureRangeEl = document.getElementById('resultFutureRange');
    if (futureTrendEl && futureProbEl && futureRangeEl) {
      var prob = result.futureProbability;
      var range = result.futurePriceRange;
      var hasProb = prob && (prob.up != null || prob.sideways != null || prob.down != null);
      var hasRange = range && range.low != null && range.high != null;
      if (hasProb || hasRange) {
        futureTrendEl.style.display = 'block';
        if (hasProb) {
          var up = (prob.up != null ? Math.round(prob.up * 100) : 0);
          var side = (prob.sideways != null ? Math.round(prob.sideways * 100) : 0);
          var down = (prob.down != null ? Math.round(prob.down * 100) : 0);
          futureProbEl.innerHTML = '<span style="color:#0f9;">上涨 ' + up + '%</span><span style="color:#888;">震荡 ' + side + '%</span><span style="color:#f55;">下跌 ' + down + '%</span>';
        } else futureProbEl.innerHTML = '';
        if (hasRange) {
          futureRangeEl.textContent = '预计区间（' + (range.horizonDays || 5) + ' 日）: ' + range.low + ' — ' + range.high;
        } else futureRangeEl.textContent = '';
      } else {
        futureTrendEl.style.display = 'none';
      }
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
              if (s.type === 'buy') parts.push('买入信号');
              else parts.push('卖出信号');
              parts.push('日期: ' + s.date);
              if (s.reasons && s.reasons.length) parts.push('原因: ' + s.reasons.join('；'));
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

  async function loadStrategies() {
    try {
      var res = await fetch('/api/strategies');
      if (!res.ok) {
        throw new Error('HTTP ' + res.status + ': ' + res.statusText);
      }
      var data = await res.json();
      var list = document.getElementById('strategyList');
      var select = document.getElementById('strategyFile');

      list.innerHTML = '';
      select.innerHTML = '<option value="">请选择策略</option>';

      data.strategies.forEach(function(s) {
        var file = s.file || s;
        var name = s.name || file;
        var desc = s.description || '';
        var li = document.createElement('li');
        li.className = 'strategy-item';
        li.title = desc;
        var safeName = (name || '').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        var safeDesc = (desc + '').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        li.innerHTML = '<strong>' + safeName + '</strong>' + (desc ? '<br><span class="strategy-desc">' + safeDesc + '</span>' : '');
        li.onclick = function() {
          document.querySelectorAll('.strategy-item').forEach(function(el) { el.classList.remove('active'); });
          li.classList.add('active');
          selectedStrategy = file;
          document.getElementById('strategyFile').value = name + ' (' + file + ')';
          document.getElementById('strategyFile').setAttribute('data-file', file);
        };
        list.appendChild(li);
      });
    } catch (e) {
      handleError(e, 'loadStrategies');
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

      select.innerHTML = '<option value="">请选择股票</option>';

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
    var stockCode = document.getElementById('stockCode').value;
    var customStockCode = document.getElementById('customStockCode').value.trim();
    var startDate = document.getElementById('startDate').value;
    var endDate = document.getElementById('endDate').value;
    var initialCash = document.getElementById('initialCash').value;
    var dataSource = document.getElementById('dataSource').value;

    if (!strategy) {
      alert('请选择策略文件');
      return;
    }

    if (customStockCode) {
      stockCode = customStockCode;
      if (!stockCode.includes('.')) {
        stockCode = stockCode + (stockCode.startsWith('6') ? '.XSHG' : '.XSHE');
      }
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
          card.style.display = 'block';
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
    var stockCode = document.getElementById('stockCode').value || document.getElementById('customStockCode').value.trim();
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
  window.syncStockData = syncStockData;
  window.syncPoolStocks = syncPoolStocks;
  window.loadStrategy = loadStrategy;
  window.saveStrategy = saveStrategy;

  window.addEventListener('resize', function() {
    if (cockpitKlineChart) cockpitKlineChart.resize();
    if (cockpitCurveChart) cockpitCurveChart.resize();
  });

  document.addEventListener('DOMContentLoaded', function() {
    var loadBtn = document.getElementById('loadBtn');
    if (loadBtn) loadBtn.addEventListener('click', loadStrategy);
    loadStrategies();
    loadStocks();
  });
})();
