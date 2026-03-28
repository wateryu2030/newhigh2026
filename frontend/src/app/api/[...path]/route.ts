import type { NextRequest } from 'next/server';

/**
 * 将浏览器同源 `/api/*` 转发到 Gateway。
 * - 生产环境请在运行 **Next 的服务端** 设置 `API_PROXY_TARGET`（或回退 `NEXT_PUBLIC_API_TARGET`），
 *   无需仅为改 API 地址而重新 build；仅 `next.config` rewrites 会在构建期固化，易导致 502。
 * @see frontend/next.config.js
 */
export const dynamic = 'force-dynamic';
export const fetchCache = 'force-no-store';

const HOP_BY_HOP = new Set([
  'connection',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailers',
  'transfer-encoding',
  'upgrade',
  'host',
]);

function gatewayOrigin(): string {
  const raw =
    process.env.API_PROXY_TARGET?.trim() ||
    process.env.NEXT_PUBLIC_API_TARGET?.trim() ||
    'http://127.0.0.1:8000';
  return raw.replace(/\/$/, '');
}

function upstreamUrl(pathSegments: string[], search: string): string {
  const tail = pathSegments.length ? pathSegments.join('/') : '';
  const base = `${gatewayOrigin()}/api`;
  return tail ? `${base}/${tail}${search}` : `${base}${search}`;
}

async function proxy(req: NextRequest, path: string[] | undefined) {
  const segments = path ?? [];
  const url = upstreamUrl(segments, req.nextUrl.search);
  const headers = new Headers();
  req.headers.forEach((value, key) => {
    if (HOP_BY_HOP.has(key.toLowerCase())) return;
    headers.set(key, value);
  });

  let body: ArrayBuffer | undefined;
  if (!['GET', 'HEAD'].includes(req.method)) {
    const buf = await req.arrayBuffer();
    if (buf.byteLength) body = buf;
  }

  let res: Response;
  try {
    const ctrl = AbortSignal.timeout(120_000);
    res = await fetch(url, {
      method: req.method,
      headers,
      body,
      signal: ctrl,
      redirect: 'manual',
    });
  } catch (e) {
    const detail = e instanceof Error ? e.message : String(e);
    return new Response(
      JSON.stringify({
        ok: false,
        error: 'gateway_unreachable',
        detail,
        hint: '检查 Gateway 是否监听 API_PROXY_TARGET，或本机防火墙/隧道是否指向 Next 所在机器',
      }),
      { status: 502, headers: { 'Content-Type': 'application/json; charset=utf-8' } }
    );
  }

  const out = new Headers();
  res.headers.forEach((value, key) => {
    if (HOP_BY_HOP.has(key.toLowerCase())) return;
    out.set(key, value);
  });
  return new Response(res.body, { status: res.status, headers: out });
}

type Ctx = { params: { path?: string[] } };

export async function GET(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx.params.path);
}
export async function POST(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx.params.path);
}
export async function PUT(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx.params.path);
}
export async function PATCH(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx.params.path);
}
export async function DELETE(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx.params.path);
}
export async function OPTIONS(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx.params.path);
}
