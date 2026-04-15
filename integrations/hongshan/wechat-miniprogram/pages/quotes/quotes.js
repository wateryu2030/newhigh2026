const { request } = require('../../utils/request.js');

const DEFAULT_CODES = ['000001', '600519', '300750', '601318'];
const WATCH_KEY = 'watchlist_codes';

function loadWatchlist() {
  try {
    const raw = wx.getStorageSync(WATCH_KEY);
    if (Array.isArray(raw) && raw.length) return raw.map((x) => String(x).slice(0, 6));
  } catch {
    /* ignore */
  }
  return DEFAULT_CODES.slice();
}

function saveWatchlist(codes) {
  try {
    wx.setStorageSync(WATCH_KEY, codes);
  } catch {
    /* ignore */
  }
}

Page({
  data: {
    tabLabels: ['自选', '示例'],
    tabIndex: 0,
    keyword: '',
    loading: true,
    error: '',
    list: [],
    displayList: [],
  },

  onShow() {
    void this.refresh();
  },

  noop() {},

  onTab(e) {
    const i = Number(e.detail.value || 0);
    this.setData({ tabIndex: i });
    void this.refresh();
  },

  onKw(e) {
    this.setData({ keyword: (e.detail.value || '').trim() });
  },

  async onSearch() {
    const kw = this.data.keyword;
    if (!kw) {
      void this.refresh();
      return;
    }
    wx.showLoading({ title: '搜索' });
    try {
      const body = await request({
        url: '/api/stocks/search',
        data: { keyword: kw },
        redirectOn401: false,
      });
      const rows = (body && body.data) || [];
      if (!rows.length) {
        wx.showToast({ title: '未找到', icon: 'none' });
        return;
      }
      const symbols = rows.map((r) => r.symbol).filter(Boolean);
      const sym = symbols[0];
      let codes = loadWatchlist();
      if (this.data.tabIndex === 0 && sym && codes.indexOf(sym) < 0) {
        codes = [sym].concat(codes).slice(0, 50);
        saveWatchlist(codes);
      }
      await this.loadQuotes(sym ? [sym] : symbols.slice(0, 5));
    } catch (err) {
      wx.showToast({ title: '搜索失败', icon: 'none' });
    } finally {
      wx.hideLoading();
    }
  },

  async refresh() {
    this.setData({ loading: true, error: '' });
    try {
      const codes =
        this.data.tabIndex === 0 ? loadWatchlist() : DEFAULT_CODES;
      await this.loadQuotes(codes);
    } catch (e) {
      this.setData({
        loading: false,
        error: '加载失败，请检查网络与合法域名配置',
        list: [],
        displayList: [],
      });
    }
  },

  async loadQuotes(codes) {
    if (!codes || !codes.length) {
      this.setData({ loading: false, list: [], displayList: [] });
      return;
    }
    const symbols = codes.join(',');
    const body = await request({
      url: '/api/stocks/quotes',
      data: { symbols },
      redirectOn401: false,
    });
    const quotes = (body && body.quotes) || [];
    const displayList = quotes.map((q) => {
      const p = q.current_price != null ? Number(q.current_price) : null;
      const chg = q.change_percent != null ? Number(q.change_percent) : 0;
      return {
        symbol: String(q.symbol || ''),
        name: String(q.name || ''),
        priceStr: p != null && !Number.isNaN(p) ? p.toFixed(2) : '—',
        pctStr: `${chg >= 0 ? '+' : ''}${chg.toFixed(2)}%`,
        chgClass: chg >= 0 ? 'up' : 'down',
      };
    });
    this.setData({ loading: false, list: quotes, displayList });
  },

  goDetail(e) {
    const sym = e.currentTarget.dataset.symbol;
    if (!sym) return;
    wx.navigateTo({
      url: `/pages/quote-detail/quote-detail?symbol=${encodeURIComponent(sym)}`,
    });
  },
});
