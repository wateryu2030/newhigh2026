/**
 * Gateway 请求封装：自动 Bearer、401 清理并跳转登录、统一错误提示。
 * 合法域名须在微信公众平台配置为 HTTPS（不可用 localhost）。
 */
const AUTH_TOKEN_KEY = 'newhigh_jwt_token';
const { resolveRequestBase } = require('./api-base.js');

function getStoredToken() {
  try {
    return (
      wx.getStorageSync(AUTH_TOKEN_KEY) ||
      wx.getStorageSync('token') ||
      ''
    );
  } catch {
    return '';
  }
}

/**
 * @param {object} opts
 * @param {string} opts.url 相对路径或完整 URL
 * @param {string} [opts.method='GET']
 * @param {object} [opts.data]
 * @param {boolean} [opts.redirectOn401=true] 401 时 reLaunch 登录页
 * @param {number} [opts.timeout=30000]
 */
function request(opts) {
  const {
    url,
    method = 'GET',
    data = {},
    redirectOn401 = true,
    timeout = 30000,
  } = opts || {};
  const base = resolveRequestBase();
  const full = url.startsWith('http') ? url : `${base}${url}`;
  const token = getStoredToken();
  const header = {
    'content-type': 'application/json',
  };
  if (token) {
    header.Authorization = `Bearer ${token}`;
  }
  return new Promise((resolve, reject) => {
    wx.request({
      url: full,
      method,
      data,
      timeout,
      header,
      success(res) {
        const { statusCode, data: body } = res;
        if (statusCode === 401) {
          try {
            wx.removeStorageSync(AUTH_TOKEN_KEY);
            wx.removeStorageSync('token');
          } catch {
            /* ignore */
          }
          try {
            const g = getApp();
            if (g && g.globalData) g.globalData.userLevel = 'trial';
          } catch {
            /* ignore */
          }
          if (redirectOn401) {
            wx.reLaunch({ url: '/pages/login/login?reason=401' });
          }
          reject(new Error('登录已过期，请重新登录'));
          return;
        }
        if (statusCode >= 200 && statusCode < 300) {
          if (
            body &&
            typeof body === 'object' &&
            body.ok === false &&
            body.error
          ) {
            reject(new Error(String(body.error)));
            return;
          }
          resolve(body);
          return;
        }
        const msg =
          body && typeof body === 'object' && (body.detail || body.error)
            ? String(body.detail || body.error)
            : `HTTP ${statusCode}`;
        reject(new Error(msg));
      },
      fail(err) {
        const em = (err && err.errMsg) || '';
        if (/CONNECTION_REFUSED|connection refused|ERR_CONNECTION_REFUSED/i.test(em)) {
          reject(
            new Error(
              '无法连接服务器（连接被拒绝）。若曾在开发者工具写入 API 地址，请在登录页点「恢复默认线路」后重试。',
            ),
          );
          return;
        }
        reject(err instanceof Error ? err : new Error(em || '网络请求失败'));
      },
    });
  });
}

module.exports = { request, AUTH_TOKEN_KEY, getStoredToken };
