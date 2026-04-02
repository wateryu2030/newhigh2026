'use client';

import type { HealthDetailPayload } from '@/api/client';
import { useLang } from '@/context/LangContext';

function celeryLabel(celery: HealthDetailPayload['celery'] | undefined): string {
  if (!celery) return '—';
  if (celery.status === 'ok' && celery.workers?.length) {
    return `${celery.workers.length} worker(s)`;
  }
  return celery.reason || celery.error || celery.status;
}

export function HealthDetailStrip({
  data,
  loadFailed,
}: {
  data: HealthDetailPayload | null;
  loadFailed?: boolean;
}) {
  const { t } = useLang();
  if (loadFailed) {
    return (
      <div
        className="rounded-lg border border-amber-600/40 bg-amber-950/20 px-3 py-2 text-sm text-amber-200/90"
        role="status"
      >
        {t('dashboard.healthDetailFailed')}
      </div>
    );
  }
  if (!data) return null;
  const meta = data.pipeline_meta_recent?.[0];
  const metaHint =
    meta?.k === 'data_orchestrator_last' && meta.v
      ? t('dashboard.healthPipelineHint')
      : meta?.k || '—';

  return (
    <div
      className="flex flex-col gap-2 rounded-lg border border-slate-600/50 bg-slate-900/40 px-3 py-2 text-xs sm:flex-row sm:flex-wrap sm:items-center sm:justify-between sm:text-sm"
      role="region"
      aria-label={t('dashboard.healthDetailTitle')}
    >
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-slate-300">
        <span>
          <span className="text-slate-500">{t('dashboard.healthOverall')}</span>{' '}
          <span
            className={
              data.status === 'ok'
                ? 'font-medium text-emerald-400'
                : 'font-medium text-amber-400'
            }
          >
            {data.status}
          </span>
        </span>
        <span>
          <span className="text-slate-500">{t('dashboard.healthCelery')}</span>{' '}
          <span className="text-slate-200">{celeryLabel(data.celery)}</span>
        </span>
        <span className="hidden sm:inline">
          <span className="text-slate-500">{t('dashboard.healthPipeline')}</span>{' '}
          <span className="max-w-[220px] truncate font-mono text-slate-400" title={meta?.v || ''}>
            {metaHint}
          </span>
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-3 text-slate-500">
        <span>
          {t('dashboard.healthMetrics')}{' '}
          <code className="rounded bg-slate-800 px-1 text-slate-300">{data.prometheus_metrics_path}</code>
        </span>
        {data.alert_webhook_configured ? (
          <span className="text-emerald-500/90">{t('dashboard.healthWebhookOn')}</span>
        ) : (
          <span>{t('dashboard.healthWebhookOff')}</span>
        )}
      </div>
    </div>
  );
}
