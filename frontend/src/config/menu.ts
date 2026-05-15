/**
 * 红山量化平台 - 统一菜单配置
 * 供 Layout/Sidebar/MobileBottomNav/MobileDrawer 使用
 * 图标使用 Material Symbols Outlined（与现有项目一致）
 *
 * 数据源：`config/navigation_manifest.json`（与微信小程序 `config/menu.generated.js` 同源）
 */

import manifest from '../../../config/navigation_manifest.json';

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

type NavRow = (typeof manifest.items)[number];

function toMenuItem(row: NavRow): MenuItem {
  return {
    name: row.labelZh,
    key: row.labelKey,
    icon: row.icon,
    path: row.webPath,
  };
}

/** 桌面端侧边栏菜单 */
export const menuItems: MenuItem[] = manifest.items.map(toMenuItem);

/** 快捷导航路径（侧边栏顶部 4 个常用入口） */
export const quickNavPaths = manifest.quickNavPaths as string[];

/** 快捷导航菜单项 */
export const quickNavItems: MenuItem[] = menuItems.filter((m) =>
  quickNavPaths.includes(m.path)
);

/** 完整菜单（排除快捷导航，避免重复） */
export const fullMenuItems: MenuItem[] = menuItems.filter(
  (m) => !quickNavPaths.includes(m.path)
);

/** 移动端底部栏主要入口路径 */
const mobilePrimaryPaths = manifest.mobilePrimaryPaths as string[];

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
