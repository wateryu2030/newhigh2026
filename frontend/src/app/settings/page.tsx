'use client';

import { useLang } from '@/context/LangContext';

export default function SettingsPage() {
  const { t } = useLang();
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">{t('settings.title')}</h1>
      <div className="card max-w-xl space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-400">Theme</label>
          <p className="mt-1 text-slate-300">Dark (default)</p>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-400">API base</label>
          <p className="mt-1 font-mono text-sm text-slate-300">/api (proxy to gateway)</p>
        </div>
      </div>
    </div>
  );
}
