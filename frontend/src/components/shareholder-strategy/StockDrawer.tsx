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
        className="fixed inset-0 z-40 bg-[color:var(--color-overlay-scrim)] backdrop-blur-sm"
        onClick={onClose}
        onKeyDown={(e) => e.key === 'Escape' && onClose()}
        role="button"
        tabIndex={0}
        aria-label="关闭"
      />
      <aside className="animate-drawer-in fixed right-0 top-0 z-50 h-full w-full max-w-md overflow-y-auto border-l border-card-border bg-card-bg shadow-2xl md:w-[420px]">
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-card-border bg-card-bg px-4 py-3">
          <h3 className="text-lg font-bold text-text-primary">
            {stock?.stock_name} ({stock?.stock_code})
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-text-secondary transition hover:bg-white/10"
            aria-label="关闭"
          >
            <span className="text-xl">×</span>
          </button>
        </div>

        <div className="space-y-4 p-4">
          {loading && <div className="py-8 text-center text-text-dim">加载中...</div>}

          {!loading && detail?.ok && f && (
            <>
              <div className="rounded-xl border border-card-border bg-terminal-bg p-4">
                <h4 className="mb-3 text-sm font-semibold text-text-secondary">因子概览</h4>
                <dl className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <dt className="text-text-dim">持股集中度</dt>
                    <dd className="font-medium text-text-primary">{f.top10_ratio}%</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-text-dim">机构数</dt>
                    <dd className="font-medium text-text-primary">{f.institution_count_current}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-text-dim">长期机构数</dt>
                    <dd className="font-medium text-text-primary">{f.long_term_institution_count}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-text-dim">换主频率</dt>
                    <dd className="font-medium text-text-primary">
                      {f.turnover_avg != null ? f.turnover_avg.toFixed(2) : '—'}
                    </dd>
                  </div>
                </dl>
                {detail.chip && (
                  <div className="mt-4 border-t border-card-border pt-3">
                    <h4 className="mb-2 text-sm font-semibold text-text-secondary">筹码结构</h4>
                    <dl className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <dt className="text-text-dim">筹码得分</dt>
                        <dd className="font-medium text-[color:var(--color-data-cyan)]">
                          {detail.chip.chip_score != null ? detail.chip.chip_score : '—'}
                        </dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-text-dim">前十大 HHI</dt>
                        <dd className="font-medium text-text-primary">
                          {detail.chip.hhi_top10 != null ? detail.chip.hhi_top10 : '—'}
                        </dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-text-dim">前十占比环比(pts)</dt>
                        <dd className="font-medium text-text-primary">
                          {detail.chip.top10_delta_pp != null
                            ? `${detail.chip.top10_delta_pp > 0 ? '+' : ''}${detail.chip.top10_delta_pp}`
                            : '—'}
                        </dd>
                      </div>
                    </dl>
                  </div>
                )}
              </div>

              {detail.in_pool && (
                <div className="rounded-lg bg-[color:var(--color-success-alpha-15)] px-3 py-2 text-sm text-accent-green">
                  ✓ 当前在反量化选股池内
                </div>
              )}
            </>
          )}

          {!loading && !detail?.ok && detail !== null && (
            <p className="text-sm text-text-dim">暂无详细数据</p>
          )}
        </div>
      </aside>
    </>
  );
}
