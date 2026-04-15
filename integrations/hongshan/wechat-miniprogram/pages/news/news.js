const { request } = require('../../utils/request.js');

const CACHE_KEY = 'news_detail_cache';
const PAGE_SIZE = 20;

Page({
  data: {
    loading: true,
    skeleton: true,
    loadingMore: false,
    error: '',
    news: [],
    source: '',
    totalHint: '',
    page: 1,
    hasMore: true,
  },

  onLoad() {
    this.loadList(true);
  },

  onPullDownRefresh() {
    this.loadList(true).finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  onReachBottom() {
    if (this.data.loading || this.data.loadingMore || !this.data.hasMore) return;
    void this.loadList(false);
  },

  onBell() {
    wx.showToast({ title: '通知', icon: 'none' });
  },

  async loadList(reset) {
    if (reset) {
      this.setData({
        loading: true,
        skeleton: true,
        error: '',
        page: 1,
        hasMore: true,
      });
    } else {
      this.setData({ loadingMore: true });
    }
    const nextPage = reset ? 1 : this.data.page + 1;
    const limit = nextPage * PAGE_SIZE;
    try {
      const data = await request({
        url: '/api/news',
        data: { limit },
      });
      const list = Array.isArray(data.news) ? data.news : [];
      let totalHint = '';
      if (data.news_items_total != null) {
        totalHint = `站内条目约 ${data.news_items_total} 条`;
      }
      const hasMore = list.length >= limit;
      this.setData({
        news: list,
        source: data.source || '',
        totalHint,
        loading: false,
        skeleton: false,
        loadingMore: false,
        page: nextPage,
        hasMore,
        error: '',
      });
    } catch (e) {
      this.setData({
        loading: false,
        skeleton: false,
        loadingMore: false,
        error:
          '加载失败。请确认：1）微信公众平台已配置 request 合法域名；2）服务端 HTTPS 可访问。',
        news: reset ? [] : this.data.news,
      });
    }
  },

  onOpenItem(e) {
    const idx = e.currentTarget.dataset.index;
    const item = this.data.news[idx];
    if (!item) return;
    try {
      wx.setStorageSync(CACHE_KEY, item);
    } catch {
      /* ignore */
    }
    wx.navigateTo({ url: '/pages/news-detail/news-detail' });
  },
});
