const { tryMiniprogramLogin, getToken } = require('../../utils/auth.js');

Page({
  data: {
    agreed: false,
    loading: false,
  },

  onShow() {
    if (getToken()) {
      wx.switchTab({ url: '/pages/index/index' });
    }
  },

  onAgree(e) {
    const vals = e.detail.value || [];
    this.setData({ agreed: vals.indexOf('1') >= 0 });
  },

  async onLogin() {
    if (!this.data.agreed) {
      wx.showToast({ title: '请先勾选协议', icon: 'none' });
      return;
    }
    this.setData({ loading: true });
    try {
      const d = await tryMiniprogramLogin();
      if (d && (d.token || d.access_token)) {
        wx.showToast({ title: '登录成功', icon: 'success' });
        wx.switchTab({ url: '/pages/index/index' });
      } else {
        wx.showToast({ title: '登录失败，请重试', icon: 'none' });
      }
    } catch (e) {
      const msg = e && e.message ? String(e.message) : '登录失败';
      wx.showToast({ title: msg.length > 36 ? msg.slice(0, 33) + '…' : msg, icon: 'none', duration: 4000 });
    } finally {
      this.setData({ loading: false });
    }
  },
});
