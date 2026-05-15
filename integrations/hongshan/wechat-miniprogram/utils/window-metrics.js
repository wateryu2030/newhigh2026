/**
 * 窗口相关指标：优先 wx.getWindowInfo，避免 wx.getSystemInfoSync 弃用告警。
 * 极低基础库无 getWindowInfo 时回退 sync。
 */
function getWindowMetrics() {
  if (typeof wx.getWindowInfo === 'function') {
    try {
      return wx.getWindowInfo();
    } catch {
      /* fallthrough */
    }
  }
  try {
    return wx.getSystemInfoSync();
  } catch {
    return { statusBarHeight: 20, pixelRatio: 1 };
  }
}

function getPixelRatio() {
  const m = getWindowMetrics();
  const pr = m && m.pixelRatio;
  return pr != null && pr > 0 ? pr : 1;
}

module.exports = { getWindowMetrics, getPixelRatio };
