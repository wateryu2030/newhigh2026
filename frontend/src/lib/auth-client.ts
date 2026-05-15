/**
 * 登录 / 注册 / OAuth 引导专用请求层（与 Gateway /api 对齐）。
 * 与 `@/api/client` 行为一致，但不引入整包 client（千余行）——避免 dev 下服务端 chunk 编号错配（Cannot find module './NNN.js'）。
 */
export const AUTH_TOKEN_STORAGE_KEY = 'newhigh_jwt_token';
const API_BASE_STORAGE_KEY = 'newhigh_api_base';
const SERVER_API_BASE = process.env.NEXT_PUBLIC_API_TARGET || 'http://127.0.0.1:8000';

function getAuthHeaders(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  try {
    const token = localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)?.trim();
    if (token) return { Authorization: `Bearer ${token}` };
  } catch {
    /* ignore */
  }
  return {};
}

function redirectToLogin(): void {
  if (typeof window === 'undefined') return;
  const path = window.location.pathname || '';
  if (path.startsWith('/login') || path.startsWith('/register')) return;
  if (path === '/news' || path.startsWith('/news/')) return;
  const next = encodeURIComponent(window.location.pathname + window.location.search);
  window.location.href = `/login?next=${next}`;
}

export function getApiBase(): string {
  if (typeof window === 'undefined') {
    return SERVER_API_BASE;
  }
  try {
    const v = localStorage.getItem(API_BASE_STORAGE_KEY)?.trim();
    if (
      v &&
      (v.startsWith('http://') || v.startsWith('https://')) &&
      v.length >= 12
    ) {
      return v.replace(/\/$/, '');
    }
  } catch {
    /* ignore */
  }
  return '';
}

type ApiGetOptions = { unwrapEnvelope?: boolean; timeoutMs?: number };

async function apiGet<T>(path: string, options?: ApiGetOptions): Promise<T> {
  const base = getApiBase();
  const url = path.startsWith('http')
    ? path
    : base
      ? `${base}/api${path}`
      : `/api${path}`;
  const ms = options?.timeoutMs;
  const ctrl = typeof AbortController !== 'undefined' ? new AbortController() : undefined;
  const tid =
    ctrl != null && ms != null && ms > 0
      ? setTimeout(() => ctrl.abort(), ms)
      : undefined;
  let res: Response;
  try {
    res = await fetch(url, {
      cache: 'no-store',
      headers: { ...getAuthHeaders() },
      signal: ctrl?.signal,
    });
  } finally {
    if (tid != null) clearTimeout(tid);
  }
  if (res.status === 401) {
    redirectToLogin();
    throw new Error('Unauthorized');
  }
  if (!res.ok) throw new Error(`API ${path}: ${res.status}`);
  const json: unknown = await res.json();
  if (options?.unwrapEnvelope && json && typeof json === 'object' && 'ok' in json) {
    const o = json as { ok?: boolean; data?: unknown; error?: string };
    if (o.ok === false) throw new Error(o.error || 'API error');
    return o.data as T;
  }
  return json as T;
}

export async function apiPostJson<T>(path: string, body?: unknown): Promise<T> {
  const base = getApiBase();
  const url = path.startsWith('http')
    ? path
    : base
      ? `${base}/api${path}`
      : `/api${path}`;
  const res = await fetch(url, {
    method: 'POST',
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: body !== undefined ? JSON.stringify(body) : '{}',
  });
  if (res.status === 401) {
    redirectToLogin();
    throw new Error('Unauthorized');
  }
  if (!res.ok) throw new Error(`API ${path}: ${res.status}`);
  return res.json() as Promise<T>;
}

export interface AuthOAuthUrlPayload {
  configured: boolean;
  authorize_url: string | null;
  hint?: string;
  state?: string;
}

export async function getWechatAuthUrl(): Promise<AuthOAuthUrlPayload> {
  return apiGet<AuthOAuthUrlPayload>('/auth/wechat/url', { unwrapEnvelope: true });
}

export async function getFeishuAuthUrl(): Promise<AuthOAuthUrlPayload> {
  return apiGet<AuthOAuthUrlPayload>('/auth/feishu/url', { unwrapEnvelope: true });
}
