const { BASE, copyWebPath } = require('../../utils/htma.js');

Page({
  data: {
    url: '',
    err: '',
  },

  onLoad(query) {
    const raw = query.path ? decodeURIComponent(query.path) : '/';
    let url = raw;
    if (!raw.startsWith('http://') && !raw.startsWith('https://')) {
      url = BASE + (raw.startsWith('/') ? raw : `/${raw}`);
    }
    if (!url || url === BASE) {
      this.setData({ err: '无效地址' });
      return;
    }
    this.setData({ url });
    const title = raw.length > 24 ? `${raw.slice(0, 22)}…` : raw.replace(BASE, '') || 'Web';
    wx.setNavigationBarTitle({ title: title.slice(0, 32) });
  },

  onWebError() {
    this.setData({ err: '页面无法内嵌打开（请检查公众平台「业务域名」是否包含 htma.newhigh.com.cn）' });
  },

  onCopy() {
    const u = this.data.url;
    if (u) copyWebPath(u.replace(BASE, '') || '/');
  },
});
