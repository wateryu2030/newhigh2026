import type { Metadata, Viewport } from 'next';
import { Inter, Manrope } from 'next/font/google';
import './globals.css';
import { Layout } from '@/components/Layout';
import { MainContent } from '@/components/MainContent';
import { ClientProviders } from '@/components/ClientProviders';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});
const manrope = Manrope({
  subsets: ['latin'],
  variable: '--font-manrope',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'AI 对冲基金 控制台',
  description: 'AI Fund Manager Cockpit / 数据直接展示，中英切换',
  icons: { icon: '/icon' },
  manifest: '/manifest.json',
  appleWebApp: { capable: true, title: 'AI Fund' },
  /** 与 manifest 一致；Chrome 建议使用 mobile-web-app-capable（apple-mobile-web-app-capable 已弃用提示） */
  other: { 'mobile-web-app-capable': 'yes' },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  themeColor: '#FF3B30',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh" className={`dark ${inter.variable} ${manrope.variable}`}>
      <body
        className={`min-h-screen ${inter.className}`}
        style={{ backgroundColor: '#0B0E14', color: '#ECEDF6' }}
      >
        <ClientProviders>
          <Layout>
          {/* Main Content - 新闻滚动已并入 TopBar，节约垂直空间 */}
          <MainContent>
            {children}
          </MainContent>
          </Layout>
        </ClientProviders>
      </body>
    </html>
  );
}
