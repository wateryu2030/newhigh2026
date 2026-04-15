const CACHE_KEY = 'news_detail_cache';

Page({
  data: {
    title: '',
    meta: '',
    content: '',
    url: '',
  },

  onLoad() {
    try {
      const item = wx.getStorageSync(CACHE_KEY) || {};
      const title = item.title || '资讯';
      const pub = item.publish_time || '';
      const source = item.source || '';
      const meta = [pub, source].filter(Boolean).join(' · ');
      this.setData({
        title,
        meta,
        content: (item.content || '').slice(0, 4000),
        url: (item.url || '').trim(),
      });
    } catch {
      this.setData({ title: '资讯' });
    }
  },

  openUrl() {
    const u = this.data.url;
    if (!u) return;
    wx.setClipboardData({
      data: u,
      success: () => {
        wx.showModal({
          title: '链接已复制',
          content: '请在系统浏览器中粘贴打开（部分域名需业务配置 web-view）。',
          showCancel: false,
        });
      },
    });
  },
});
