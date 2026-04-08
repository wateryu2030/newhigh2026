/** @type {import('next').NextConfig} */
const gatewayOrigin = (
  process.env.API_PROXY_TARGET ||
  process.env.NEXT_PUBLIC_API_TARGET ||
  'http://127.0.0.1:8000'
).replace(/\/$/, '');

const isProd = process.env.NODE_ENV === 'production';

const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  /** 开发环境关闭持久化缓存，减轻 vendor-chunks / flight 错配导致的页面 Internal Server Error */
  webpack: (config, { dev }) => {
    if (dev) config.cache = false;
    return config;
  },
  /**
   * `/api/*` 由 Next 内置反代到 Gateway（同 dev/start 进程可读到的环境变量）。
   * 不再使用 `app/api/[...path]/route.ts`：webpack dev 对 catch-all Route Handler 易产生
   * Cannot find module './NNN.js' chunk 错配。
   *
   * 生产/隧道：请在 `next build` 与 `next start`（或 standalone）前导出与线上一致的
   * `API_PROXY_TARGET`，否则需重新 build。
   */
  async rewrites() {
    const base = gatewayOrigin;
    return [
      { source: '/api', destination: `${base}/api` },
      { source: '/api/', destination: `${base}/api/` },
      { source: '/api/:path*', destination: `${base}/api/:path*` },
    ];
  },
  /**
   * 仅为 /_next/static 设长缓存。切勿对同一 URL 再叠加「全站 no-cache」，否则部分 CDN/浏览器会合并出
   * 冲突的 Cache-Control，表现为 CSS chunk 未命中或错配 → 页面只剩深色底、Tailwind 全部失效。
   * HTML 勿在 Cloudflare 上套「Cache Everything」长缓存；部署新版本后建议 Purge Cache。
   */
  async headers() {
    // 切勿在 next dev 下对 /_next/static 设 immutable：HMR 会换 chunk 名，浏览器若长缓存旧 URL → 404 → RSC 报错
    if (!isProd) return [];
    return [
      {
        source: '/_next/static/:path*',
        headers: [{ key: 'Cache-Control', value: 'public, max-age=31536000, immutable' }],
      },
    ];
  },
};

module.exports = nextConfig;
