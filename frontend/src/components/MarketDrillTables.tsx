'use client';

import type { FundflowDrillItem, LimitupDrillItem, LonghubangDrillItem } from '@/api/client';
import { useLang } from '@/context/LangContext';
import { chgClass, fmtAmountWan, fmtPct, fmtPrice } from '@/lib/marketFormat';

function useDenseClass(dense?: boolean) {
  const th = dense ? 'p-2 text-[11px]' : 'py-2 pr-3 text-xs';
  const td = dense ? 'p-2 text-[11px]' : 'py-2 pr-3 text-sm';
  return { th, td };
}

function Empty({ dense }: { dense?: boolean }) {
  const { t } = useLang();
  return <p className={dense ? 'text-[11px] text-text-secondary' : 'text-sm text-text-secondary'}>{t('systemData.drill.tableEmpty')}</p>;
}

function safeLhbDate(s?: string | null): string {
  if (!s) return '—';
  const u = String(s).toLowerCase();
  if (u.includes('nat') || u === 'none') return '—';
  return s;
}

export function LimitupDrillTable({
  rows,
  dense,
  onRowClick,
}: {
  rows: LimitupDrillItem[];
  dense?: boolean;
  onRowClick?: (row: LimitupDrillItem) => void;
}) {
  const { t } = useLang();
  const { th, td } = useDenseClass(dense);
  if (!rows.length) return <Empty dense={dense} />;
  return (
    <div className="max-h-[55vh] overflow-auto rounded-lg border border-card-border">
      <p className="mb-2 text-[11px] text-text-secondary">{t('drill.rowClickPenetrate')}</p>
      <table className="w-full min-w-[640px] text-left text-text-primary">
        <thead className="sticky top-0 z-[1] border-b border-card-border bg-[#1a1d24]">
          <tr className="text-text-secondary">
            <th className={th}>{t('market.code')}</th>
            <th className={th}>{t('aiTrading.stockName')}</th>
            <th className={th}>{t('aiTrading.lastPrice')}</th>
            <th className={th}>{t('aiTrading.changePct')}</th>
            <th className={th}>{t('drill.limitupTimes')}</th>
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
              <td className={`${td} font-mono`}>{row.code}</td>
              <td className={`${td} max-w-[120px] truncate`} title={row.stock_name}>{row.stock_name?.trim() || '—'}</td>
              <td className={`${td} font-mono`}>{fmtPrice(row.last_price)}</td>
              <td className={`${td} font-mono ${chgClass(row.change_pct)}`}>{fmtPct(row.change_pct)}</td>
              <td className={td}>{row.limit_up_times ?? '—'}</td>
              <td className={`${td} whitespace-nowrap text-text-secondary`}>{row.updated_at ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function LonghubangDrillTable({
  rows,
  dense,
  onRowClick,
}: {
  rows: LonghubangDrillItem[];
  dense?: boolean;
  onRowClick?: (row: LonghubangDrillItem) => void;
}) {
  const { t } = useLang();
  const { th, td } = useDenseClass(dense);
  if (!rows.length) return <Empty dense={dense} />;
  return (
    <div className="max-h-[55vh] overflow-auto rounded-lg border border-card-border">
      {onRowClick ? <p className="mb-2 text-[11px] text-text-secondary">{t('drill.rowClickPenetrate')}</p> : null}
      <table className="w-full min-w-[720px] text-left text-text-primary">
        <thead className="sticky top-0 z-[1] border-b border-card-border bg-[#1a1d24]">
          <tr className="text-text-secondary">
            <th className={th}>{t('market.code')}</th>
            <th className={th}>{t('aiTrading.stockName')}</th>
            <th className={th}>{t('drill.lhbDate')}</th>
            <th className={th}>{t('drill.netBuy')}</th>
            <th className={th}>{t('aiTrading.lastPrice')}</th>
            <th className={th}>{t('aiTrading.changePct')}</th>
            <th className={th}>{t('aiTrading.updatedAt')}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={`${row.code}-${row.lhb_date}-${i}`}
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
              <td className={`${td} font-mono`}>{row.code}</td>
              <td className={`${td} max-w-[120px] truncate`} title={row.stock_name}>{row.stock_name?.trim() || '—'}</td>
              <td className={`${td} font-mono text-text-secondary`}>{safeLhbDate(row.lhb_date)}</td>
              <td className={`${td} font-mono`}>{fmtAmountWan(row.net_buy)}</td>
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

export function FundflowDrillTable({
  rows,
  dense,
  onRowClick,
}: {
  rows: FundflowDrillItem[];
  dense?: boolean;
  onRowClick?: (row: FundflowDrillItem) => void;
}) {
  const { t } = useLang();
  const { th, td } = useDenseClass(dense);
  if (!rows.length) return <Empty dense={dense} />;
  return (
    <div className="max-h-[55vh] overflow-auto rounded-lg border border-card-border">
      {onRowClick ? <p className="mb-2 text-[11px] text-text-secondary">{t('drill.rowClickPenetrate')}</p> : null}
      <table className="w-full min-w-[720px] text-left text-text-primary">
        <thead className="sticky top-0 z-[1] border-b border-card-border bg-[#1a1d24]">
          <tr className="text-text-secondary">
            <th className={th}>{t('market.code')}</th>
            <th className={th}>{t('aiTrading.stockName')}</th>
            <th className={th}>{t('drill.mainNetInflow')}</th>
            <th className={th}>{t('drill.dataDate')}</th>
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
              <td className={`${td} font-mono`}>{row.code}</td>
              <td className={`${td} max-w-[120px] truncate`} title={row.stock_name}>{row.stock_name?.trim() || '—'}</td>
              <td className={`${td} font-mono`}>{fmtAmountWan(row.main_net_inflow)}</td>
              <td className={`${td} font-mono text-text-secondary`}>{row.snapshot_date ?? '—'}</td>
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
