'use client';

import { useEffect } from 'react';

const SESSION_KEY = 'newhigh_chunk_reload_once';

/**
 * 部署后若 CDN/浏览器仍缓存旧 HTML，会引用已不存在的 _next/static 下 JS/CSS，触发 ChunkLoadError 或样式丢失。
 * 自动刷新一次以拉取最新 HTML（session 内仅一次，防止网络异常时死循环）。
 */
export function ChunkLoadRecovery() {
  useEffect(() => {
    const shouldReload = (msg: string) =>
      /loading chunk [\d]+ failed/i.test(msg) ||
      /chunk load error/i.test(msg) ||
      /failed to fetch dynamically imported module/i.test(msg);

    const tryReload = () => {
      try {
        if (typeof sessionStorage !== 'undefined' && sessionStorage.getItem(SESSION_KEY)) return;
        sessionStorage.setItem(SESSION_KEY, '1');
      } catch {
        return;
      }
      window.location.reload();
    };

    const onError = (e: ErrorEvent) => {
      const raw = e.target;
      if (raw instanceof HTMLLinkElement) {
        const href = String(raw.href || '');
        if (href.includes('/_next/static/')) tryReload();
        return;
      }
      if (raw instanceof HTMLScriptElement) {
        const src = String(raw.src || '');
        if (src.includes('/_next/static/')) tryReload();
        return;
      }
      const msg = [e.message, (e as ErrorEvent & { filename?: string }).filename]
        .filter(Boolean)
        .join(' ');
      if (shouldReload(msg) || msg.includes('_next/static/chunks')) tryReload();
    };

    const onRejection = (e: PromiseRejectionEvent) => {
      const r = e.reason;
      const msg = r?.message || String(r || '');
      if (shouldReload(msg)) {
        e.preventDefault();
        tryReload();
      }
    };

    window.addEventListener('error', onError, true);
    window.addEventListener('unhandledrejection', onRejection);
    return () => {
      window.removeEventListener('error', onError, true);
      window.removeEventListener('unhandledrejection', onRejection);
    };
  }, []);

  return null;
}
