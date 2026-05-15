'use client';

import Link from 'next/link';
import { useState } from 'react';
import { apiPostJson, AUTH_TOKEN_STORAGE_KEY } from '@/lib/auth-client';
import { notifyAuthChanged } from '@/context/AuthContext';
import { useLang } from '@/context/LangContext';

export default function RegisterPage() {
  const { t } = useLang();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setLoading(true);
    try {
      const r = await apiPostJson<{
        token: string;
        username: string;
        user_id: string;
      }>('/auth/register', {
        username: username.trim(),
        email: email.trim(),
        password,
        phone: phone.trim() || undefined,
      });
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

  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4">
      <div className="mx-auto w-full max-w-md space-y-6 rounded-xl border border-card-border bg-terminal-bg/80 p-8">
        <h1 className="text-xl font-semibold text-on-surface">{t('register.title')}</h1>
        <p className="text-sm text-text-secondary">{t('register.subtitle')}</p>
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm text-text-secondary">{t('profile.username')}</label>
            <input
              className="w-full rounded border border-card-border bg-surface-container-high px-3 py-2 text-on-surface"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              minLength={3}
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-text-secondary">{t('profile.email')}</label>
            <input
              type="email"
              className="w-full rounded border border-card-border bg-surface-container-high px-3 py-2 text-on-surface"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-text-secondary">{t('profile.phone')}</label>
            <input
              className="w-full rounded border border-card-border bg-surface-container-high px-3 py-2 text-on-surface"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              autoComplete="tel"
              placeholder={t('register.phoneOptional')}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-text-secondary">{t('login.password')}</label>
            <input
              type="password"
              className="w-full rounded border border-card-border bg-surface-container-high px-3 py-2 text-on-surface"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              minLength={6}
              required
            />
          </div>
          {err && <p className="text-sm text-[color:var(--color-chart-amber)]">{err}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded bg-primary-fixed py-2 text-on-warm-fill hover:opacity-90 disabled:opacity-50"
          >
            {loading ? t('register.submitting') : t('register.submit')}
          </button>
        </form>
        <p className="text-center text-sm text-text-secondary">
          {t('register.hasAccount')}{' '}
          <Link href="/login" className="text-primary-fixed underline">
            {t('register.goLogin')}
          </Link>
        </p>
      </div>
    </div>
  );
}
