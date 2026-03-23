'use client';

import { useEffect, useState } from 'react';
import { api, type AntiQuantStockResponse } from '@/api/client';
import type { AntiQuantPoolItem } from '@/api/client';

interface StockDrawerProps {
  open: boolean;
  onClose: () => void;
  stock: AntiQuantPoolItem | null;
}

/** 点击表格行时右侧滑出抽屉：展示该股票股东变动流水、机构分类等 */
export function StockDrawer({ open, onClose, stock }: StockDrawerProps) {
  const [detail, setDetail] = useState<AntiQuantStockResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || !stock?.stock_code) {
      setDetail(null);
      return;
    }
    setLoading(true);
    api
      .antiQuantStock(stock.stock_code)
      .then((r) => {
        if (r.ok) setDetail(r as AntiQuantStockResponse);
        else setDetail(null);
      })
      .catch(() => setDetail(null))
      .finally(() => setLoading(false));
  }, [open, stock?.stock_code]);

  if (!open) return null;

  const f = detail?.factors;

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
        onKeyDown={(e) => e.key === 'Escape' && onClose()}
        role="button"
        tabIndex={0}
        aria-label="关闭"
      />
      <aside
        className="animate-drawer-in fixed top-0 right-0 z-50 h-full w-full max-w-md overflow-y-auto shadow-2xl md:w-[420px]"
        style={{
          backgroundColor: '#14171C',
          borderLeft: '1px solid #2A2E36',
        }}
      >
        <div className="sticky top-0 z-10 flex items-center justify-between border-b px-4 py-3" style={{ backgroundColor: '#14171C', borderColor: '#2A2E36' }}>
          <h3 className="text-lg font-bold" style={{ color: '#F1F5F9' }}>
            {stock?.stock_name} ({stock?.stock_code})
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 transition hover:bg-white/10"
            style={{ color: '#94A3B8' }}
            aria-label="关闭"
          >
            <span className="text-xl">×</span>
          </button>
        </div>

        <div className="space-y-4 p-4">
          {loading && (
            <div className="py-8 text-center" style={{ color: '#64748B' }}>
              加载中...
            </div>
          )}

          {!loading && detail?.ok && f && (
            <>
              <div className="rounded-xl p-4" style={{ backgroundColor: '#0A0C10', border: '1px solid #2A2E36' }}>
                <h4 className="mb-3 text-sm font-semibold" style={{ color: '#94A3B8' }}>
                  因子概览
                </h4>
                <dl className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <dt style={{ color: '#64748B' }}>持股集中度</dt>
                    <dd className="font-medium" style={{ color: '#F1F5F9' }}>{f.top10_ratio}%</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt style={{ color: '#64748B' }}>机构数</dt>
                    <dd className="font-medium" style={{ color: '#F1F5F9' }}>{f.institution_count_current}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt style={{ color: '#64748B' }}>长期机构数</dt>
                    <dd className="font-medium" style={{ color: '#F1F5F9' }}>{f.long_term_institution_count}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt style={{ color: '#64748B' }}>换主频率</dt>
                    <dd className="font-medium" style={{ color: '#F1F5F9' }}>{f.turnover_avg != null ? f.turnover_avg.toFixed(2) : '—'}</dd>
                  </div>
                </dl>
              </div>

              {detail.in_pool && (
                <div
                  className="rounded-lg px-3 py-2 text-sm"
                  style={{ backgroundColor: 'rgba(34,197,94,0.15)', color: '#22C55E' }}
                >
                  ✓ 当前在反量化选股池内
                </div>
              )}
            </>
          )}

          {!loading && !detail?.ok && detail !== null && (
            <p className="text-sm" style={{ color: '#64748B' }}>暂无详细数据</p>
          )}
        </div>
      </aside>
    </>
  );
}
