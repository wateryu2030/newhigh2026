'use client';

import { useCallback, useEffect, useState } from 'react';
import { useLang } from '@/context/LangContext';
import {
  getStockQAJob,
  getStockQAJobReportMarkdown,
  postStockQAAnalyze,
  postStockQAReportMarkdown,
  type StockQAAnalyzeData,
  type StockQAJobPayload,
  type StockQASymbolBlock,
} from '@/api/client';

function formatNum(n: number | null | undefined, digits = 2): string {
  if (n == null || Number.isNaN(n)) return '—';
  if (Math.abs(n) >= 1e8) return `${(n / 1e8).toFixed(2)} 亿`;
  if (Math.abs(n) >= 1e4) return `${(n / 1e4).toFixed(2)} 万`;
  return n.toFixed(digits);
}

function parseOverrideLine(s: string): string[] {
  return s
    .split(/[\s,，;；]+/)
    .map((x) => x.trim())
    .filter(Boolean);
}

function SymbolCard({ row, labels }: { row: StockQASymbolBlock; labels: Record<string, string> }) {
  const q = row.quote || {};
  const f = row.financial;
  const sh = row.shareholders;
  const tr = row.trend;
  const lstm = tr?.lstm as Record<string, unknown> | undefined;

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
          <div className="space-y-1 text-sm leading-relaxed text-on-surface">
            <p>
              <span className="font-medium text-primary-fixed">{tr.bias}</span> · {tr.summary}
              {tr.model ? <span className="text-text-dim"> ({tr.model})</span> : null}
            </p>
            {lstm && typeof lstm.trend_label === 'string' ? (
              <p className="text-text-secondary">
                LSTM：{lstm.trend_label as string}
                {typeof lstm.confidence === 'number'
                  ? ` · 置信度 ${(lstm.confidence as number).toFixed(2)}`
                  : ''}
              </p>
            ) : null}
          </div>
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
  const [asyncMode, setAsyncMode] = useState(false);
  const [useLlm, setUseLlm] = useState(true);
  const [nerMode, setNerMode] = useState<'hybrid' | 'rules_only' | 'llm_only'>('hybrid');
  const [includeLstm, setIncludeLstm] = useState(true);
  const [overrideLine, setOverrideLine] = useState('');
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [result, setResult] = useState<StockQAAnalyzeData | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string | null>(null);
  const labels = {
    quote: t('stockQA.quote'),
    financial: t('stockQA.financial'),
    shareholders: t('stockQA.shareholders'),
    trend: t('stockQA.trend'),
  };

  const applyResult = useCallback((data: StockQAAnalyzeData) => {
    setResult(data);
    setJobStatus(null);
    setJobId(null);
  }, []);

  const pollJob = useCallback(
    async (id: string) => {
      try {
        const st = await getStockQAJob(id);
        setJobStatus(st.status);
        if (st.status === 'completed' && st.result) {
          applyResult(st.result);
          setLoading(false);
        } else if (st.status === 'failed') {
          setErr(st.error || t('stockQA.jobFailed'));
          setLoading(false);
        }
      } catch (e) {
        setErr(String(e));
        setLoading(false);
      }
    },
    [applyResult, t],
  );

  useEffect(() => {
    if (!jobId || !asyncMode) return undefined;
    void pollJob(jobId);
    const id = setInterval(() => void pollJob(jobId), 1600);
    return () => clearInterval(id);
  }, [jobId, asyncMode, pollJob]);

  const buildRequest = () => {
    const raw = text.trim();
    const ov = parseOverrideLine(overrideLine);
    return {
      text: raw,
      max_symbols: maxSym,
      async_mode: asyncMode,
      use_llm_ner: useLlm,
      ner_mode: nerMode,
      include_lstm: includeLstm,
      symbols_override: ov.length ? ov : undefined,
    };
  };

  const run = async () => {
    setErr(null);
    if (!text.trim() && !parseOverrideLine(overrideLine).length) {
      setErr(t('stockQA.empty'));
      return;
    }
    setLoading(true);
    setResult(null);
    setJobId(null);
    try {
      const req = buildRequest();
      const out = await postStockQAAnalyze(req);
      if ('job_id' in out && (out as StockQAJobPayload).async) {
        const jp = out as StockQAJobPayload;
        setJobId(jp.job_id);
        setJobStatus('queued');
        return;
      }
      applyResult(out as StockQAAnalyzeData);
    } catch (e) {
      setErr(String(e));
      setLoading(false);
    } finally {
      if (!asyncMode) setLoading(false);
    }
  };

  const runOverrideOnly = async () => {
    const ov = parseOverrideLine(overrideLine);
    if (!ov.length) {
      setErr(t('stockQA.empty'));
      return;
    }
    setErr(null);
    setLoading(true);
    setResult(null);
    try {
      const out = await postStockQAAnalyze({
        text: '',
        max_symbols: maxSym,
        async_mode: false,
        use_llm_ner: false,
        ner_mode: 'rules_only',
        include_lstm: includeLstm,
        symbols_override: ov,
      });
      if ('job_id' in out && (out as StockQAJobPayload).async) {
        setJobId((out as StockQAJobPayload).job_id);
        return;
      }
      applyResult(out as StockQAAnalyzeData);
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  };

  const exportMd = async () => {
    if (!result) return;
    try {
      const md = await postStockQAReportMarkdown(result);
      const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
      const u = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = u;
      a.download = `stock-qa-${Date.now()}.md`;
      a.click();
      URL.revokeObjectURL(u);
    } catch (e) {
      setErr(String(e));
    }
  };

  const exportJobMd = async () => {
    if (!jobId) return;
    try {
      const md = await getStockQAJobReportMarkdown(jobId);
      const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
      const u = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = u;
      a.download = `stock-qa-job-${jobId}.md`;
      a.click();
      URL.revokeObjectURL(u);
    } catch (e) {
      setErr(String(e));
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
          className="min-h-[180px] w-full resize-y rounded-lg border border-card-border bg-surface-container-high px-3 py-2 text-sm text-on-surface placeholder:text-text-dim"
          placeholder={t('stockQA.placeholder')}
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={loading}
        />

        <div className="flex flex-wrap gap-4 text-sm text-text-secondary">
          <label className="flex cursor-pointer items-center gap-2">
            <input
              type="checkbox"
              checked={asyncMode}
              onChange={(e) => setAsyncMode(e.target.checked)}
              disabled={loading}
            />
            {t('stockQA.async')}
          </label>
          <label className="flex cursor-pointer items-center gap-2">
            <input
              type="checkbox"
              checked={useLlm}
              onChange={(e) => setUseLlm(e.target.checked)}
              disabled={loading}
            />
            {t('stockQA.useLlm')}
          </label>
          <label className="flex cursor-pointer items-center gap-2">
            <input
              type="checkbox"
              checked={includeLstm}
              onChange={(e) => setIncludeLstm(e.target.checked)}
              disabled={loading}
            />
            {t('stockQA.includeLstm')}
          </label>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <label className="text-sm text-text-secondary">
            {t('stockQA.nerMode')}
            <select
              className="ml-2 rounded border border-card-border bg-surface-container-high px-2 py-1 text-on-surface"
              value={nerMode}
              onChange={(e) => setNerMode(e.target.value as typeof nerMode)}
              disabled={loading}
            >
              <option value="hybrid">{t('stockQA.nerHybrid')}</option>
              <option value="rules_only">{t('stockQA.nerRules')}</option>
              <option value="llm_only">{t('stockQA.nerLlm')}</option>
            </select>
          </label>
          <label className="text-sm text-text-secondary">
            {t('stockQA.maxSymbols')}
            <input
              type="number"
              min={1}
              max={12}
              className="ml-2 w-16 rounded border border-card-border bg-surface-container-high px-2 py-1 text-on-surface"
              value={maxSym}
              onChange={(e) => setMaxSym(Number(e.target.value) || 8)}
              disabled={loading}
            />
          </label>
        </div>

        <div>
          <label className="mb-1 block text-xs text-text-dim">{t('stockQA.overrideHint')}</label>
          <input
            type="text"
            className="w-full rounded-lg border border-card-border bg-surface-container-high px-3 py-2 text-sm text-on-surface"
            value={overrideLine}
            onChange={(e) => setOverrideLine(e.target.value)}
            placeholder="600519.SH 000001 300750"
            disabled={loading}
          />
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void run()}
            disabled={loading}
            className="rounded-lg bg-primary-fixed px-5 py-2 text-sm font-medium text-on-warm-fill transition hover:opacity-90 disabled:opacity-50"
          >
            {loading && !asyncMode ? t('common.loading') : t('stockQA.analyze')}
          </button>
          <button
            type="button"
            onClick={() => void runOverrideOnly()}
            disabled={loading}
            className="rounded-lg border border-card-border bg-surface-container-high px-4 py-2 text-sm text-on-surface hover:bg-white/5 disabled:opacity-50"
          >
            {t('stockQA.runOverride')}
          </button>
          {result ? (
            <button
              type="button"
              onClick={() => void exportMd()}
              className="rounded-lg border border-card-border bg-surface-container-high px-4 py-2 text-sm text-on-surface hover:bg-white/5"
            >
              {t('stockQA.exportMd')}
            </button>
          ) : null}
          {jobId && asyncMode ? (
            <button
              type="button"
              onClick={() => void exportJobMd()}
              className="rounded-lg border border-card-border bg-surface-container-high px-4 py-2 text-sm text-on-surface hover:bg-white/5"
            >
              {t('stockQA.exportMd')} (job)
            </button>
          ) : null}
        </div>

        {asyncMode && jobId ? (
          <p className="text-sm text-text-secondary">
            {t('stockQA.jobRunning')} job_id={jobId} status={jobStatus || '…'}
          </p>
        ) : null}
      </div>

      {err ? (
        <div className="rounded-lg border border-red-900/50 bg-red-950/30 px-4 py-3 text-sm text-red-200">
          {err}
        </div>
      ) : null}

      {result ? (
        <div className="space-y-4">
          {result.llm_ner_error ? (
            <p className="text-xs text-amber-300/90">LLM：{result.llm_ner_error}</p>
          ) : null}
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
