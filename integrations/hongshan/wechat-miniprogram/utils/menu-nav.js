/**
 * 与 `config/menu.js` 中 DESKTOP_SYNC 项配合：原生跳转或打开 Web 内嵌页。
 */
const { copyWebPath } = require('./htma.js');

function openWebPath(path) {
  const raw = String(path || '/').trim();
  const query = raw.startsWith('http')
    ? encodeURIComponent(raw)
    : encodeURIComponent(raw.startsWith('/') ? raw : `/${raw}`);
  wx.navigateTo({
    url: `/pages/web-page/web-page?path=${query}`,
    fail() {
      copyWebPath(raw.startsWith('http') ? raw : raw.startsWith('/') ? raw : `/${raw}`);
    },
  });
}

function navigateMenuItem(m) {
  if (!m) return;
  if (m.t === 'web') {
    openWebPath(m.p);
    return;
  }
  switch (m.p) {
    case 'index':
      wx.switchTab({ url: '/pages/index/index' });
      break;
    case 'strategy':
      wx.switchTab({ url: '/pages/strategy/strategy' });
      break;
    case 'news':
      wx.switchTab({ url: '/pages/news/news' });
      break;
    case 'quotes':
      wx.navigateTo({ url: '/pages/quotes/quotes' });
      break;
    case 'stock-qa':
      wx.navigateTo({ url: '/pages/stock-qa/stock-qa' });
      break;
    case 'block-trade':
      wx.navigateTo({ url: '/pages/block-trade/block-trade' });
      break;
    default:
      break;
  }
}

module.exports = { openWebPath, navigateMenuItem };
