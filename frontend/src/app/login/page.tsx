'use client';

import Link from 'next/link';
import { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  apiPostJson,
  AUTH_TOKEN_STORAGE_KEY,
  getFeishuAuthUrl,
  getWechatAuthUrl,
} from '@/lib/auth-client';
import { useLang } from '@/context/LangContext';
import { notifyAuthChanged } from '@/context/AuthContext';

function LoginForm() {
  const { t } = useLang();
  const sp = useSearchParams();
  const [username, setUsername] = useState('demo');
  const [password, setPassword] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [oauthHint, setOauthHint] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [oauthLoading, setOauthLoading] = useState<'wechat' | 'feishu' | null>(null);

  useEffect(() => {
    const oauthErr = sp?.get('oauth_error');
    const token = sp?.get('token');
    const oauth = sp?.get('oauth');
    const nextOnly = sp?.get('next');
    if (oauthErr) {
      setErr(decodeURIComponent(oauthErr));
      const q = new URLSearchParams();
      if (nextOnly) q.set('next', nextOnly);
      const qs = q.toString();
      window.history.replaceState({}, '', qs ? `/login?${qs}` : '/login');
      return;
    }
    if (token && oauth && typeof window !== 'undefined') {
      try {
        localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
        notifyAuthChanged();
        const next = nextOnly || '/';
        const target = next.startsWith('/') ? next : '/';
        window.location.replace(target);
      } catch {
        setErr(t('login.saveTokenFailed'));
      }
    }
  }, [sp, t]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setOauthHint(null);
    setLoading(true);
    try {
      const r = await apiPostJson<{ token: string; user: string }>('/auth/login', {
        username,
        password,
      });
      if (typeof window !== 'undefined') {
        localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, r.token);
        notifyAuthChanged();
      }
      const next = sp?.get('next') || '/';
      const target = next.startsWith('/') ? next : '/';
      window.location.href = target;
    } catch (e) {
      setErr(e instanceof Error ? e.message : t('login.failed'));
    } finally {
      setLoading(false);
    }
  }

  async function startWechatOAuth() {
    setErr(null);
    setOauthHint(null);
    setOauthLoading('wechat');
    try {
      const r = await getWechatAuthUrl();
      if (!r.configured || !r.authorize_url) {
        setOauthHint(r.hint || t('login.wechatNotConfigured'));
        return;
      }
      window.location.href = r.authorize_url;
    } catch (e) {
      setErr(e instanceof Error ? e.message : t('login.failed'));
    } finally {
      setOauthLoading(null);
    }
  }

  async function startFeishuOAuth() {
    setErr(null);
    setOauthHint(null);
    setOauthLoading('feishu');
    try {
      const r = await getFeishuAuthUrl();
      if (!r.configured || !r.authorize_url) {
        setOauthHint(r.hint || t('login.feishuNotConfigured'));
        return;
      }
      window.location.href = r.authorize_url;
    } catch (e) {
      setErr(e instanceof Error ? e.message : t('login.failed'));
    } finally {
      setOauthLoading(null);
    }
  }

  return (
    <div className="mx-auto max-w-md space-y-6">
      <div className="rounded-xl border border-card-border bg-terminal-bg/80 p-8">
        <h1 className="text-xl font-semibold text-on-surface">{t('login.title')}</h1>
        <p className="mt-1 text-xs text-text-dim">{t('login.scopeHint')}</p>
        <p className="mt-3 text-sm text-text-secondary">{t('login.wechatLead')}</p>

        <div className="mt-6 space-y-3">
          <button
            type="button"
            disabled={oauthLoading !== null}
            onClick={() => void startWechatOAuth()}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#07C160] py-3.5 text-base font-semibold text-white shadow-lg transition hover:opacity-95 disabled:opacity-50"
          >
            {oauthLoading === 'wechat' ? t('common.loading') : t('login.wechat')}
          </button>
          <button
            type="button"
            disabled={oauthLoading !== null}
            onClick={() => void startFeishuOAuth()}
            className="flex w-full items-center justify-center rounded-xl border border-card-border bg-surface-container-high py-3 text-sm font-medium text-on-surface transition hover:opacity-90 disabled:opacity-50"
          >
            {oauthLoading === 'feishu' ? t('common.loading') : t('login.feishu')}
          </button>
        </div>
        {oauthHint && <p className="mt-3 text-sm text-text-secondary">{oauthHint}</p>}
        {err && <p className="mt-3 text-sm text-[color:var(--color-chart-amber)]">{err}</p>}

        <div className="my-8 flex items-center gap-3">
          <div className="h-px flex-1 bg-card-border" />
          <span className="text-xs text-text-dim">{t('login.oauthDivider')}</span>
          <div className="h-px flex-1 bg-card-border" />
        </div>

        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm text-text-secondary">{t('profile.username')}</label>
            <input
              className="w-full rounded border border-card-border bg-surface-container-high px-3 py-2 text-on-surface"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-text-secondary">{t('login.password')}</label>
            <input
              type="password"
              className="w-full rounded border border-card-border bg-surface-container-high px-3 py-2 text-on-surface"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-primary-fixed py-2.5 text-on-warm-fill hover:opacity-90 disabled:opacity-50"
          >
            {loading ? t('login.submitting') : t('login.submit')}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-text-secondary">
          {t('login.noAccount')}{' '}
          <Link href="/register" className="text-primary-fixed underline">
            {t('login.goRegister')}
          </Link>
        </p>
      </div>
      <p className="text-center text-xs text-text-dim">{t('login.subtitle')}</p>
    </div>
  );
}

export default function LoginPage() {
  const { t } = useLang();
  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4">
      <Suspense fallback={<p className="text-text-secondary">{t('common.loading')}</p>}>
        <LoginForm />
      </Suspense>
    </div>
  );
}
