/**
 * 统一解析小程序请求的 HTTPS 根地址，避免本地/局域网残留配置导致真机 ERR_CONNECTION_REFUSED。
 */
const config = require('../config.js');

function defaultApiBase() {
  const b = (config && config.apiBase) || 'https://htma.newhigh.com.cn';
  return String(b).replace(/\/$/, '');
}

function hostFromHttpsUrl(url) {
  const m = String(url || '')
    .trim()
    .match(/^https:\/\/([^/:?#]+)/i);
  return m ? m[1].toLowerCase() : '';
}

function isPrivateOrLoopbackHost(host) {
  if (!host) return true;
  if (host === 'localhost' || host === '127.0.0.1' || host === '0.0.0.0' || host === '[::1]') {
    return true;
  }
  if (host.startsWith('192.168.') || host.startsWith('10.')) return true;
  if (host.startsWith('172.')) {
    const parts = host.split('.');
    if (parts.length >= 2) {
      const n = parseInt(parts[1], 10);
      if (!Number.isNaN(n) && n >= 16 && n <= 31) return true;
    }
  }
  return false;
}

/**
 * 仅允许 https + 非内网地址 +（与默认配置同主机或 newhigh.com.cn 系域名）。
 */
function isAllowedApiBase(url) {
  if (typeof url !== 'string' || !url.trim().startsWith('https://')) return false;
  const host = hostFromHttpsUrl(url);
  if (!host || isPrivateOrLoopbackHost(host)) return false;
  const defHost = hostFromHttpsUrl(defaultApiBase());
  if (host === defHost) return true;
  if (host === 'newhigh.com.cn' || host.endsWith('.newhigh.com.cn')) return true;
  return false;
}

function normalizeOverride(stored) {
  if (typeof stored !== 'string') return null;
  const t = stored.trim().replace(/\/$/, '');
  if (!t) return null;
  return isAllowedApiBase(t) ? t : null;
}

/**
 * 启动时：合法 override 写入 globalData；非法则清除存储并回落默认。
 */
function applyApiBaseFromStorage(app) {
  let raw = '';
  try {
    raw = wx.getStorageSync('api_base_override');
  } catch {
    raw = '';
  }
  const normalized = normalizeOverride(raw);
  if (typeof raw === 'string' && raw.trim() && !normalized) {
    try {
      wx.removeStorageSync('api_base_override');
    } catch {
      /* ignore */
    }
  }
  if (app && app.globalData) {
    app.globalData.apiBase = normalized || defaultApiBase();
  }
}

function resolveRequestBase() {
  let app = null;
  try {
    app = getApp();
  } catch {
    app = null;
  }
  const fromApp =
    app && app.globalData && typeof app.globalData.apiBase === 'string'
      ? app.globalData.apiBase.trim().replace(/\/$/, '')
      : '';
  if (fromApp && isAllowedApiBase(fromApp)) return fromApp;
  return defaultApiBase();
}

/** 清除本地错误的 API 根地址，供登录页 / 我的页共用 */
function resetApiBaseToDefault() {
  try {
    wx.removeStorageSync('api_base_override');
  } catch {
    /* ignore */
  }
  try {
    applyApiBaseFromStorage(getApp());
  } catch {
    /* ignore */
  }
}

module.exports = {
  defaultApiBase,
  isAllowedApiBase,
  normalizeOverride,
  applyApiBaseFromStorage,
  resolveRequestBase,
  resetApiBaseToDefault,
};
