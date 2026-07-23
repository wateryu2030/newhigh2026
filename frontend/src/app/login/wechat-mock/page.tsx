'use client';

import { apiPostJson, AUTH_TOKEN_STORAGE_KEY } from '@/lib/auth-client';
import { notifyAuthChanged } from '@/context/AuthContext';
import { useSearchParams } from 'next/navigation';
import { useCallback, useState, Suspense } from 'react';

type RoleOption = 'viewer' | 'operator' | 'admin';

interface MockCompleteResponse {
  token: string;
  access_token: string;
  user_id: string;
  username: string;
  user: string;
  role: string;
  user_level: string;
}

const ROLE_OPTIONS: { role: RoleOption; label: string; description: string; color: string }[] = [
  {
    role: 'viewer',
    label: '用户',
    description: '普通用户，查看行情与数据',
    color: 'border-[#07C160]/30 text-[#07C160] hover:bg-[#07C160]/10 hover:border-[#07C160]/60',
  },
  {
    role: 'operator',
    label: '运营',
    description: '运营人员，管理系统内容',
    color: 'border-blue-400/30 text-blue-600 hover:bg-blue-50 hover:border-blue-400/60',
  },
  {
    role: 'admin',
    label: '管理员',
    description: '管理员，拥有全部权限',
    color: 'border-amber-400/30 text-amber-600 hover:bg-amber-50 hover:border-amber-400/60',
  },
];

function WechatMockInner() {
  const sp = useSearchParams();
  const ticket = sp?.get('t') ?? '';
  const [selectedRole, setSelectedRole] = useState<RoleOption | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const handleConfirm = useCallback(async () => {
    if (!selectedRole) return;
    setLoading(true);
    setError(null);
    try {
      const res = await apiPostJson<MockCompleteResponse>('/auth/wechat/mock-complete', {
        ticket: ticket || 'direct',
        role: selectedRole,
      });
      // 处理信封包裹
      let token: string;
      let username: string;
      if (res && typeof res === 'object' && 'ok' in res && (res as Record<string, unknown>).ok === true) {
        const data = (res as Record<string, unknown>).data as MockCompleteResponse;
        token = data.token;
        username = data.username;
      } else {
        token = (res as MockCompleteResponse).token;
        username = (res as MockCompleteResponse).username;
      }
      if (!token) {
        throw new Error('登录失败：未收到 token');
      }
      localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
      notifyAuthChanged();
      setDone(true);
      setTimeout(() => {
        const next = sp?.get('next');
        window.location.href = next && next.startsWith('/') ? next : '/';
      }, 600);
    } catch (e) {
      setError(e instanceof Error ? e.message : '登录失败');
    } finally {
      setLoading(false);
    }
  }, [selectedRole, ticket, sp]);

  if (done) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center px-4 py-8">
        <div className="text-center max-w-md">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
            <svg className="h-8 w-8 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="mt-4 text-xl font-bold text-on-surface">登录成功</h2>
          <p className="mt-2 text-sm text-text-secondary">正在跳转...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4 py-8">
      <div className="mx-auto w-full max-w-md">
        <div className="rounded-3xl border border-card-border/80 bg-card/95 p-6 shadow-xl ring-1 ring-white/60 backdrop-blur-sm md:p-8">
          <div className="text-center mb-6">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-[#07C160]/10 mb-3">
              <svg className="h-7 w-7 text-[#07C160]" viewBox="0 0 24 24" fill="currentColor">
                <path d="M8.5 11a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zm7 0a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zM12 2C6.477 2 2 6.477 2 12c0 1.82.487 3.53 1.338 5.002L2 22l5.14-1.264A9.956 9.956 0 0 0 12 22c5.523 0 10-4.477 10-10S17.523 2 12 2z"/>
              </svg>
            </div>
            <h2 className="text-xl font-bold text-on-surface">微信扫码登录</h2>
            <p className="mt-1 text-xs text-text-dim">
              模拟模式 — 选择身份后直接登录
            </p>
          </div>

          <p className="mb-4 text-sm font-medium text-on-surface text-center">
            请选择登录身份
          </p>

          <div className="space-y-3">
            {ROLE_OPTIONS.map((opt) => (
              <button
                key={opt.role}
                type="button"
                disabled={loading}
                onClick={() => setSelectedRole(opt.role)}
                className={`w-full rounded-xl border-2 px-4 py-3 text-left transition disabled:opacity-50 ${
                  selectedRole === opt.role
                    ? 'border-[#07C160] bg-[#07C160]/10 ring-2 ring-[#07C160]/30'
                    : opt.color
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm font-semibold">{opt.label}</span>
                    <p className="text-xs text-text-dim mt-0.5">{opt.description}</p>
                  </div>
                  <div className={`h-5 w-5 rounded-full border-2 flex items-center justify-center ${
                    selectedRole === opt.role
                      ? 'border-[#07C160] bg-[#07C160]'
                      : 'border-text-dim'
                  }`}>
                    {selectedRole === opt.role && (
                      <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </div>
                </div>
              </button>
            ))}
          </div>

          {error && (
            <p className="mt-3 text-sm text-red-500 bg-red-50 rounded-xl px-4 py-3 text-center" role="alert">
              {error}
            </p>
          )}

          <button
            type="button"
            disabled={!selectedRole || loading}
            onClick={handleConfirm}
            className="mt-5 w-full rounded-xl bg-[#07C160] py-2.5 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-50"
          >
            {loading ? '正在登录...' : '确认登录'}
          </button>

          <p className="mt-4 text-center text-xs text-text-secondary">
            <a href="/login" className="inline-flex items-center gap-1 text-[#07C160] hover:underline">
              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
              </svg>
              返回登录页
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}

export default function LoginWechatMockPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-[60vh] items-center justify-center">
        <p className="text-text-secondary">加载中...</p>
      </div>
    }>
      <WechatMockInner />
    </Suspense>
  );
}
