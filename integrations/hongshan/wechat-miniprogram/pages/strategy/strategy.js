const { getToken } = require('../../utils/auth.js');
const config = require('../../config.js');

Page({
  data: {
    guest: true,
    publicBrowse: true,
  },
  onShow() {
    this.setData({
      guest: !getToken(),
      publicBrowse: config.publicBrowseMode !== false,
    });
  },
  onSettings() {
    wx.switchTab({ url: '/pages/mine/mine' });
  },
  onBell() {
    wx.showToast({ title: '分享', icon: 'none' });
  },
  onUpgrade() {
    wx.showModal({
      title: '专业版',
      content: '请联系管理员开通或与 Web 端账户权益同步（后续可接支付）。',
      showCancel: false,
    });
  },
  onContact() {
    wx.showToast({ title: '请通过 Web 端或企业微信联系', icon: 'none' });
  },
  onStart() {
    wx.switchTab({ url: '/pages/index/index' });
  },
  goMine() {
    wx.switchTab({ url: '/pages/mine/mine' });
  },
});
