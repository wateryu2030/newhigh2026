/** @type {import('next').NextConfig} */
const apiTarget = process.env.NEXT_PUBLIC_API_TARGET || 'http://127.0.0.1:8000';
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  async rewrites() {
    return [
      { source: '/api/:path*', destination: `${apiTarget}/api/:path*` },
    ];
  },
};

module.exports = nextConfig;
