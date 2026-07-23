'use client';

import Link from 'next/link';
import { Suspense, useCallback, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { AUTH_TOKEN_STORAGE_KEY } from '@/api/client';
import { notifyAuthChanged } from '@/context/AuthContext';

const ROLES = [
  { key: 'viewer', label: '用户', desc: '普通用户，查看行情与数据' },
  { key: 'operator', label: '运营', desc: '运营人员，管理系统内容' },
  { key: 'admin', label: '管理员', desc: '管理员，拥有全部权限' },
];

function FeishuMockPick() {
  const sp = useSearchParams();
  const [selected, setSelected] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  const ticket = sp?.get('t') || 'direct';

  const handleConfirm = useCallback(async () => {
    if (!selected) return;
    setErr(null);
    setLoading(true);
    try {
      const res = await fetch('/auth/feishu/mock-complete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticket, role: selected }),
      });
      const data = await res.json();
      if (!data.ok || !data.data?.token) {
        setErr(data.message || data.error || '登录失败');
        return;
      }
      localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, data.data.token);
      notifyAuthChanged();
      setDone(true);
      setTimeout(() => { window.location.href = '/'; }, 800);
    } catch (e) {
      setErr(e instanceof Error ? e.message : '登录失败');
    } finally {
      setLoading(false);
    }
  }, [selected, ticket]);

  if (done) {
    return (
      <div className="text-center py-20">
        <div className="text-4xl text-primary-fixed mb-4">✓</div>
        <h2 className="text-lg font-semibold text-on-surface">登录成功</h2>
        <p className="text-sm text-text-dim mt-2">正在跳转...</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-md">
      <div className="rounded-3xl border border-card-border/80 bg-card/95 p-6 shadow-xl md:p-8">
        <h2 className="font-sans text-xl font-bold tracking-tight text-on-surface">飞书扫码登录</h2>
        <p className="mt-1 mb-6 text-xs text-text-dim">模拟模式 — 选择身份后直接登录</p>

        <p className="text-sm text-text-secondary mb-4">请选择登录身份</p>

        <div className="space-y-3">
          {ROLES.map(({ key, label, desc }) => (
            <button
              key={key}
              type="button"
              onClick={() => setSelected(key)}
              className={`w-full text-left rounded-2xl border p-4 transition ${
                selected === key
                  ? 'border-primary-fixed bg-primary-fixed/10 ring-1 ring-primary-fixed'
                  : 'border-card-border/60 bg-surface-container-high/50 hover:border-card-border'
              }`}
            >
              <div className="font-semibold text-sm text-on-surface">{label}</div>
              <p className="text-xs text-text-dim mt-1">{desc}</p>
            </button>
          ))}
        </div>

        {err && <p className="mt-4 text-sm text-[color:var(--color-chart-amber)]">{err}</p>}

        <button
          type="button"
          disabled={!selected || loading}
          onClick={handleConfirm}
          className="mt-6 w-full rounded-xl bg-primary-fixed py-2.5 text-sm font-semibold text-on-warm-fill transition hover:opacity-90 disabled:opacity-50"
        >
          {loading ? '登录中...' : '确认登录'}
        </button>

        <p className="mt-4 text-center text-sm text-text-secondary">
          <Link href="/login" className="text-text-dim hover:text-on-surface inline-flex items-center gap-1">
            <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M19 12H5m7-7-7 7 7 7"/></svg>
            返回登录页
          </Link>
        </p>
      </div>
    </div>
  );
}

export default function FeishuMockPage() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4 py-8">
      <Suspense fallback={<p className="text-text-secondary">加载中...</p>}>
        <FeishuMockPick />
      </Suspense>
    </div>
  );
}
