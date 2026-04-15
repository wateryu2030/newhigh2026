const { request } = require('../../utils/request.js');
const { getToken } = require('../../utils/auth.js');
const config = require('../../config.js');

function pickSummary(data) {
  if (!data || typeof data !== 'object') return JSON.stringify(data, null, 2);
  if (data.summary) return String(data.summary);
  if (data.answer) return String(data.answer);
  if (data.markdown) return String(data.markdown);
  return JSON.stringify(data, null, 2).slice(0, 8000);
}

Page({
  data: {
    text: '',
    loading: false,
    result: '',
    folded: false,
    quotaText: '',
    submitDisabled: false,
    publicBrowse: true,
  },

  onShow() {
    const open = config.publicBrowseMode !== false;
    this.setData({ publicBrowse: open });
    if (!open && !getToken()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }
    void this.loadQuota();
  },

  onBack() {
    wx.navigateBack({ delta: 1 });
  },

  onInp(e) {
    this.setData({ text: e.detail.value || '' });
  },

  toggleFold() {
    this.setData({ folded: !this.data.folded });
  },

  async loadQuota() {
    if (!getToken()) {
      if (config.publicBrowseMode !== false) {
        this.setData({
          quotaText: '正式上架并登录后可查看配额并提交分析',
          submitDisabled: true,
        });
      }
      return;
    }
    try {
      const body = await request({ url: '/api/user/quota', redirectOn401: false });
      const d = (body && body.data) || body;
      const sq = (d && d.stock_qa) || {};
      const used = sq.used != null ? sq.used : 0;
      const limit = sq.limit != null ? sq.limit : '—';
      const ul = (d && d.user_level) || '';
      this.setData({
        quotaText: `今日问答：${used} / ${limit}${ul ? ` · 级别 ${ul}` : ''}`,
        submitDisabled: Number(used) >= Number(limit) && limit !== '—',
      });
    } catch {
      this.setData({ quotaText: '', submitDisabled: false });
    }
  },

  async onAsk() {
    if (!getToken()) {
      wx.showModal({
        title: '提示',
        content: '正式上架并登录后可使用股票问答分析。',
        showCancel: false,
      });
      return;
    }
    const raw = (this.data.text || '').trim();
    if (!raw) {
      wx.showToast({ title: '请输入内容', icon: 'none' });
      return;
    }
    wx.showLoading({ title: '分析中' });
    this.setData({ loading: true });
    try {
      const body = await request({
        url: '/api/stock-qa/analyze',
        method: 'POST',
        data: { text: raw, max_symbols: 8, use_llm_analysis: false },
      });
      const d = (body && body.data) || body;
      if (body && body.ok === false) {
        wx.showToast({ title: (body.error || '失败').slice(0, 18), icon: 'none' });
        return;
      }
      this.setData({
        result: pickSummary(d),
        folded: true,
      });
      void this.loadQuota();
    } catch (e) {
      const msg = (e && e.message) || '请求失败';
      wx.showToast({ title: msg.slice(0, 18), icon: 'none' });
    } finally {
      wx.hideLoading();
      this.setData({ loading: false });
    }
  },
});
