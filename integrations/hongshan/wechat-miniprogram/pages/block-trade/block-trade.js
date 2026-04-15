const { request } = require('../../utils/request.js');

const DEFAULT_QS =
  'block_days=30&lookback_days=60&range_ratio_max=0.32&trend_abs_max=0.12&ret_std_max=0.035&min_amount_wan=0&max_codes=400';

Page({
  data: {
    loading: false,
    error: '',
    note: '',
    rangeHint: '',
    items: [],
  },

  onLoad() {
    void this.runScreen();
  },

  onPullDownRefresh() {
    this.runScreen().finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  onBack() {
    wx.navigateBack({ fail: () => wx.switchTab({ url: '/pages/mine/mine' }) });
  },

  async runScreen() {
    this.setData({ loading: true, error: '', note: '' });
    try {
      const body = await request({
        url: `/api/screen/block-trade-sideways?${DEFAULT_QS}`,
        method: 'GET',
        redirectOn401: false,
        timeout: 120000,
      });
      const payload = body && body.ok === true ? body.data : body;
      const items = (payload && payload.items) || [];
      const blockRange = payload && payload.block_range;
      const hint = blockRange
        ? `${blockRange.start || ''}—${blockRange.end || ''}`
        : '';
      this.setData({
        items: items.map((row) => ({
          code: row.code,
          name: row.name,
          block_amount_wan:
            row.block_amount_wan != null ? Number(row.block_amount_wan).toFixed(2) : '—',
          range_ratio: row.range_ratio != null ? Number(row.range_ratio).toFixed(4) : '—',
        })),
        note: (payload && payload.note) || '',
        rangeHint: hint,
      });
    } catch (e) {
      const msg = e && e.message ? String(e.message) : '加载失败';
      this.setData({ error: msg, items: [] });
    } finally {
      this.setData({ loading: false });
    }
  },

  onRun() {
    void this.runScreen();
  },
});
