const { request } = require('../../utils/request.js');
const { getPixelRatio } = require('../../utils/window-metrics.js');
const { getToken } = require('../../utils/auth.js');
const { formatWanYuan, formatPct, formatTime } = require('../../utils/format.js');
const config = require('../../config.js');

function isPublicBrowse() {
  try {
    const app = getApp();
    if (app && app.globalData && app.globalData.publicBrowseMode === false) return false;
  } catch {
    /* ignore */
  }
  return config.publicBrowseMode !== false;
}

function mapEmotion(row) {
  if (!row) {
    return {
      title: '—',
      desc: '情绪数据加载中',
      reaction: 'HOLD',
    };
  }
  const stage = String(row.stage || row.state || '').trim();
  const score = row.score != null ? Number(row.score) : null;
  let title = stage || '观测中';
  if (/冰|低|冷/i.test(stage) || (score != null && score < 35)) title = '冰点周期';
  else if (/沸|高|热/i.test(stage) || (score != null && score > 70)) title = '高潮周期';
  const desc =
    score != null
      ? `全市场评分约 ${score.toFixed(0)}，涨停家数 ${row.limit_up_count ?? '—'}`
      : '基于涨跌停与市场宽度等维度的综合状态';
  let reaction = 'HOLD';
  if (/冰点|恐慌|退潮/i.test(title)) reaction = 'WAIT';
  if (/主升|高潮|一致/i.test(title)) reaction = 'CAUTION';
  return { title, desc, reaction };
}

