const { request } = require('../../utils/request.js');

Page({
  data: {
    symbol: '',
    titleStr: '行情详情',
    loading: true,
    error: '',
    rows: [],
  },

  onLoad(q) {
    const sym = decodeURIComponent(q.symbol || '').trim().slice(0, 8);
    if (!sym) {
      this.setData({ loading: false, error: '缺少代码' });
      return;
    }
    this.setData({ symbol: sym, titleStr: sym });
    void this.loadK(sym);
  },

  onBack() {
    wx.navigateBack({ delta: 1 });
  },

  async loadK(symbol) {
    this.setData({ loading: true, error: '' });
    try {
      const body = await request({
        url: '/api/market/klines',
        data: { symbol, interval: '1d', limit: 120 },
        redirectOn401: false,
      });
      const pay = (body && body.data) || body;
      const arr = (pay && pay.data) || [];
      const rows = arr
        .map((bar) => {
          const c = bar.c != null ? Number(bar.c) : bar.close != null ? Number(bar.close) : null;
          const t = bar.t || '';
          const v = bar.v != null ? Number(bar.v) : null;
          return {
            d: String(t).slice(0, 10),
            c: c != null && !Number.isNaN(c) ? c.toFixed(3) : '—',
            v:
              v != null && !Number.isNaN(v)
                ? v >= 1e8
                  ? `${(v / 1e8).toFixed(2)}亿`
                  : v >= 1e4
                    ? `${(v / 1e4).toFixed(1)}万`
                    : String(Math.round(v))
                : '—',
          };
        })
        .reverse();
      this.setData({ loading: false, rows });
    } catch (e) {
      this.setData({
        loading: false,
        error: '加载失败',
        rows: [],
      });
    }
  },
});
