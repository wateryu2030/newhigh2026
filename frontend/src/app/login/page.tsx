'use client';

import Link from 'next/link';
import { Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  apiPostJson,
  AUTH_TOKEN_STORAGE_KEY,
  getFeishuAuthUrl,
  getWechatAuthUrl,
} from '@/lib/auth-client';
import { useLang } from '@/context/LangContext';
import { notifyAuthChanged } from '@/context/AuthContext';

/**
 * 登录页 — 所有方式平行展示，用户自选一种
 *
 * 微信扫码、飞书登录、手机号验证码、用户名与密码 四张卡片并排，
 * 无先后推荐、无折叠隐藏、无强制顺序。
 */

type LoginCapabilities = {
  wechatLogin: boolean;
  feishuLogin: boolean;
  phoneOtpLogin: boolean;
  localPasswordLogin: boolean;
  localPasswordRegister: boolean;
};

const DEFAULT_CAPS: LoginCapabilities = {
  wechatLogin: true,
  feishuLogin: true,
  phoneOtpLogin: true,
  localPasswordLogin: true,
  localPasswordRegister: true,
};

async function fetchLoginCaps(): Promise<LoginCapabilities | null> {
  try {
    const res = await fetch('/api/auth/login-capabilities');
    if (!res.ok) return null;
    return (await res.json()) as LoginCapabilities;
  } catch {
    return null;
  }
}

function LoginCard({
  icon,
  label,
  description,
  enabled,
  enabledLabel,
  actions,
}: {
  icon: React.ReactNode;
  label: string;
  description: string;
  enabled: boolean;
  enabledLabel: string;
  actions: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-card-border/60 p-5 space-y-4">
      <div className="flex items-center gap-2 font-semibold text-sm text-on-surface">
        {icon}
        {label}
      </div>
      <p className="text-xs text-text-dim leading-relaxed">{description}</p>
      {enabled ? (
        actions
      ) : (
        <div className="w-full rounded-xl bg-surface-container-high py-2.5 text-sm text-text-dim text-center opacity-50">
          暂未开放
        </div>
      )}
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="rounded-2xl border border-card-border/40 bg-surface-container-high/10 p-5 animate-pulse space-y-3">
      <div className="h-4 w-20 bg-surface-mid rounded" />
      <div className="h-3 w-full bg-surface-mid rounded" />
      <div className="h-9 w-full bg-surface-mid rounded" />
    </div>
  );
}

