/**
 * 前端路由：未登录可访问的路径（与 Gateway 新闻白名单、业务「登录后可见」策略对齐）。
 */
export function isAuthPublicPath(pathname: string): boolean {
  const p = pathname || '';
  if (p === '/login' || p.startsWith('/login/') || p === '/register') return true;
  if (p === '/news' || p.startsWith('/news/')) return true;
  return false;
}

/** 侧栏/底栏：未登录仍展示的菜单（资讯 + 登录入口） */
export function isMenuVisibleForGuest(path: string): boolean {
  return path === '/news' || path === '/login';
}
