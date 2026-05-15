/**
 * 与 Gateway `/api` 对话的轻量客户端；浏览器用 fetch，Taro 可传入 request 实现。
 */
export type RequestImpl = (args: {
  url: string;
  method?: string;
  headers?: Record<string, string>;
  body?: string;
}) => Promise<{ status: number; text: () => Promise<string> }>;

const defaultFetch: RequestImpl = async (args) => {
  const res = await fetch(args.url, {
    method: args.method || 'GET',
    headers: args.headers,
    body: args.body,
  });
  return {
    status: res.status,
    text: () => res.text(),
  };
};

export function createApiClient(opts: {
  baseUrl: string;
  getToken?: () => string | null;
  request?: RequestImpl;
}) {
  const req = opts.request || defaultFetch;
  const base = opts.baseUrl.replace(/\/$/, '');

  async function getJson(path: string): Promise<unknown> {
    const token = opts.getToken?.();
    const headers: Record<string, string> = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    const r = await req({
      url: `${base}${path.startsWith('/') ? path : `/${path}`}`,
      method: 'GET',
      headers,
    });
    const raw = await r.text();
    try {
      return JSON.parse(raw);
    } catch {
      return { raw };
    }
  }

  return { getJson };
}
