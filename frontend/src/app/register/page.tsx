'use client';

import Link from 'next/link';
import { useState } from 'react';
import { apiPostJson, AUTH_TOKEN_STORAGE_KEY, getFeishuAuthUrl, getWechatAuthUrl } from '@/lib/auth-client';
import { notifyAuthChanged } from '@/context/AuthContext';
import { useLang } from '@/context/LangContext';

export default function RegisterPage() {
  const { t } = useLang();
  const [mode, setMode] = useState<'account' | 'phone'>('account');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [oauthLoading, setOauthLoading] = useState<'wechat' | 'feishu' | null>(null);
  const [oauthHint, setOauthHint] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setLoading(true);
    try {
      const body: Record<string, string | undefined> = mode === 'account'
        ? {
            username: username.trim(),
            email: email.trim(),
            password,
            phone: phone.trim() || undefined,
          }
        : {
            phone: phone.trim(),
            code: code.trim(),
            password,
          };
      const r = await apiPostJson<{
        token: string;
        username: string;
        user_id: string;
      }>('/auth/register', body);
      if (typeof window !== 'undefined' && r.token) {
        localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, r.token);
        notifyAuthChanged();
      }
      window.location.href = '/';
    } catch (e) {
      setErr(e instanceof Error ? e.message : t('register.failed'));
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
      setErr(e instanceof Error ? e.message : t('register.failed'));
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
      setErr(e instanceof Error ? e.message : t('register.failed'));
    } finally {
      setOauthLoading(null);
    }
  }

  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4">
      <div className="mx-auto w-full max-w-md space-y-6">
        <div className="rounded-xl border border-card-border bg-terminal-bg/80 p-8">
          <h1 className="text-xl font-semibold text-on-surface text-center">{t('register.title')}</h1>
          <p className="mt-2 text-center text-xs text-text-dim">{t('login.scopeHint')}</p>

          {/* OAuth 注册方式 */}
          <div className="mt-6 space-y-3">
            <button
              type="button"
              disabled={oauthLoading !== null}
              onClick={() => void startWechatOAuth()}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#07C160] py-3.5 text-base font-semibold text-white shadow-lg transition hover:opacity-95 disabled:opacity-50"
            >
              {oauthLoading === 'wechat' ? t('common.loading') : '微信注册'}
            </button>
            <button
              type="button"
              disabled={oauthLoading !== null}
              onClick={() => void startFeishuOAuth()}
              className="flex w-full items-center justify-center rounded-xl border border-card-border bg-surface-container-high py-3 text-sm font-medium text-on-surface transition hover:opacity-90 disabled:opacity-50"
            >
              {oauthLoading === 'feishu' ? t('common.loading') : '飞书注册'}
            </button>
          </div>
          {oauthHint && <p className="mt-3 text-sm text-text-secondary text-center">{oauthHint}</p>}
          {err && <p className="mt-3 text-sm text-[color:var(--color-chart-amber)]">{err}</p>}

          {/* 分隔线 */}
          <div className="my-8 flex items-center gap-3">
            <div className="h-px flex-1 bg-card-border" />
            <span className="text-xs text-text-dim">或使用账号/手机注册</span>
            <div className="h-px flex-1 bg-card-border" />
          </div>

          {/* 切换标签 */}
          <div className="mb-6 flex rounded-lg border border-card-border bg-surface-container-high p-1">
            <button
              type="button"
              onClick={() => setMode('account')}
              className={`flex-1 rounded-md py-2 text-sm font-medium transition ${
                mode === 'account' ? 'bg-primary-fixed text-on-warm-fill' : 'text-text-secondary hover:text-on-surface'
              }`}
            >
              账号注册
            </button>
            <button
              type="button"
              onClick={() => setMode('phone')}
              className={`flex-1 rounded-md py-2 text-sm font-medium transition ${
                mode === 'phone' ? 'bg-primary-fixed text-on-warm-fill' : 'text-text-secondary hover:text-on-surface'
              }`}
            >
              手机注册
            </button>
          </div>

          {/* 表单 */}
          <form onSubmit={onSubmit} className="space-y-4">
            {mode === 'account' ? (
              <>
                <div>
                  <label className="mb-1 block text-sm text-text-secondary">{t('profile.username')}</label>
                  <input
                    className="w-full rounded border border-card-border bg-surface-container-high px-3 py-2 text-on-surface outline-none focus:border-primary-fixed transition"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    autoComplete="username"
                    minLength={3}
                    required
                    placeholder="用户名"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm text-text-secondary">{t('profile.email')}</label>
                  <input
                    type="email"
                    className="w-full rounded border border-card-border bg-surface-container-high px-3 py-2 text-on-surface outline-none focus:border-primary-fixed transition"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="email"
                    required
                    placeholder="邮箱"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm text-text-secondary">{t('profile.phone')}</label>
                  <input
                    className="w-full rounded border border-card-border bg-surface-container-high px-3 py-2 text-on-surface outline-none focus:border-primary-fixed transition"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    autoComplete="tel"
                    placeholder="手机号（选填）"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm text-text-secondary">{t('login.password')}</label>
                  <input
                    type="password"
                    className="w-full rounded border border-card-border bg-surface-container-high px-3 py-2 text-on-surface outline-none focus:border-primary-fixed transition"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="new-password"
                    minLength={6}
                    required
                    placeholder="密码（至少 6 位）"
                  />
                </div>
              </>
            ) : (
              <>
                <div>
                  <label className="mb-1 block text-sm text-text-secondary">手机号</label>
                  <input
                    className="w-full rounded border border-card-border bg-surface-container-high px-3 py-2 text-on-surface outline-none focus:border-primary-fixed transition"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    autoComplete="tel"
                    required
                    placeholder="11 位手机号"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm text-text-secondary">验证码</label>
                  <div className="flex gap-2">
                    <input
                      className="flex-1 rounded border border-card-border bg-surface-container-high px-3 py-2 text-on-surface outline-none focus:border-primary-fixed transition"
                      value={code}
                      onChange={(e) => setCode(e.target.value)}
                      autoComplete="one-time-code"
                      required
                      placeholder="6 位验证码"
                    />
                    <button
                      type="button"
                      className="shrink-0 rounded bg-surface-container-high px-4 py-2 text-sm text-on-surface border border-card-border hover:opacity-80 transition"
                    >
                      获取验证码
                    </button>
                  </div>
                </div>
                <div>
                  <label className="mb-1 block text-sm text-text-secondary">{t('login.password')}</label>
                  <input
                    type="password"
                    className="w-full rounded border border-card-border bg-surface-container-high px-3 py-2 text-on-surface outline-none focus:border-primary-fixed transition"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="new-password"
                    minLength={6}
                    required
                    placeholder="设置密码（至少 6 位）"
                  />
                </div>
              </>
            )}
            {err && !oauthHint && <p className="text-sm text-[color:var(--color-chart-amber)]">{err}</p>}
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-primary-fixed py-2.5 text-on-warm-fill hover:opacity-90 disabled:opacity-50"
            >
              {loading ? t('register.submitting') : '注册并登录'}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-text-secondary">
            {t('register.hasAccount')}{' '}
            <Link href="/login" className="text-primary-fixed underline hover:opacity-80">
              去登录
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
