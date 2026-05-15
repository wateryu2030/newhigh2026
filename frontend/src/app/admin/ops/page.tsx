'use client';

import { useEffect, useState } from 'react';
import { apiGet } from '@/api/client';

/** 运维：拉取 /api/health/detailed（JWT_AUTH_REQUIRED=1 时需白名单或带 Token） */
export default function AdminOpsPage() {
  const [raw, setRaw] = useState<unknown>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const data = await apiGet<unknown>('/health/detailed', { unwrapEnvelope: true });
        setRaw(data);
      } catch (e) {
        setErr(String(e));
      }
    })();
  }, []);

  return (
    <div className="space-y-4 px-4 pb-24 pt-6">
      <h1 className="text-xl font-semibold text-on-surface">系统健康（详细）</h1>
      <p className="text-xs text-text-dim">来源：GET /api/health/detailed</p>
      {err ? <p className="text-sm text-amber-400">{err}</p> : null}
      <pre className="max-h-[70vh] overflow-auto rounded-lg border border-card-border bg-surface-container-high p-4 text-xs text-text-code">
        {raw ? JSON.stringify(raw, null, 2) : '加载中…'}
      </pre>
    </div>
  );
}
