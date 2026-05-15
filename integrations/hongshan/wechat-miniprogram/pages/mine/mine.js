const { request } = require('../../utils/request.js');
const {
  tryMiniprogramLogin,
  getToken,
  setToken,
  applyUserLevelFromPayload,
} = require('../../utils/auth.js');
const { canViewFeature } = require('../../utils/permission.js');
const config = require('../../config.js');
const { DESKTOP_SYNC } = require('../../config/menu.js');
const { navigateMenuItem, openWebPath } = require('../../utils/menu-nav.js');
const { resetApiBaseToDefault } = require('../../utils/api-base.js');

Page({
  data: {
    desktopMenu: DESKTOP_SYNC,
    loggedIn: false,
    displayLabel: '未登录用户',
    roleLabel: 'VIEWER',
    userLevelLabel: 'trial',
    quotaHint: '',
    showAiPick: false,
    showDeepFinance: false,
    publicBrowse: true,
    avatarUrl: '',
    agreed: false,
    strategyHint: '4 个运行中',
    reports: [
      {
        id: '1',
        theme: 'a',
        tag: 'ALPHA REPORT',
        title: '2024 Q3 波动率套利策略深度解析',
      },
      {
        id: '2',
        theme: 'b',
        tag: 'TECH INSIGHT',
        title: '低延迟交易基础设施与风控要点',
      },
    ],
  },

  onShow() {
    this.setData({ publicBrowse: config.publicBrowseMode !== false });
    this.refreshProfile();
  },

  async refreshProfile() {
    const token = getToken();
    if (!token) {
      this.setData({
        loggedIn: false,
        displayLabel: '未登录用户',
        avatarUrl: '',
      });
      return;
    }
    try {
      const body = await request({ url: '/api/user/profile' });
      const p = body && body.ok === true ? body.data : body;
      if (p && (p.user_id || p.username)) {
        const name = (p.display_name || p.username || '用户').trim();
        const ul = String(p.user_level || 'trial').toLowerCase();
        applyUserLevelFromPayload({ user_level: ul });
        this.setData({
          loggedIn: true,
          displayLabel: name,
          roleLabel: String(p.role || 'viewer').toUpperCase(),
          userLevelLabel: ul,
          showAiPick: canViewFeature('ai_pick', ul),
          showDeepFinance: canViewFeature('deep_finance', ul),
          avatarUrl: (p.avatar_url || '').trim(),
        });
        try {
          const qb = await request({ url: '/api/user/quota' });
          const qd = qb && qb.ok === true ? qb.data : qb;
          const sq = (qd && qd.stock_qa) || {};
          const used = sq.used != null ? sq.used : 0;
          const limit = sq.limit != null ? sq.limit : '—';
          this.setData({
            quotaHint: `问答配额 ${used}/${limit} · 回测 ${(qd.backtest && qd.backtest.used) || 0}/${(qd.backtest && qd.backtest.limit) || '—'}`,
          });
        } catch {
          this.setData({ quotaHint: '' });
        }
        return;
      }
    } catch (e) {
      setToken('');
    }
    this.setData({
      loggedIn: false,
      displayLabel: '未登录用户',
      avatarUrl: '',
      quotaHint: '',
      showAiPick: false,
      showDeepFinance: false,
    });
  },

  onAgreeChange(e) {
    const vals = e.detail.value || [];
    this.setData({ agreed: vals.indexOf('1') >= 0 });
  },

  async onWxLogin() {
    if (!this.data.agreed) {
      wx.showToast({ title: '请先勾选协议', icon: 'none' });
      return;
    }
    wx.showLoading({ title: '登录中' });
    try {
      const d = await tryMiniprogramLogin();
      wx.hideLoading();
      wx.showToast({ title: '登录成功', icon: 'success' });
      await this.refreshProfile();
    } catch (e) {
      wx.hideLoading();
      const msg = e && e.message ? String(e.message) : '登录失败';
      wx.showToast({
        title: msg.length > 36 ? msg.slice(0, 33) + '…' : msg,
        icon: 'none',
        duration: 4000,
      });
    }
  },

  onResetApiBase() {
    resetApiBaseToDefault();
    wx.showToast({ title: '已恢复默认线路', icon: 'success' });
  },

  onLogout() {
    setToken('');
    try {
      wx.removeStorageSync('user_level');
    } catch {
      /* ignore */
    }
    try {
      const app = getApp();
      if (app && app.globalData) app.globalData.userLevel = 'trial';
    } catch {
      /* ignore */
    }
    this.setData({
      loggedIn: false,
      displayLabel: '未登录用户',
      avatarUrl: '',
      quotaHint: '',
      userLevelLabel: 'trial',
    });
    wx.reLaunch({ url: '/pages/login/login' });
  },

  goQuotes() {
    wx.navigateTo({ url: '/pages/quotes/quotes' });
  },

  goStockQA() {
    wx.navigateTo({ url: '/pages/stock-qa/stock-qa' });
  },

  goSignals() {
    wx.navigateTo({ url: '/pages/signals/signals' });
  },

  onUpgrade() {
    wx.showModal({
      title: '升级权益',
      content:
        'trial 用户可联系管理员开通 basic / pro。请通过 Web 端 https://htma.newhigh.com.cn 或企业渠道申请。',
      showCancel: false,
    });
  },

  onSettings() {
    wx.navigateTo({ url: '/pages/about/about' });
  },

  goStrategy() {
    wx.switchTab({ url: '/pages/strategy/strategy' });
  },

  goNews() {
    wx.switchTab({ url: '/pages/news/news' });
  },

  goAbout() {
    wx.navigateTo({ url: '/pages/about/about' });
  },

  onSoon() {
    wx.showToast({ title: '敬请期待', icon: 'none' });
  },

  goFeatureHub() {
    wx.navigateTo({ url: '/pages/feature-hub/feature-hub' });
  },

  /** 组合 → Web 版持仓/组合页 */
  openPortfolioWeb() {
    openWebPath('/portfolio');
  },

  /** 数据 / 账务类入口 */
  openDataWeb() {
    openWebPath('/data');
  },

  /** 系统监控 Web */
  openSystemMonitorWeb() {
    openWebPath('/system-monitor');
  },

  onBell() {
    wx.showToast({ title: '消息中心', icon: 'none' });
  },

  onContact() {
    wx.showModal({
      title: '联系客服',
      content: '请通过 Web 端 https://htma.newhigh.com.cn 或企业渠道联系。',
      showCancel: false,
    });
  },

  /** 与 Web 侧栏一致：Web 项优先小程序内 web-view 打开 */
  onDesktopMenu(e) {
    const idx = Number(e.currentTarget.dataset.index);
    const rows = this.data.desktopMenu;
    if (!rows || Number.isNaN(idx) || !rows[idx]) return;
    navigateMenuItem(rows[idx]);
  },
});
