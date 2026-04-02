import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';

/**
 * 透传中间件：无额外逻辑。
 * Next 14 dev 在「空 .next」冷启动时依赖生成 `server/middleware-manifest.json`；
 * 无 middleware 源文件时，部分版本会出现 manifest 缺失 → 全站与 `/api/*` 代理 500。
 */
export function middleware(_request: NextRequest) {
  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
