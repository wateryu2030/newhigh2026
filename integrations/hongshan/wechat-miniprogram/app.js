// 红山量化 — 小程序入口
const config = require('./config.js');
const { defaultApiBase, applyApiBaseFromStorage } = require('./utils/api-base.js');

App({
  globalData: {
    apiBase: defaultApiBase(),
    appName: '红山量化',
    userLevel: 'trial',
    /** 与 config.publicBrowseMode 同步：开放浏览期不强制登录看首页 */
    publicBrowseMode: config.publicBrowseMode !== false,
  },
  onLaunch() {
    applyApiBaseFromStorage(this);
    try {
      const lv = wx.getStorageSync('user_level');
      if (lv) this.globalData.userLevel = String(lv);
    } catch {
      /* ignore */
    }
  },
});
