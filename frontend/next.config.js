/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  /** `/api/*` 由 `src/app/api/[...path]/route.ts` 服务端转发，运行时可读 `API_PROXY_TARGET`，避免仅 rewrites 在构建期写死后生产 502 */
  async rewrites() {
    return [];
  },
  /**
   * 仅为 /_next/static 设长缓存。切勿对同一 URL 再叠加「全站 no-cache」，否则部分 CDN/浏览器会合并出
   * 冲突的 Cache-Control，表现为 CSS chunk 未命中或错配 → 页面只剩深色底、Tailwind 全部失效。
   * HTML 勿在 Cloudflare 上套「Cache Everything」长缓存；部署新版本后建议 Purge Cache。
   */
  async headers() {
    return [
      {
        source: '/_next/static/:path*',
        headers: [{ key: 'Cache-Control', value: 'public, max-age=31536000, immutable' }],
      },
    ];
  },
};

module.exports = nextConfig;
