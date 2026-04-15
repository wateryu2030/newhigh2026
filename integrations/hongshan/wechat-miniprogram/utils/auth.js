/**
 * 与 Web 端共用 JWT 键名，便于同一 Gateway 鉴权。
 * 登录：wx.login → POST /api/auth/wechat/miniprogram
 */
const AUTH_TOKEN_KEY = 'newhigh_jwt_token';

const { request } = require('./request.js');

function getToken() {
  try {
    return wx.getStorageSync(AUTH_TOKEN_KEY) || '';
  } catch {
    return '';
  }
}

function setToken(token) {
  try {
    if (token) {
      wx.setStorageSync(AUTH_TOKEN_KEY, token);
      try {
        wx.setStorageSync('token', token);
      } catch {
        /* ignore */
      }
    } else {
      wx.removeStorageSync(AUTH_TOKEN_KEY);
      try {
        wx.removeStorageSync('token');
      } catch {
        /* ignore */
      }
    }
  } catch {
    /* ignore */
  }
}

function applyUserLevelFromPayload(d) {
  const lv = (d && d.user_level) || 'trial';
  try {
    const app = getApp();
    if (app && app.globalData) {
      app.globalData.userLevel = String(lv);
    }
    wx.setStorageSync('user_level', String(lv));
  } catch {
    /* ignore */
  }
}

/**
 * wx.login → POST /api/auth/wechat/miniprogram；成功 resolve 载荷，失败 reject(Error)。
 */
function tryMiniprogramLogin() {
  return new Promise((resolve, reject) => {
    wx.login({
      success: (loginRes) => {
        if (!loginRes.code) {
          reject(new Error('未获取到微信 code，请重试'));
          return;
        }
        request({
          url: '/api/auth/wechat/miniprogram',
          method: 'POST',
          data: { code: loginRes.code },
        })
          .then((body) => {
            if (!body || body.ok !== true) {
              const msg = (body && body.error) || '登录失败';
              reject(new Error(String(msg)));
              return;
            }
            const d = body.data || {};
            const token = d.token || d.access_token;
            if (token) setToken(token);
            applyUserLevelFromPayload(d);
            resolve(d);
          })
          .catch((e) => {
            reject(e instanceof Error ? e : new Error(String(e)));
          });
      },
      fail: (e) => {
        reject(new Error((e && e.errMsg) || 'wx.login 失败'));
      },
    });
  });
}

module.exports = {
  AUTH_TOKEN_KEY,
  getToken,
  setToken,
  tryMiniprogramLogin,
  applyUserLevelFromPayload,
};
