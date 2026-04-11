'use client';

import { useState } from 'react';
import { useLang } from '@/context/LangContext';
import {
  postStockQAAnalyze,
  type StockQAAnalyzeData,
  type StockQASymbolBlock,
} from '@/api/client';

function formatNum(n: number | null | undefined, digits = 2): string {
  if (n == null || Number.isNaN(n)) return '—';
  if (Math.abs(n) >= 1e8) return `${(n / 1e8).toFixed(2)} 亿`;
  if (Math.abs(n) >= 1e4) return `${(n / 1e4).toFixed(2)} 万`;
  return n.toFixed(digits);
}

function SymbolCard({ row, labels }: { row: StockQASymbolBlock; labels: Record<string, string> }) {
  const q = row.quote || {};
  const f = row.financial;
  const sh = row.shareholders;
  const tr = row.trend;

  return (
    <div className="card space-y-3 border border-card-border p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <span className="text-lg font-semibold text-on-surface">{row.name || row.symbol}</span>
          <span className="ml-2 text-sm text-text-secondary">{row.symbol}</span>
        </div>
        {row.sector ? (
          <span className="rounded-full bg-surface-container-high px-2 py-0.5 text-xs text-text-secondary">
            {row.sector}
          </span>
        ) : null}
      </div>

      {row.errors && row.errors.length > 0 ? (
        <p className="text-sm text-amber-400">{row.errors.join(' ')}</p>
      ) : null}

      <div>
        <h3 className="mb-1 text-xs font-medium uppercase tracking-wide text-text-dim">{labels.quote}</h3>
        <p className="text-sm text-on-surface">
          {q.last_price != null ? (
            <>
              最新约 {q.last_price.toFixed(3)} ，涨跌 {q.change_pct != null ? `${q.change_pct.toFixed(2)}%` : '—'}
              {q.snapshot_time ? (
                <span className="text-text-secondary"> · {q.snapshot_time}</span>
              ) : null}
            </>
          ) : (
            <span className="text-text-secondary">暂无行情快照</span>
          )}
        </p>
      </div>

      <div>
        <h3 className="mb-1 text-xs font-medium uppercase tracking-wide text-text-dim">{labels.financial}</h3>
        {f ? (
          <ul className="list-inside list-disc text-sm text-on-surface">
            <li>报告期 {f.report_date || '—'}</li>
            <li>营收 {formatNum(f.total_revenue)} · 净利 {formatNum(f.net_profit)}</li>
            <li>
              毛利率 {f.gross_margin != null ? `${f.gross_margin.toFixed(2)}%` : '—'} · 净利率{' '}
              {f.net_margin != null ? `${f.net_margin.toFixed(2)}%` : '—'}
            </li>
          </ul>
        ) : (
          <p className="text-sm text-text-secondary">暂无财报入库</p>
        )}
      </div>

      <div>
        <h3 className="mb-1 text-xs font-medium uppercase tracking-wide text-text-dim">{labels.shareholders}</h3>
        {sh?.top_holders && sh.top_holders.length > 0 ? (
          <ul className="text-sm text-on-surface">
            {sh.top_holders.slice(0, 5).map((h, i) => (
              <li key={`${h.name}-${i}`}>
                {h.name}
                {h.ratio != null ? ` · ${h.ratio.toFixed(2)}%` : ''}
              </li>
            ))}
            <li className="text-text-secondary">数据截至 {sh.report_date || '—'}</li>
          </ul>
        ) : (
          <p className="text-sm text-text-secondary">暂无十大股东入库</p>
        )}
      </div>

      <div>
        <h3 className="mb-1 text-xs font-medium uppercase tracking-wide text-text-dim">{labels.trend}</h3>
        {tr ? (
          <p className="text-sm leading-relaxed text-on-surface">
            <span className="font-medium text-primary-fixed">{tr.bias}</span> · {tr.summary}
            {tr.model ? (
              <span className="text-text-dim"> ({tr.model})</span>
            ) : null}
          </p>
        ) : (
          <p className="text-sm text-text-secondary">—</p>
        )}
      </div>
    </div>
  );
}

export default function StockQAPage() {
  const { t } = useLang();
  const [text, setText] = useState('');
  const [maxSym, setMaxSym] = useState(8);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [result, setResult] = useState<StockQAAnalyzeData | null>(null);

  const labels = {
    quote: t('stockQA.quote'),
    financial: t('stockQA.financial'),
    shareholders: t('stockQA.shareholders'),
    trend: t('stockQA.trend'),
  };

  const run = async () => {
    setErr(null);
    setResult(null);
    const raw = text.trim();
    if (!raw) {
      setErr(t('stockQA.empty'));
      return;
    }
    setLoading(true);
    try {
      const data = await postStockQAAnalyze({ text: raw, max_symbols: maxSym });
      setResult(data);
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 pb-24 md:pb-8">
      <div>
        <h1 className="text-2xl font-bold text-on-surface">{t('stockQA.title')}</h1>
        <p className="mt-1 text-sm text-text-secondary">{t('stockQA.subtitle')}</p>
      </div>

      <div className="card space-y-4">
        <textarea
          className="min-h-[200px] w-full resize-y rounded-lg border border-card-border bg-surface-container-high px-3 py-2 text-sm text-on-surface placeholder:text-text-dim"
          placeholder={t('stockQA.placeholder')}
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={loading}
        />
        <div className="flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-2 text-sm text-text-secondary">
            {t('stockQA.maxSymbols')}
            <input
              type="number"
              min={1}
              max={12}
              className="w-16 rounded border border-card-border bg-surface-container-high px-2 py-1 text-on-surface"
              value={maxSym}
              onChange={(e) => setMaxSym(Number(e.target.value) || 8)}
              disabled={loading}
            />
          </label>
          <button
            type="button"
            onClick={() => void run()}
            disabled={loading}
            className="rounded-lg bg-primary-fixed px-5 py-2 text-sm font-medium text-on-warm-fill transition hover:opacity-90 disabled:opacity-50"
          >
            {loading ? t('common.loading') : t('stockQA.analyze')}
          </button>
        </div>
      </div>

      {err ? (
        <div className="rounded-lg border border-red-900/50 bg-red-950/30 px-4 py-3 text-sm text-red-200">
          {err}
        </div>
      ) : null}

      {result ? (
        <div className="space-y-4">
          <div className="card p-4">
            <h2 className="mb-2 text-sm font-semibold text-text-secondary">{t('stockQA.summary')}</h2>
            <p className="text-sm leading-relaxed text-on-surface">{result.summary}</p>
          </div>

          {result.entities.length > 0 ? (
            <div className="card p-4">
              <h2 className="mb-2 text-sm font-semibold text-text-secondary">{t('stockQA.entities')}</h2>
              <ul className="flex flex-wrap gap-2">
                {result.entities.map((e, i) => (
                  <li
                    key={`${e.symbol}-${i}`}
                    className="rounded-full border border-card-border bg-surface-container-high px-3 py-1 text-xs text-on-surface"
                  >
                    {e.mention} → {e.symbol}
                    <span className="text-text-dim"> ({e.source})</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="grid gap-4 lg:grid-cols-2">
            {result.symbols.map((row) => (
              <SymbolCard key={row.symbol} row={row} labels={labels} />
            ))}
          </div>
        </div>
      ) : null}

      <p className="text-xs text-text-dim">{t('stockQA.disclaimer')}</p>
    </div>
  );
}
