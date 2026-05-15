'use client';

import { useEffect } from 'react';

/** 生产环境注册 sw.js（同源缓存静态资源） */
export function ServiceWorkerRegister() {
  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (process.env.NODE_ENV !== 'production') return;
    if (!('serviceWorker' in navigator)) return;
    void navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(() => {
      /* 忽略注册失败（如非 HTTPS） */
    });
  }, []);
  return null;
}
