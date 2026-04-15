/**
 * 与仓库规则一致：公网 Web 基准域名（飞书/通知可点击链接）。
 */
const BASE = 'https://htma.newhigh.com.cn';

function fullUrl(path) {
  const p = String(path || '').trim();
  if (!p) return BASE;
  if (p.startsWith('http://') || p.startsWith('https://')) return p;
  return BASE + (p.startsWith('/') ? p : `/${p}`);
}

function copyWebPath(path) {
  const url = fullUrl(path);
  wx.setClipboardData({
    data: url,
    success() {
      wx.showModal({
        title: '已复制链接',
        content: '请在系统浏览器中打开（与桌面端同一页面）。',
        showCancel: false,
      });
    },
    fail() {
      wx.showToast({ title: '复制失败', icon: 'none' });
    },
  });
}

module.exports = { BASE, fullUrl, copyWebPath };
