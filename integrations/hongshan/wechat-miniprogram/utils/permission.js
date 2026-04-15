/**
 * 按 user_level 控制功能入口展示（与 Gateway 配额策略对齐：trial/basic/pro）。
 * @param {string} feature
 * @param {string} [level]
 */
function canViewFeature(feature, level) {
  const lv = String(level || 'trial').toLowerCase();
  switch (feature) {
    case 'signals':
    case 'news':
    case 'quotes':
      return true;
    case 'stock_qa':
      return true;
    case 'deep_finance':
      return lv === 'pro' || lv === 'enterprise' || lv === 'admin';
    case 'ai_pick':
      return lv === 'basic' || lv === 'pro' || lv === 'enterprise' || lv === 'admin';
    default:
      return true;
  }
}

module.exports = { canViewFeature };
