'use client';

import { useState, useEffect } from 'react';
import { api, type AntiQuantPoolItem, type AntiQuantPoolResponse } from '@/api/client';

export function AntiQuantPoolSection() {
  const [res, setRes] = useState<AntiQuantPoolResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api
      .antiQuantPool(50, 50)
      .then((r) => {
        if (r.ok) setRes(r as AntiQuantPoolResponse);
        else setError(r.error || '加载失败');
      })
      .catch((e) => setError(e?.message || '请求失败'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="rounded-lg border border-card-border bg-card-bg/80 px-4 py-6 text-center text-text-secondary">
        加载反量化选股池中...
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-[color:var(--color-warning-banner-border)] bg-[color:var(--color-warning-banner-bg)] px-4 py-2 text-sm text-[color:var(--color-badge-amber-text)]">
        反量化选股池加载失败：{error}
      </div>
    );
  }

  if (!res?.ok || !res.data?.length) {
    return (
      <div className="card">
        <h3 className="mb-2 text-sm font-semibold text-on-surface">反量化长线选股池</h3>
        <p className="text-sm text-text-secondary">{res?.note || '暂无候选股票'}</p>
      </div>
    );
  }

  const { summary, data, note, filter_mode } = res;

  return (
    <div className="card space-y-4">
      <h3 className="text-sm font-semibold text-on-surface">反量化长线选股池</h3>
      <p className="text-xs text-text-dim">
        基于股东稳定性、机构纯度、换主频率筛选；列表补充 <strong className="text-text-secondary">HHI</strong>、
        <strong className="text-text-secondary">前十大占比环比</strong>、<strong className="text-text-secondary">筹码得分</strong>（启发式，非投资建议）
      </p>

      {/* 因子汇总卡片 */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-lg bg-surface-container-high/50 px-3 py-2">
          <div className="text-xs text-text-secondary">分析股票数</div>
          <div className="text-lg font-bold text-on-surface">{summary?.total_stocks_analyzed ?? 0}</div>
        </div>
        <div className="rounded-lg bg-surface-container-high/50 px-3 py-2">
          <div className="text-xs text-text-secondary">候选股数</div>
          <div className="text-lg font-bold text-accent-green">{summary?.candidate_count ?? 0}</div>
        </div>
        <div className="rounded-lg bg-surface-container-high/50 px-3 py-2">
          <div className="text-xs text-text-secondary">平均持股集中度</div>
          <div className="text-lg font-bold text-on-surface">{summary?.avg_top10_ratio ?? '—'}%</div>
        </div>
        <div className="rounded-lg bg-surface-container-high/50 px-3 py-2">
          <div className="text-xs text-text-secondary">平均机构数</div>
          <div className="text-lg font-bold text-on-surface">{summary?.avg_institution_count ?? '—'}</div>
        </div>
        {summary?.avg_chip_score != null && (
          <div className="rounded-lg bg-surface-container-high/50 px-3 py-2 sm:col-span-2">
            <div className="text-xs text-text-secondary">平均筹码得分</div>
            <div className="text-lg font-bold text-[color:var(--color-data-cyan)]">{summary.avg_chip_score}</div>
          </div>
        )}
      </div>

      {filter_mode === 'relaxed' && (
        <p className="rounded bg-[color:var(--color-badge-amber-bg)] px-2 py-1 text-xs text-[color:var(--color-badge-amber-text)]">
          ⚠ 当前为放宽模式（报告期不足 4 期）：持股集中度≥50%、机构数≥2。完整 5 年数据后可启用严格规则。
        </p>
      )}

      {/* 候选股表格 */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-card-border text-text-secondary">
              <th className="pb-2 pr-2">股票</th>
              <th className="pb-2 pr-2">筹码分</th>
              <th className="pb-2 pr-2">持股集中度</th>
              <th className="pb-2 pr-2">HHI</th>
              <th className="pb-2 pr-2">前十Δ%</th>
              <th className="pb-2 pr-2">机构数</th>
              <th className="pb-2 pr-2">换主频率</th>
              <th className="pb-2 pr-2">报告期</th>
            </tr>
          </thead>
          <tbody>
            {data.slice(0, 20).map((row: AntiQuantPoolItem) => (
              <tr key={row.stock_code} className="border-b border-card-border/80">
                <td className="py-2 pr-2">
                  <span className="font-medium text-on-surface">{row.stock_name}</span>
                  <span className="ml-1 text-text-dim">{row.stock_code}</span>
                </td>
                <td className="py-2 pr-2 tabular-nums text-[color:var(--color-data-cyan)]">
                  {row.chip_score != null ? row.chip_score : '—'}
                </td>
                <td className="py-2 pr-2 text-on-surface">{row.top10_ratio}%</td>
                <td className="py-2 pr-2 tabular-nums text-text-primary">
                  {row.hhi_top10 != null ? row.hhi_top10 : '—'}
                </td>
                <td className="py-2 pr-2 tabular-nums text-text-primary">
                  {row.top10_delta_pp != null ? (row.top10_delta_pp > 0 ? `+${row.top10_delta_pp}` : row.top10_delta_pp) : '—'}
                </td>
                <td className="py-2 pr-2 text-text-primary">{row.institution_count_current}</td>
                <td className="py-2 pr-2 text-text-primary">
                  {row.turnover_avg != null ? row.turnover_avg : '—'}
                </td>
                <td className="py-2 pr-2 text-text-dim">{row.latest_report_date ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data.length > 20 && (
        <p className="text-xs text-text-dim">仅展示前 20 只，共 {data.length} 只候选</p>
      )}
      {note && <p className="text-xs text-text-dim">{note}</p>}
    </div>
  );
}
