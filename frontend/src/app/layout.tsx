import type { Metadata, Viewport } from 'next';
import './globals.css';
import { Nav } from '@/components/Nav';
import { ClientProviders } from '@/components/ClientProviders';
import { HotTickerBanner } from '@/components/HotTickerBanner';

export const metadata: Metadata = {
  title: 'AI 对冲基金 控制台',
  description: 'AI Fund Manager Cockpit / 数据直接展示，中英切换',
  icons: { icon: '/icon' },
  manifest: '/manifest.json',
  appleWebApp: { capable: true, title: 'AI Fund' },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  themeColor: '#0F172A',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh" className="dark">
      <body className="min-h-screen">
        <ClientProviders>
          <HotTickerBanner />
          <Nav />
          <main className="mx-auto min-h-screen max-w-7xl px-4 pb-20 pt-4 sm:px-6 sm:pb-6 sm:pt-6 lg:px-8 md:pb-6">
            {children}
          </main>
        </ClientProviders>
      </body>
    </html>
  );
}
