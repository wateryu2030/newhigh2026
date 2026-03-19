'use client';

import { useEffect, useState } from 'react';
import { useLang } from '@/context/LangContext';
import { API_BASE_STORAGE_KEY, getApiBase } from '@/api/client';

export default function SettingsPage() {
  const { t } = useLang();
  const [input, setInput] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    try {
      const v = localStorage.getItem(API_BASE_STORAGE_KEY);
      setInput(v || '');
    } catch {
      setInput('');
    }
  }, []);

  const current = typeof window !== 'undefined' ? getApiBase() : '';

  const handleSave = () => {
    const v = input.trim();
    try {
      if (!v) {
        localStorage.removeItem(API_BASE_STORAGE_KEY);
      } else if (v.startsWith('http://') || v.startsWith('https://')) {
        localStorage.setItem(API_BASE_STORAGE_KEY, v.replace(/\/$/, ''));
      }
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
      window.location.reload();
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">{t('settings.title')}</h1>

      <div className="card max-w-2xl space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-300">{t('settings.apiGateway')}</label>
          <p className="mt-1 text-slate-500 text-sm leading-relaxed">{t('settings.apiGatewayHint')}</p>
          <input
            className="mt-2 w-full rounded-lg bg-slate-800 border border-slate-600 px-3 py-2 font-mono text-sm text-white"
            placeholder="http://192.168.1.5:8000"
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          <p className="mt-1 text-xs text-slate-600">
            {t('settings.currentEffective')}: <span className="text-slate-400">{current}</span>
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={handleSave}
            className="rounded-lg bg-indigo-600 hover:bg-indigo-500 px-4 py-2 text-white text-sm"
          >
            {t('settings.saveApi')}
          </button>
          <button
            type="button"
            onClick={() => {
              setInput('');
              try {
                localStorage.removeItem(API_BASE_STORAGE_KEY);
                window.location.reload();
              } catch {
                /* ignore */
              }
            }}
            className="rounded-lg bg-slate-600 hover:bg-slate-500 px-4 py-2 text-white text-sm"
          >
            {t('settings.clearApi')}
          </button>
        </div>
        {saved && <p className="text-sm text-emerald-400">{t('settings.savedReload')}</p>}

        <div className="border-t border-slate-700 pt-4 text-sm text-slate-500 space-y-2">
          <p className="font-medium text-slate-400">{t('settings.lanSteps')}</p>
          <ol className="list-decimal list-inside space-y-1 text-slate-400">
            <li>{t('settings.lanStep1')}</li>
            <li>{t('settings.lanStep2')}</li>
            <li>{t('settings.lanStep3')}</li>
          </ol>
        </div>
      </div>

      <div className="card max-w-xl">
        <label className="block text-sm font-medium text-slate-400">Theme</label>
        <p className="mt-1 text-slate-300">Dark (default)</p>
      </div>
    </div>
  );
}
