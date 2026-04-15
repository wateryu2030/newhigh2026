/**
 * 与 Web 端 `frontend/src/config/menu.ts` 中 `menuItems` 顺序一致，
 * 供「我的」页全量入口与路由分发（native | 复制 Web 链接）。
 */
module.exports.DESKTOP_SYNC = [
  { label: '首页', t: 'native', p: 'index' },
  { label: 'Alpha工坊', t: 'web', p: '/alpha-lab' },
  { label: '行情', t: 'native', p: 'quotes' },
  { label: 'AI交易', t: 'web', p: '/ai-trading' },
  { label: '策略', t: 'native', p: 'strategy' },
  { label: '组合', t: 'web', p: '/portfolio' },
  { label: '大佬策略', t: 'web', p: '/shareholder-strategy' },
  { label: '数据', t: 'web', p: '/data' },
  { label: '系统监控', t: 'web', p: '/system-monitor' },
  { label: '新闻', t: 'native', p: 'news' },
  { label: '股票问答', t: 'native', p: 'stock-qa' },
  { label: '徘徊大宗', t: 'native', p: 'block-trade' },
  { label: '账户', t: 'web', p: '/profile' },
  { label: '设置', t: 'web', p: '/settings' },
];
