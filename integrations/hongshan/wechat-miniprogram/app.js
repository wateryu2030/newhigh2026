// 红山量化 — 小程序入口
const config = require('./config.js');

App({
  globalData: {
    apiBase: config.apiBase,
    appName: '红山量化',
    userLevel: 'trial',
    /** 与 config.publicBrowseMode 同步：开放浏览期不强制登录看首页 */
    publicBrowseMode: config.publicBrowseMode !== false,
  },
  onLaunch() {
    const base = wx.getStorageSync('api_base_override');
    if (typeof base === 'string' && base.startsWith('https://')) {
      this.globalData.apiBase = base.replace(/\/$/, '');
    }
    try {
      const lv = wx.getStorageSync('user_level');
      if (lv) this.globalData.userLevel = String(lv);
    } catch {
      /* ignore */
    }
  },
});
