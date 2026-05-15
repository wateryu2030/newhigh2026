'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { isAuthPublicPath } from '@/config/authPaths';
import { useLang } from '@/context/LangContext';
import { LoadingSpinner } from '@/components/LoadingSpinner';

/**
 * 未登录访问受保护路由时拦截，仅允许资讯 / 登录 / 注册等公开页直通。
 */
export function AuthGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() ?? '';
  const { ready, isAuthenticated } = useAuth();
  const { t } = useLang();

  if (isAuthPublicPath(pathname)) {
    return <>{children}</>;
  }

  if (!ready) {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center gap-3 text-text-secondary">
        <LoadingSpinner />
        <span className="text-sm">{t('common.loading')}</span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <GuestUnlockPrompt />;
  }

  return <>{children}</>;
}

function GuestUnlockPrompt() {
  const pathname = usePathname() ?? '/';
  const { t } = useLang();
  const next = encodeURIComponent(pathname);
  return (
    <div className="mx-auto flex max-w-lg flex-col gap-6 rounded-2xl border border-card-border bg-card-bg/90 px-6 py-10 text-center shadow-lg">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-fixed/15 text-2xl text-primary-fixed">
        <span className="material-symbols-outlined text-4xl">lock_open</span>
      </div>
      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t('auth.guestTitle')}</h1>
        <p className="mt-3 text-sm leading-relaxed text-text-secondary">{t('auth.guestBody')}</p>
      </div>
      <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
        <Link
          href={`/login?next=${next}`}
          className="inline-flex min-h-touch items-center justify-center rounded-xl bg-primary-fixed px-6 py-3 text-sm font-semibold text-on-warm-fill transition hover:opacity-90"
        >
          {t('auth.loginWechatOrAccount')}
        </Link>
        <Link
          href="/news"
          className="inline-flex min-h-touch items-center justify-center rounded-xl border border-card-border px-6 py-3 text-sm font-medium text-text-secondary transition hover:bg-surface-container-high"
        >
          {t('auth.browseNewsOnly')}
        </Link>
      </div>
      <p className="text-xs text-text-dim">{t('auth.guestHint')}</p>
    </div>
  );
}