function LoginForm() {
  const { t } = useLang();
  const sp = useSearchParams();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [oauthLoading, setOauthLoading] = useState<'wechat' | 'feishu' | null>(null);
  const [caps, setCaps] = useState<LoginCapabilities | null>(null);

  const nextPath = useMemo(() => {
    const n = sp?.get('next');
    return n && n.startsWith('/') ? n : '/';
  }, [sp]);

  useEffect(() => {
    let cancelled = false;
    fetchLoginCaps().then((data) => {
      if (!cancelled) setCaps(data ?? DEFAULT_CAPS);
    });
    return () => { cancelled = true; };
  }, []);

  // OAuth callback
  useEffect(() => {
    const oauthErr = sp?.get('oauth_error');
    const token = sp?.get('token');
    const oauth = sp?.get('oauth');
    if (oauthErr) {
      setErr('该登录方式暂不可用，请选择其他方式');
      const q = new URLSearchParams();
      if (nextPath !== '/') q.set('next', nextPath.slice(1));
      window.history.replaceState({}, '', q.toString() ? `/login?${q}` : '/login');
      return;
    }
    if (token && oauth && typeof window !== 'undefined') {
      try {
        localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
        notifyAuthChanged();
        window.location.replace(nextPath);
      } catch {
        setErr(t('login.saveTokenFailed'));
      }
    }
  }, [sp, t, nextPath]);

  const handlePasswordSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    setLoading(true);
    try {
      const r = await apiPostJson<{ token: string; user: string }>('/auth/login', { username, password });
      localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, r.token);
      notifyAuthChanged();
      window.location.href = nextPath;
    } catch (e) {
      setErr(e instanceof Error ? e.message : t('login.failed'));
    } finally {
      setLoading(false);
    }
  }, [username, password, nextPath, t]);

  const handlePhoneSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    setLoading(true);
    try {
      const r = await apiPostJson<{ token: string; user: string }>('/auth/login', { phone: phone.trim(), code: code.trim() });
      localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, r.token);
      notifyAuthChanged();
      window.location.href = nextPath;
    } catch (e) {
      setErr(e instanceof Error ? e.message : t('login.failed'));
    } finally {
      setLoading(false);
    }
  }, [phone, code, nextPath, t]);

  const startWechatOAuth = useCallback(async () => {
    setErr(null);
    setOauthLoading('wechat');
    try {
      const r = await getWechatAuthUrl();
      if (!r.configured || !r.authorize_url) {
        // 未配置真微信时走模拟扫码登录 → 选角页
        window.location.href = '/login/wechat-mock';
        return;
      }
      window.location.href = r.authorize_url;
    } catch {
      setErr(t('login.failed'));
    } finally {
      setOauthLoading(null);
    }
  }, [t]);

  const startFeishuOAuth = useCallback(async () => {
    setErr(null);
    setOauthLoading('feishu');
    try {
      const r = await getFeishuAuthUrl();
      if (!r.configured || !r.authorize_url) {
        // 未配置真飞书时走模拟扫码登录 → 选角页
        window.location.href = '/login/feishu-mock';
        return;
      }
      window.location.href = r.authorize_url;
    } catch {
      setErr(t('login.failed'));
    } finally {
      setOauthLoading(null);
    }
  }, [t]);

  const c = caps ?? DEFAULT_CAPS;
  const loadingCaps = caps === null;

  return (
    <div className="mx-auto w-full max-w-5xl">
      <div className="rounded-3xl border border-card-border/80 bg-card/95 p-6 shadow-xl ring-1 ring-white/60 backdrop-blur-sm md:p-8">
        <h2 className="font-sans text-xl font-bold tracking-tight text-on-surface">登录</h2>
        <p className="mt-1 mb-6 text-xs text-text-dim">选择一种方式登录，其余信息可在登录后补充</p>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {loadingCaps ? (
            [1,2,3,4].map(i => <SkeletonCard key={i} />)
          ) : (
            <>
              <LoginCard
                icon={<svg className="h-4 w-4 text-[#07C160] shrink-0" viewBox="0 0 24 24" fill="currentColor"><path d="M8.5 11a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zm7 0a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zM12 2C6.477 2 2 6.477 2 12c0 1.82.487 3.53 1.338 5.002L2 22l5.14-1.264A9.956 9.956 0 0 0 12 22c5.523 0 10-4.477 10-10S17.523 2 12 2z"/></svg>}
                label="微信登录"
                description="使用微信扫码快速登录"
                enabled={c.wechatLogin}
                enabledLabel="微信扫码登录"
                actions={
                  <button type="button" disabled={oauthLoading !== null} onClick={startWechatOAuth}
                    className="w-full rounded-xl bg-[#07C160] py-2.5 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-50">
                    {oauthLoading === 'wechat' ? '...' : '微信扫码登录'}
                  </button>
                }
              />
              <LoginCard
                icon={<svg className="h-4 w-4 text-blue-500 shrink-0" viewBox="0 0 24 24" fill="currentColor"><path d="M4.5 3A1.5 1.5 0 0 0 3 4.5v15A1.5 1.5 0 0 0 4.5 21h15a1.5 1.5 0 0 0 1.5-1.5v-15A1.5 1.5 0 0 0 19.5 3h-15z"/></svg>}
                label="飞书登录"
                description="使用飞书扫码登录"
                enabled={c.feishuLogin}
                enabledLabel="飞书登录"
                actions={
                  <button type="button" disabled={oauthLoading !== null} onClick={startFeishuOAuth}
                    className="w-full rounded-xl border border-card-border bg-surface-container-high py-2.5 text-sm font-medium text-on-surface transition hover:opacity-90 disabled:opacity-50">
                    {oauthLoading === 'feishu' ? '...' : '飞书登录'}
                  </button>
                }
              />
              <LoginCard
                icon={<svg className="h-4 w-4 text-primary-fixed shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="5" y="2" width="14" height="20" rx="2" ry="2"/><line x1="12" y1="18" x2="12.01" y2="18"/></svg>}
                label="手机号登录"
                description="短信验证码，1分钟内送达"
                enabled={c.phoneOtpLogin}
                enabledLabel="手机号登录"
                actions={
                  <form onSubmit={handlePhoneSubmit} className="space-y-2">
                    <input className="w-full rounded-lg border border-card-border bg-surface-container-high px-3 py-2 text-sm text-on-surface outline-none focus:border-primary-fixed transition"
                      value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="手机号" required />
                    <div className="flex gap-2">
                      <input className="flex-1 rounded-lg border border-card-border bg-surface-container-high px-3 py-2 text-sm text-on-surface outline-none focus:border-primary-fixed transition"
                        value={code} onChange={(e) => setCode(e.target.value)} placeholder="验证码" required />
                      <button type="button" className="shrink-0 rounded-lg bg-surface-container-high px-3 py-2 text-xs text-text-secondary border border-card-border hover:opacity-80">获取</button>
                    </div>
                    <button type="submit" disabled={loading} className="w-full rounded-xl bg-primary-fixed py-2 text-sm font-semibold text-on-warm-fill hover:opacity-90 disabled:opacity-50">
                      {loading ? '...' : '登录'}
                    </button>
                  </form>
                }
              />
              <LoginCard
                icon={<svg className="h-4 w-4 text-primary-fixed shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>}
                label="账号密码"
                description="已注册用户使用邮箱或用户名"
                enabled={c.localPasswordLogin}
                enabledLabel="密码登录"
                actions={
                  <form onSubmit={handlePasswordSubmit} className="space-y-2">
                    <input className="w-full rounded-lg border border-card-border bg-surface-container-high px-3 py-2 text-sm text-on-surface outline-none focus:border-primary-fixed transition"
                      value={username} onChange={(e) => setUsername(e.target.value)} placeholder="用户名 / 邮箱" required />
                    <input type="password" className="w-full rounded-lg border border-card-border bg-surface-container-high px-3 py-2 text-sm text-on-surface outline-none focus:border-primary-fixed transition"
                      value={password} onChange={(e) => setPassword(e.target.value)} placeholder="密码" required />
                    <button type="submit" disabled={loading} className="w-full rounded-xl bg-primary-fixed py-2 text-sm font-semibold text-on-warm-fill hover:opacity-90 disabled:opacity-50">
                      {loading ? '...' : '登录'}
                    </button>
                  </form>
                }
              />
            </>
          )}
        </div>

        {err && <p className="mt-4 text-sm text-[color:var(--color-chart-amber)] text-center">{err}</p>}

        <p className="mt-6 text-center text-sm text-text-secondary">
          还没有账号？{' '}
          <Link href="/register" className="font-medium text-primary-fixed underline-offset-2 hover:underline">
            立即注册
          </Link>
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  const { t } = useLang();
  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4 py-8">
      <Suspense fallback={<p className="text-text-secondary">{t('common.loading')}</p>}>
        <LoginForm />
      </Suspense>
    </div>
  );
}
