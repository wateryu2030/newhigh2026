const { DESKTOP_SYNC } = require('../../config/menu.js');
const { EXTRA_WEB_PARITY } = require('../../config/extra_web_paths.js');
const { navigateMenuItem } = require('../../utils/menu-nav.js');

Page({
  data: {
    items: DESKTOP_SYNC.concat(EXTRA_WEB_PARITY),
  },

  onTapItem(e) {
    const idx = Number(e.currentTarget.dataset.index);
    const row = this.data.items[idx];
    if (!row) return;
    navigateMenuItem(row);
  },

  onBack() {
    wx.navigateBack({ fail: () => wx.switchTab({ url: '/pages/index/index' }) });
  },
});
