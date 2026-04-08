'use client';

import { Suspense, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { apiPostJson, AUTH_TOKEN_STORAGE_KEY } from '@/api/client';

function LoginForm() {
  const sp = useSearchParams();
  const [username, setUsername] = useState('demo');
  const [password, setPassword] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setLoading(true);
    try {
      const r = await apiPostJson<{ token: string; user: string }>('/auth/login', {
        username,
        password,
      });
      if (typeof window !== 'undefined') {
        localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, r.token);
      }
      const next = sp?.get('next') || '/';
      const target = next.startsWith('/') ? next : '/';
      window.location.href = target;
    } catch (e) {
      setErr(e instanceof Error ? e.message : '登录失败');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-md space-y-6 rounded-xl border border-card-border bg-terminal-bg/80 p-8">
      <h1 className="text-xl font-semibold text-on-surface">登录</h1>
      <p className="text-sm text-text-secondary">生产环境启用 JWT 后需先登录再访问 API。</p>
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="mb-1 block text-sm text-text-secondary">用户名</label>
          <input
            className="w-full rounded border border-card-border bg-surface-container-high px-3 py-2 text-on-surface"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm text-text-secondary">密码（可占位）</label>
          <input
            type="password"
            className="w-full rounded border border-card-border bg-surface-container-high px-3 py-2 text-on-surface"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </div>
        {err && <p className="text-sm text-[color:var(--color-chart-amber)]">{err}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded bg-primary-fixed py-2 text-on-warm-fill hover:opacity-90 disabled:opacity-50"
        >
          {loading ? '登录中…' : '登录'}
        </button>
      </form>
    </div>
  );
}

export default function LoginPage() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4">
      <Suspense fallback={<p className="text-text-secondary">加载中…</p>}>
        <LoginForm />
      </Suspense>
    </div>
  );
}
