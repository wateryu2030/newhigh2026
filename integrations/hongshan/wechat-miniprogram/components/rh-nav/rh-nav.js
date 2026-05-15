const { getWindowMetrics } = require('../../utils/window-metrics.js');

Component({
  properties: {
    title: { type: String, value: '红山量化' },
    showBack: { type: Boolean, value: false },
    showBell: { type: Boolean, value: true },
    showSettings: { type: Boolean, value: true },
  },
  data: {
    statusBarHeight: 20,
    navBarHeight: 44,
  },
  lifetimes: {
    attached() {
      const sys = getWindowMetrics();
      const menu = wx.getMenuButtonBoundingClientRect
        ? wx.getMenuButtonBoundingClientRect()
        : null;
      let navBarHeight = 44;
      if (menu && menu.top && menu.height) {
        navBarHeight = (menu.top - sys.statusBarHeight) * 2 + menu.height;
      }
      this.setData({
        statusBarHeight: sys.statusBarHeight || 20,
        navBarHeight,
      });
    },
  },
  methods: {
    onBell() {
      this.triggerEvent('bell');
    },
    onSettings() {
      this.triggerEvent('settings');
    },
    onBack() {
      this.triggerEvent('back');
    },
  },
});
