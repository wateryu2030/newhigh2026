'use client';

import type { TradeSignalItem } from '@/api/client';
import { useLang } from '@/context/LangContext';
import { chgClass, fmtPct, fmtPrice, fmtScore01 } from '@/lib/marketFormat';

interface TradeSignalsTableProps {
  rows: TradeSignalItem[];
  /** 弹层内略紧凑 */
  dense?: boolean;
  onRowClick?: (row: TradeSignalItem) => void;
}

/**
 * 融合交易信号表：代码 + 名称 + 现价/涨跌 + 目标/止损 + 缩略时间（传统终端风格）
 */
export function TradeSignalsTable({ rows, dense, onRowClick }: TradeSignalsTableProps) {
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
        <thead className="sticky top-0 z-[1] border-b border-card-border bg-[#1a1d24]">
          <tr className="text-text-secondary">
            <th className={th}>{t('market.code')}</th>
            <th className={th}>{t('aiTrading.stockName')}</th>
            <th className={th}>{t('aiTrading.direction')}</th>
            <th className={th}>{t('aiTrading.signalScore')}</th>
            <th className={th}>{t('aiTrading.confidence')}</th>
            <th className={th}>{t('aiTrading.lastPrice')}</th>
            <th className={th}>{t('aiTrading.changePct')}</th>
            <th className={th}>{t('aiTrading.targetPrice')}</th>
            <th className={th}>{t('aiTrading.stopLoss')}</th>
            <th className={th}>{t('aiTrading.strategyId')}</th>
            <th className={th}>{t('aiTrading.updatedAt')}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => {
            const chg = row.change_pct;
            const chgCls = chgClass(chg);
            const sig = (row.signal ?? '').toUpperCase();
            const sigClass =
              sig === 'BUY' ? 'text-emerald-400' : sig === 'SELL' ? 'text-rose-400' : 'text-text-secondary';
            return (
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
                <td className={`${td} max-w-[140px] truncate font-medium`} title={row.stock_name}>
                  {row.stock_name?.trim() ? row.stock_name : '—'}
                </td>
                <td className={`${td} font-medium ${sigClass}`}>{row.signal ?? '—'}</td>
                <td className={td}>{fmtScore01(row.signal_score)}</td>
                <td className={`${td} text-text-secondary`}>{fmtScore01(row.confidence)}</td>
                <td className={`${td} font-mono`}>{fmtPrice(row.last_price)}</td>
                <td className={`${td} font-mono ${chgCls}`}>{fmtPct(row.change_pct)}</td>
                <td className={`${td} font-mono text-text-secondary`}>{fmtPrice(row.target_price)}</td>
                <td className={`${td} font-mono text-text-secondary`}>{fmtPrice(row.stop_loss)}</td>
                <td className={`${td} text-text-secondary`}>{row.strategy_id?.trim() || '—'}</td>
                <td className={`${td} whitespace-nowrap text-text-secondary`}>{row.updated_at ?? '—'}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
