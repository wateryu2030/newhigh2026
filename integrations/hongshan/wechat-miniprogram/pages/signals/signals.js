const { request } = require('../../utils/request.js');

Page({
  data: {
    loading: true,
    error: '',
    items: [],
  },

  onShow() {
    void this.load();
  },

  onBack() {
    wx.navigateBack({ delta: 1 });
  },

  async load() {
    this.setData({ loading: true, error: '' });
    try {
      const body = await request({
        url: '/api/strategy/signals',
        data: { limit: 80 },
        redirectOn401: false,
      });
      const arr = Array.isArray(body) ? body : [];
      const items = arr.map((item, idx) => {
        const chg = item.change_pct;
        let pctStr = '';
        if (chg != null && chg !== '') {
          const n = Number(chg);
          pctStr = `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;
        }
        return {
          k: `${item.code || ''}-${idx}`,
          code: item.code || '',
          stock_name: item.stock_name || '',
          signal: item.signal || '',
          strategy_id: item.strategy_id || '',
          updated_at: item.updated_at || '',
          change_pct: chg,
          pctStr,
        };
      });
      this.setData({ loading: false, items });
    } catch (e) {
      this.setData({
        loading: false,
        error: '加载失败',
        items: [],
      });
    }
  },
});