Page({
  data: {
    alertText: '市场波动加剧，请注意仓位与风控；数据仅供参考，不构成投资建议。',
    totalAssetsStr: '¥—',
    dailyPct: 0,
    dailyPctStr: '+0.00%',
    sharpeStr: '—',
    maxDdStr: '—',
    maxDdPct: 0,
    perfTab: '1d',
    axisLabels: ['09:30', '11:30', '15:00'],
    emotionTitle: '冰点周期',
    emotionDesc: '情绪偏弱，资金观望',
    emotionReaction: 'HOLD',
    alphaList: [],
    signals: [],
    equitySeries: [],
    guest: false,
    publicBrowse: true,
    openTip:
      '当前为开放浏览：可查看平台公开数据与资讯，仅供参考。正式上架后将支持账户登录与个性化能力。',
  },

  onShow() {
    this.setData({ publicBrowse: isPublicBrowse() });
    void this.loadAll();
    wx.nextTick(() => {
      if (this._pendingDraw) {
        this._drawEquity(this._pendingDraw);
        this._pendingDraw = null;
      }
    });
  },

  onPullDownRefresh() {
    this.loadAll().finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  onNavSettings() {
    wx.switchTab({ url: '/pages/mine/mine' });
  },

  onNavBell() {
    wx.showToast({ title: '消息中心', icon: 'none' });
  },

  onPerfTab(e) {
    const t = e.currentTarget.dataset.t;
    if (t) this.setData({ perfTab: t });
  },

  noop() {},

  goStrategy() {
    wx.switchTab({ url: '/pages/strategy/strategy' });
  },

  goMineLogin() {
    wx.switchTab({ url: '/pages/mine/mine' });
  },

  goQuotes() {
    wx.navigateTo({ url: '/pages/quotes/quotes' });
  },

  goStockQA() {
    wx.navigateTo({ url: '/pages/stock-qa/stock-qa' });
  },

  goSignals() {
    wx.navigateTo({ url: '/pages/signals/signals' });
  },

  goBlockTrade() {
    wx.navigateTo({ url: '/pages/block-trade/block-trade' });
  },

  goNewsTab() {
    wx.switchTab({ url: '/pages/news/news' });
  },

  goFeatureHub() {
    wx.navigateTo({ url: '/pages/feature-hub/feature-hub' });
  },

  async loadAll() {
    const token = getToken();
    const open = isPublicBrowse();
    this.setData({
      guest: !token,
      publicBrowse: open,
    });

    if (!open && !token) {
      this.setData({
        signals: [],
        alphaList: [
          { id: 'x', name: '登录后同步策略榜', pctStr: '—' },
          { id: 'y', name: '登录后查看实时信号', pctStr: '—' },
        ],
        emotionTitle: '—',
        emotionDesc: '请先在「我的」使用微信登录',
        emotionReaction: 'LOGIN',
        totalAssetsStr: '¥—',
        dailyPctStr: '—',
        sharpeStr: '—',
        maxDdStr: '—',
        equitySeries: [],
      });
      wx.nextTick(() => this._drawEquity([]));
      return;
    }

    const tasks = [
      request({ url: '/api/dashboard', redirectOn401: false, timeout: 60000 }).catch(() => null),
      request({ url: '/api/market/emotion', redirectOn401: false, timeout: 60000 }).catch(
        () => null,
      ),
      request({
        url: '/api/strategy/signals',
        data: { limit: 12 },
        redirectOn401: false,
        timeout: 60000,
      }).catch(() => null),
    ];
    const [dash, emotion, sigBody] = await Promise.all(tasks);

    let total = 12_300_000;
    let dailyPct = 2.34;
    let sharpe = 1.2;
    let maxDd = -1.22;
    let curve = [10e6, 10.1e6, 10.4e6, 10.9e6, 11.2e6, 12.3e6];

    if (dash && typeof dash === 'object') {
      if (dash.total_equity != null) total = Number(dash.total_equity);
      if (dash.daily_return_pct != null) dailyPct = Number(dash.daily_return_pct);
      if (dash.sharpe_ratio != null) sharpe = Number(dash.sharpe_ratio);
      if (dash.max_drawdown_pct != null) maxDd = Number(dash.max_drawdown_pct);
      if (Array.isArray(dash.equity_curve) && dash.equity_curve.length > 1) {
        curve = dash.equity_curve.map((x) => Number(x));
      }
    }

    const em = mapEmotion(emotion);
    let alphaList = [];
    if (dash && Array.isArray(dash.top_strategies) && dash.top_strategies.length) {
      alphaList = dash.top_strategies.slice(0, 4).map((s) => ({
        id: s.id || s.name,
        name: s.name || s.id || '—',
        pctStr:
          s.return_pct != null
            ? `${Number(s.return_pct) >= 0 ? '+' : ''}${Number(s.return_pct).toFixed(1)}%`
            : '—',
      }));
    } else {
      alphaList = [
        { id: '1', name: 'HS-CTA 3.0', pctStr: '+12.4%' },
        { id: '2', name: 'Chip-Alpha', pctStr: '+8.1%' },
        { id: '3', name: 'Fusion-AI', pctStr: '+5.6%' },
      ];
    }

    let signals = [];
    if (sigBody && Array.isArray(sigBody)) {
      signals = sigBody.map((item, idx) => {
        const sig = String(item.signal || '').toUpperCase();
        let dir = 'LONG';
        let side = 'BUY';
        if (sig === 'SELL') {
          dir = 'SHORT';
          side = 'SELL';
        } else if (sig && sig !== 'BUY') {
          dir = sig.slice(0, 8);
          side = 'HOLD';
        }
        return {
          idx: `${item.code || ''}-${idx}`,
          title: `${item.code} ${item.stock_name || ''}`.trim(),
          meta: `${formatTime(item.updated_at)} · ${item.strategy_id || 'System'}`,
          dir,
          side,
          price: item.last_price != null ? `@${item.last_price}` : '',
        };
      });
    }

    this.setData({
      totalAssetsStr: formatWanYuan(total),
      dailyPct,
      dailyPctStr: formatPct(dailyPct),
      sharpeStr: sharpe != null && !Number.isNaN(sharpe) ? sharpe.toFixed(2) : '—',
      maxDdStr: maxDd != null ? formatPct(maxDd) : '—',
      maxDdPct: maxDd != null ? maxDd : 0,
      emotionTitle: em.title,
      emotionDesc: em.desc,
      emotionReaction: em.reaction,
      alphaList,
      signals,
      equitySeries: curve,
    });

    this._pendingDraw = curve;
    wx.nextTick(() => this._drawEquity(curve));
  },

  _drawEquity(series) {
    if (!series || series.length < 2) {
      const query = wx.createSelectorQuery().in(this);
      query
        .select('#equityCanvas')
        .fields({ node: true, size: true })
        .exec((res) => {
          if (!res || !res[0] || !res[0].node) return;
          const canvas = res[0].node;
          const ctx = canvas.getContext('2d');
          const w = res[0].width;
          const h = res[0].height;
          const dpr = getPixelRatio();
          canvas.width = w * dpr;
          canvas.height = h * dpr;
          ctx.scale(dpr, dpr);
          ctx.fillStyle = '#141a21';
          ctx.fillRect(0, 0, w, h);
          ctx.fillStyle = '#889098';
          ctx.font = '24px sans-serif';
          ctx.textAlign = 'center';
          ctx.fillText('登录后查看收益曲线', w / 2, h / 2);
        });
      return;
    }
    const query = wx.createSelectorQuery().in(this);
    query
      .select('#equityCanvas')
      .fields({ node: true, size: true })
      .exec((res) => {
        if (!res || !res[0] || !res[0].node) return;
        const canvas = res[0].node;
        const ctx = canvas.getContext('2d');
        const w = res[0].width;
        const h = res[0].height;
        const dpr = getPixelRatio();
        canvas.width = w * dpr;
        canvas.height = h * dpr;
        ctx.scale(dpr, dpr);
        ctx.clearRect(0, 0, w, h);
        ctx.fillStyle = '#141a21';
        ctx.fillRect(0, 0, w, h);

        const min = Math.min(...series);
        const max = Math.max(...series);
        const pad = 12;
        const span = max - min || 1;
        const n = series.length;
        const step = (w - pad * 2) / (n - 1);

        ctx.beginPath();
        series.forEach((v, i) => {
          const x = pad + i * step;
          const t = (v - min) / span;
          const y = pad + (1 - t) * (h - pad * 2);
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        });
        const pts = [];
        series.forEach((v, i) => {
          const x = pad + i * step;
          const t = (v - min) / span;
          const y = pad + (1 - t) * (h - pad * 2);
          pts.push({ x, y });
        });

        ctx.beginPath();
        pts.forEach((p, i) => {
          if (i === 0) ctx.moveTo(p.x, p.y);
          else ctx.lineTo(p.x, p.y);
        });
        ctx.strokeStyle = '#ff4444';
        ctx.lineWidth = 2;
        ctx.shadowColor = 'rgba(255,68,68,0.55)';
        ctx.shadowBlur = 10;
        ctx.stroke();
        ctx.shadowBlur = 0;

        const last = pts[pts.length - 1];
        const first = pts[0];
        ctx.beginPath();
        pts.forEach((p, i) => {
          if (i === 0) ctx.moveTo(p.x, p.y);
          else ctx.lineTo(p.x, p.y);
        });
        ctx.lineTo(last.x, h - pad);
        ctx.lineTo(first.x, h - pad);
        ctx.closePath();
        const g = ctx.createLinearGradient(0, 0, 0, h);
        g.addColorStop(0, 'rgba(255,68,68,0.28)');
        g.addColorStop(1, 'rgba(255,68,68,0)');
        ctx.fillStyle = g;
        ctx.fill();
      });
  },
});
