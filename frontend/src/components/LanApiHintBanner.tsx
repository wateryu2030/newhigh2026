'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { API_BASE_STORAGE_KEY } from '@/api/client';

/** HTTPS（如 Cloudflare）下若设置里仍填了 http/127.0.0.1，会导致 Failed to fetch / 混合内容 */
export function LanApiHintBanner() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    try {
      if (window.location.protocol !== 'https:') return;
      const v = localStorage.getItem(API_BASE_STORAGE_KEY)?.trim() || '';
      if (!v) return;
      if (v.includes('127.0.0.1') || v.includes('localhost') || v.startsWith('http://')) {
        setShow(true);
      }
    } catch {
      /* ignore */
    }
  }, []);

  if (!show) return null;

  return (
    <div className="border-b border-[color:var(--color-error-banner-border)] bg-[color:var(--color-error-banner-bg)] px-4 py-2 text-center text-sm text-on-surface">
      当前为 <strong>HTTPS</strong>，设置里的 API 地址使用了 <strong>http / 127.0.0.1</strong>，浏览器会拦截请求。请打开{' '}
      <Link href="/settings" className="underline font-medium text-on-surface">
        设置
      </Link>{' '}
      点击 <strong>清除</strong>，改用默认同源 <code className="bg-black/30 px-1">/api</code>。
    </div>
  );
}
