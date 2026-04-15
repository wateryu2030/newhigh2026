/**
 * 红山量化平台 - 统一菜单配置
 * 供 Layout/Sidebar/MobileBottomNav/MobileDrawer 使用
 * 图标使用 Material Symbols Outlined（与现有项目一致）
 *
 * 微信小程序侧栏顺序对齐：`integrations/hongshan/wechat-miniprogram/config/menu.js`（DESKTOP_SYNC）
 */

export interface MenuItem {
  /** 显示名称（中文） */
  name: string;
  /** i18n key，用于 LangContext */
  key: string;
  /** Material Symbols 图标名 */
  icon: string;
  /** 路由路径 */
  path: string;
  /** 是否仅在移动端底部栏显示（主要入口） */
  mobilePrimary?: boolean;
}

/** 桌面端侧边栏菜单 */
export const menuItems: MenuItem[] = [
  { name: '首页', key: 'nav.dashboard', icon: 'dashboard', path: '/' },
  { name: 'Alpha工坊', key: 'nav.alphaLab', icon: 'science', path: '/alpha-lab' },
  { name: '行情', key: 'nav.market', icon: 'query_stats', path: '/market' },
  { name: 'AI交易', key: 'nav.aiTrading', icon: 'memory', path: '/ai-trading' },
  { name: '策略', key: 'nav.strategies', icon: 'settings_input_component', path: '/strategies' },
  { name: '组合', key: 'nav.portfolio', icon: 'account_balance', path: '/portfolio' },
  { name: '大佬策略', key: 'nav.shareholderStrategy', icon: 'bar_chart', path: '/shareholder-strategy' },
  { name: '数据', key: 'nav.data', icon: 'storage', path: '/data' },
  { name: '系统监控', key: 'nav.systemMonitor', icon: 'monitor_heart', path: '/system-monitor' },
  { name: '新闻', key: 'nav.news', icon: 'newspaper', path: '/news' },
  { name: '股票问答', key: 'nav.stockQA', icon: 'chat_spark', path: '/stock-qa' },
  { name: '徘徊大宗', key: 'nav.blockTradeScreen', icon: 'swap_horiz', path: '/screen/block-trade' },
  { name: '账户', key: 'nav.profile', icon: 'person', path: '/profile' },
  { name: '设置', key: 'nav.settings', icon: 'settings', path: '/settings' },
];

/** 快捷导航路径（侧边栏顶部 4 个常用入口） */
export const quickNavPaths = ['/', '/alpha-lab', '/market', '/portfolio'];

/** 快捷导航菜单项 */
export const quickNavItems: MenuItem[] = menuItems.filter((m) =>
  quickNavPaths.includes(m.path)
);

/** 完整菜单（排除快捷导航，避免重复） */
export const fullMenuItems: MenuItem[] = menuItems.filter(
  (m) => !quickNavPaths.includes(m.path)
);

/** 移动端底部栏主要入口路径 */
const mobilePrimaryPaths = ['/', '/market', '/ai-trading', '/strategies', '/portfolio'];

/** 移动端底部栏显示的菜单项 */
export const mobilePrimaryItems: MenuItem[] = menuItems.filter((m) =>
  mobilePrimaryPaths.includes(m.path)
);

/** 未登录用户：侧栏底部「登录」入口 */
export const loginMenuItem: MenuItem = {
  name: '登录',
  key: 'auth.login',
  icon: 'login',
  path: '/login',
};

/** 快捷导航：未登录仅展示资讯 */
export function getQuickNavForUser(isAuthed: boolean): MenuItem[] {
  if (isAuthed) return quickNavItems;
  const news = menuItems.find((m) => m.path === '/news');
  return news ? [news] : [];
}

/** 全部菜单区：未登录仅展示「登录」 */
export function getFullMenuForUser(isAuthed: boolean): MenuItem[] {
  if (isAuthed) return fullMenuItems;
  return [loginMenuItem];
}

/** 移动端底栏：未登录为 资讯 + 登录 */
export function getMobilePrimaryForUser(isAuthed: boolean): MenuItem[] {
  if (isAuthed) return mobilePrimaryItems;
  const news = menuItems.find((m) => m.path === '/news');
  if (!news) return [loginMenuItem];
  return [news, loginMenuItem];
}

/** 侧滑抽屉：未登录仅资讯 + 登录 */
export function getDrawerMenuForUser(isAuthed: boolean): MenuItem[] {
  if (isAuthed) return menuItems;
  const news = menuItems.find((m) => m.path === '/news');
  return news ? [news, loginMenuItem] : [loginMenuItem];
}
