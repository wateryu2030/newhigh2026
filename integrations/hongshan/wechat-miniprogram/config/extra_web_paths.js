/**
 * 侧栏主菜单之外的「桌面 Web 能力」入口（仅小程序「全部功能」页追加展示）。
 * 形状与 menu.generated.js 中 web 项一致：{ label, t: 'web', p: '/path' }
 * 与 frontend 侧栏未收录的常用页对齐时可在此增补。
 */
module.exports.EXTRA_WEB_PARITY = [
  { label: '投研', t: 'web', p: '/research' },
  { label: '研报', t: 'web', p: '/reports' },
  { label: '交易', t: 'web', p: '/trade' },
  { label: '风控', t: 'web', p: '/risk' },
  { label: '进化', t: 'web', p: '/evolution' },
  { label: '股票池', t: 'web', p: '/stocks' },
  { label: 'A股演示', t: 'web', p: '/ashare-demo' },
];
