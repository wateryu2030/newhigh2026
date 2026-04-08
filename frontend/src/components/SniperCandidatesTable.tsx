'use client';

import type { SniperCandidateItem } from '@/api/client';
import { useLang } from '@/context/LangContext';
import { chgClass, fmtPct, fmtPrice, fmtScore01 } from '@/lib/marketFormat';

interface Props {
  rows: SniperCandidateItem[];
  dense?: boolean;
  onRowClick?: (row: SniperCandidateItem) => void;
}

/** 狙击候选：代码/名称/题材/分数/现价/涨跌/更新时间（与交易信号表风格一致） */
export function SniperCandidatesTable({ rows, dense, onRowClick }: Props) {
  const { t } = useLang();
  const th = dense ? 'p-2 text-[11px]' : 'py-2 pr-3 text-xs';
  const td = dense ? 'p-2 text-[11px]' : 'py-2 pr-3 text-sm';

  if (!rows.length) {
    return <p className="text-sm text-text-secondary">{t('systemData.drill.tableEmpty')}</p>;
  }

  return (
    <div className="max-h-[55vh] overflow-auto rounded-lg border border-card-border">
      {onRowClick ? <p className="mb-2 text-[11px] text-text-secondary">{t('drill.rowClickPenetrate')}</p> : null}
      <table className="w-full min-w-[720px] text-left text-text-primary">
        <thead className="sticky top-0 z-[1] border-b border-card-border bg-surface-container">
          <tr className="text-text-secondary">
            <th className={th}>{t('market.code')}</th>
            <th className={th}>{t('aiTrading.stockName')}</th>
            <th className={th}>{t('aiTrading.theme')}</th>
            <th className={th}>{t('aiTrading.sniperScoreCol')}</th>
            <th className={th}>{t('aiTrading.confidence')}</th>
            <th className={th}>{t('aiTrading.lastPrice')}</th>
            <th className={th}>{t('aiTrading.changePct')}</th>
            <th className={th}>{t('aiTrading.updatedAt')}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={`${row.code}-${i}`}
              onClick={() => onRowClick?.(row)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onRowClick?.(row);
                }
              }}
              tabIndex={onRowClick ? 0 : undefined}
              role={onRowClick ? 'button' : undefined}
              className={`border-b border-card-border/40 hover:bg-white/[0.06] ${onRowClick ? 'cursor-pointer' : ''}`}
            >
              <td className={`${td} font-mono text-text-secondary`}>{row.code}</td>
              <td className={`${td} max-w-[120px] truncate font-medium`} title={row.stock_name}>
                {row.stock_name?.trim() ? row.stock_name : '—'}
              </td>
              <td className={`${td} max-w-[100px] truncate text-text-secondary`} title={row.theme}>
                {row.theme && row.theme !== '—' ? row.theme : t('aiTrading.themeUncat')}
              </td>
              <td className={`${td} font-medium text-accent-red`}>{fmtScore01(row.sniper_score)}</td>
              <td className={`${td} text-text-secondary`}>{fmtScore01(row.confidence)}</td>
              <td className={`${td} font-mono`}>{fmtPrice(row.last_price)}</td>
              <td className={`${td} font-mono ${chgClass(row.change_pct)}`}>{fmtPct(row.change_pct)}</td>
              <td className={`${td} whitespace-nowrap text-text-secondary`}>{row.updated_at ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
