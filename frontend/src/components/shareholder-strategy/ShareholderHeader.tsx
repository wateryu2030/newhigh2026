'use client';

import { useState, useRef, useEffect } from 'react';
import type { Shareholder } from '@/data/mockShareholder';
import type { ShareholderByNameItem } from '@/api/client';

interface ShareholderHeaderProps {
  searchResults: ShareholderByNameItem[];
  searchLoading: boolean;
  selected: Shareholder | null;
  /** 后端宽松匹配提示（首尾字 / difflib） */
  searchHint?: string | null;
  onQueryChange: (q: string) => void;
  onSearchSubmit?: (q: string) => void;
  onSelect: (name: string) => void;
  onCompare: () => void;
}

const IDENTITY_LABEL: Record<string, string> = {
  QFII: 'QFII',
  私募: '私募',
  牛散: '牛散',
  社保: '社保',
  产业资本: '产业资本',
};

function _inferIdentity(shareholderType: string): string {
  const t = (shareholderType || '').toLowerCase();
  if (t.includes('社保') || (t.includes('基金') && t.includes('社保'))) return '社保';
  if (t.includes('qfii') || t.includes('境外') || t.includes('香港')) return 'QFII';
  if (t.includes('私募') || t.includes('有限合伙')) return '私募';
  if (t.includes('自然人') || t.includes('个人')) return '牛散';
  if (t.includes('公司') || t.includes('集团') || t.includes('有限')) return '产业资本';
  return '私募';
}

export function ShareholderHeader({
  searchResults,
  searchLoading,
  selected,
  searchHint,
  onQueryChange,
  onSearchSubmit,
  onSelect,
  onCompare,
}: ShareholderHeaderProps) {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    onQueryChange(query);
  }, [query, onQueryChange]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const showDropdown = open && query.trim().length >= 1;

  return (
    <div className="space-y-4" ref={ref}>
      {/* 搜索框 */}
      <div className="relative">
        <input
          type="text"
          autoComplete="off"
          placeholder="股东名称：子串匹配；无结果时自动首尾字/近似名（如 王…忱 → 王世忱）"
          className="w-full rounded-lg border border-card-border bg-terminal-bg px-4 py-2.5 text-text-primary focus:border-primary-fixed focus:outline-none focus:ring-2 focus:ring-primary-fixed"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              const q = query.trim();
              if (q && onSearchSubmit) onSearchSubmit(q);
            }
          }}
        />
        {showDropdown && (
          <ul className="absolute left-0 right-0 top-full z-50 mt-1 max-h-48 overflow-auto rounded-lg border border-card-border bg-card-bg py-1 shadow-xl">
            {searchLoading ? (
              <li className="px-4 py-3 text-sm text-text-secondary">搜索中...</li>
            ) : searchResults.length === 0 ? (
              <li className="px-4 py-3 text-sm text-text-secondary">
                未找到匹配股东
                <span className="mt-1 block text-xs text-text-dim">
                  请确认 Gateway 已启动：uvicorn gateway.app:app --port 8000
                </span>
              </li>
            ) : (
              searchResults.map((s) => (
                <li key={s.name}>
                  <button
                    type="button"
                    className="flex w-full items-center justify-between px-4 py-2 text-left text-sm text-text-primary transition hover:bg-white/5"
                    onClick={() => {
                      onSelect(s.name);
                      setQuery(s.name);
                      setOpen(false);
                    }}
                  >
                    <span>{s.name}</span>
                    <span className="rounded bg-card-border px-2 py-0.5 text-xs text-text-secondary">
                      {(IDENTITY_LABEL[_inferIdentity(s.shareholder_type)] ?? s.shareholder_type) || '—'}
                    </span>
                    <span className="text-xs text-text-dim">{s.stock_count} 只</span>
                  </button>
                </li>
              ))
            )}
          </ul>
        )}
        {searchHint && query.trim().length >= 1 && (
          <p className="mt-2 rounded-lg bg-[color:var(--color-badge-amber-bg)] px-3 py-2 text-xs leading-relaxed text-[color:var(--color-badge-amber-text)]">
            {searchHint}
          </p>
        )}
      </div>

      {/* 股东概览卡 */}
      {selected && (
        <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-card-border bg-[color:var(--color-header-glass)] p-4">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[color:var(--color-tag-primary-bg)] text-lg font-bold text-primary-fixed">
              {selected.name.slice(0, 1)}
            </div>
            <div>
              <h2 className="font-semibold text-text-primary">{selected.name}</h2>
              <div className="mt-1 flex flex-wrap gap-2">
                {selected.tags.map((t) => (
                  <span key={t} className="rounded bg-card-border px-2 py-0.5 text-xs text-text-secondary">
                    {t}
                  </span>
                ))}
                <span className="rounded bg-[color:var(--color-tag-primary-bg)] px-2 py-0.5 text-xs text-primary-fixed">
                  {IDENTITY_LABEL[selected.identity] ?? selected.identity}
                </span>
              </div>
            </div>
          </div>
          <div className="flex flex-wrap gap-6">
            <div className="text-center">
              <div className="text-lg font-bold text-text-primary">{selected.stats.totalMarketCap.toFixed(1)}</div>
              <div className="text-xs text-text-secondary">总持仓市值(亿)</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-text-primary">{selected.stats.stockCount}</div>
              <div className="text-xs text-text-secondary">持股数量</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-text-primary">{selected.stats.avgHoldPeriod}</div>
              <div className="text-xs text-text-secondary">平均持股周期(月)</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-accent-green">{selected.stats.winRate}%</div>
              <div className="text-xs text-text-secondary">胜率</div>
            </div>
          </div>
          <button
            type="button"
            onClick={onCompare}
            className="rounded-lg bg-primary-fixed px-4 py-2 text-sm font-medium text-on-warm-fill transition hover:opacity-90"
          >
            对比分析
          </button>
        </div>
      )}
    </div>
  );
}
