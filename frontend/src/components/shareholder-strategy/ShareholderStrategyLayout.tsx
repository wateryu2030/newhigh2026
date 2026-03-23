'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { api, type ShareholderByNameItem, type AntiQuantPoolItem, type AntiQuantPoolResponse } from '@/api/client';
import { KPICard } from './KPICard';
import { StrategyRadarChart } from './StrategyRadarChart';
import { ConcentrationHeatmap } from './ConcentrationHeatmap';
import { StockDrawer } from './StockDrawer';
import { ShareholderHeader } from './ShareholderHeader';
import { ShareholderSidebarLeft } from './ShareholderSidebarLeft';
import { ShareholderSidebarRight } from './ShareholderSidebarRight';
import { CompareModal } from './CompareModal';
import { BacktestModal } from './BacktestModal';
import {
  getIndustryRadarData,
  getBubbleData,
  type Shareholder,
  type Holding,
  type ChangeRecord,
} from '@/data/mockShareholder';

const QUARTERS = [
  '2020Q1', '2020Q2', '2020Q3', '2020Q4', '2021Q1', '2021Q2', '2021Q3', '2021Q4',
  '2022Q1', '2022Q2', '2022Q3', '2022Q4', '2023Q1', '2023Q2', '2023Q3', '2023Q4',
  '2024Q1', '2024Q2', '2024Q3', '2024Q4', '2025Q1', '2025Q2', '2025Q3', '2025Q4',
];

function inferIdentity(t: string): Shareholder['identity'] {
  const s = (t || '').toLowerCase();
  if (s.includes('社保') || (s.includes('基金') && s.includes('社保'))) return '社保';
  if (s.includes('qfii') || s.includes('境外') || s.includes('香港')) return 'QFII';
  if (s.includes('私募') || s.includes('有限合伙')) return '私募';
  if (s.includes('自然人') || s.includes('个人')) return '牛散';
  if (s.includes('公司') || s.includes('集团') || s.includes('有限')) return '产业资本';
  return '私募';
}

function toShareholder(item: ShareholderByNameItem): Shareholder {
  return {
    id: item.name,
    name: item.name,
    identity: inferIdentity(item.shareholder_type),
    tags: [],
    stats: { totalMarketCap: 0, stockCount: item.stock_count, avgHoldPeriod: 0, winRate: 0 },
  };
}

function InstitutionStars({ count }: { count: number }) {
  const stars = Math.min(5, Math.max(0, Math.floor(count / 2)));
  return (
    <span className="inline-flex gap-0.5" title={`机构数: ${count}`}>
      {'★'.repeat(stars)}
      {'☆'.repeat(5 - stars)}
    </span>
  );
}

type SortKey = 'stock_code' | 'top10_ratio' | 'institution_count_current' | 'turnover_avg' | 'latest_report_date';
type SortDir = 'asc' | 'desc';

export function ShareholderStrategyLayout() {
  const [poolRes, setPoolRes] = useState<AntiQuantPoolResponse | null>(null);
  const [poolLoading, setPoolLoading] = useState(true);
  const [selectedShareholder, setSelectedShareholder] = useState<Shareholder | null>(null);
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [changes, setChanges] = useState<ChangeRecord[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<ShareholderByNameItem[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [strategyLoading, setStrategyLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [startQuarter, setStartQuarter] = useState('2020Q1');
  const [endQuarter, setEndQuarter] = useState('2025Q4');
  const [viewQuarter, setViewQuarter] = useState('2024Q1');
  const [drawerStock, setDrawerStock] = useState<AntiQuantPoolItem | null>(null);
  const [tableSort, setTableSort] = useState<{ key: SortKey; dir: SortDir }>({ key: 'top10_ratio', dir: 'desc' });
  const [compareModalOpen, setCompareModalOpen] = useState(false);
  const [backtestStock, setBacktestStock] = useState<Holding | null>(null);
  const [highlightStock, setHighlightStock] = useState<string | null>(null);
  const searchDebounceRef = useRef<ReturnType<typeof setTimeout>>();
  const immediateSubmitRef = useRef(false);

  const timeQuarter = selectedShareholder ? viewQuarter : endQuarter;

  const runSearch = useCallback((q: string) => {
    const t = q.trim();
    if (!t) { setSearchResults([]); setError(null); return; }
    setSearchLoading(true); setError(null);
    api.shareholderByName(t, 20)
      .then((r) => setSearchResults(r.ok && r.data ? r.data : []))
      .catch((e) => setError(`搜索失败：${e?.message || '请确认 Gateway 已启动'}`))
      .finally(() => setSearchLoading(false));
  }, []);

  const handleSearchSubmit = useCallback((q: string) => {
    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
    immediateSubmitRef.current = true;
    setSearchQuery(q);
    runSearch(q);
  }, [runSearch]);

  useEffect(() => {
    if (immediateSubmitRef.current) { immediateSubmitRef.current = false; return; }
    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
    const q = searchQuery.trim();
    if (!q || q.length < 1) { setSearchResults([]); setError(null); return; }
    setSearchLoading(true);
    searchDebounceRef.current = setTimeout(() => runSearch(q), 300);
    return () => { if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current); };
  }, [searchQuery, runSearch]);

  const handleSelectShareholder = useCallback((name: string) => {
    setStrategyLoading(true); setError(null);
    api.shareholderStrategy(name)
      .then((res) => {
        if (!res.ok) {
          setError(res.error || '加载失败');
          setSelectedShareholder(null); setHoldings([]); setChanges([]);
          return;
        }
        const info = res.info;
        setSelectedShareholder(info ? {
          id: info.name, name: info.name,
          identity: (info.identity as Shareholder['identity']) || '私募',
          tags: info.tags || [], stats: info.stats,
        } : { id: name, name, identity: '私募', tags: [], stats: { totalMarketCap: 0, stockCount: res.holdings?.length || 0, avgHoldPeriod: 0, winRate: 0 } });
        setHoldings(res.holdings || []);
        setChanges(res.changes || []);
        if (res.latest_quarter) { setEndQuarter(res.latest_quarter); setViewQuarter(res.latest_quarter); }
      })
      .catch((e) => {
        setError(e?.message || '网络错误');
        setSelectedShareholder(null); setHoldings([]); setChanges([]);
      })
      .finally(() => setStrategyLoading(false));
  }, []);

  useEffect(() => {
    setPoolLoading(true);
    api.antiQuantPool(100, 50)
      .then((r) => { if (r.ok) setPoolRes(r as AntiQuantPoolResponse); })
      .catch(() => {})
      .finally(() => setPoolLoading(false));
  }, []);

  const summary = poolRes?.summary ?? {};
  const poolData = poolRes?.data ?? [];
  const filteredHoldings = holdings.filter((h) => (h.exitQuarter ?? '9999Q4') >= timeQuarter && h.firstEntry <= timeQuarter);
  const filteredChanges = changes.filter((c) => c.quarter <= timeQuarter).slice(0, 20);
  const radarData = getIndustryRadarData(holdings, timeQuarter);

  const handleExportCsv = useCallback(() => {
    const headers = ['季度', '操作类型', '股票代码', '股票名称', '变动股数(万股)', '变动比例(%)'];
    const rows = filteredChanges.map((c) =>
      [c.quarter, c.action, c.stockCode, c.stockName, c.changeShares, c.changeRatio ?? ''].join(',')
    );
    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `股东变动流水_${selectedShareholder?.name ?? 'unknown'}_${timeQuarter}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [filteredChanges, selectedShareholder?.name, timeQuarter]);
  const bubbleData = getBubbleData(holdings, timeQuarter);

  const sortedPool = [...poolData].sort((a, b) => {
    let va: number | string = 0;
    let vb: number | string = 0;
    switch (tableSort.key) {
      case 'top10_ratio': va = a.top10_ratio; vb = b.top10_ratio; break;
      case 'institution_count_current': va = a.institution_count_current; vb = b.institution_count_current; break;
      case 'turnover_avg': va = a.turnover_avg ?? 0; vb = b.turnover_avg ?? 0; break;
      case 'latest_report_date': va = a.latest_report_date ?? ''; vb = b.latest_report_date ?? ''; break;
      default: va = a.stock_code; vb = b.stock_code;
    }
    const cmp = va < vb ? -1 : va > vb ? 1 : 0;
    return tableSort.dir === 'asc' ? cmp : -cmp;
  });

  const handleSort = (key: SortKey) => {
    setTableSort((s) => ({ key, dir: s.key === key && s.dir === 'desc' ? 'asc' : 'desc' }));
  };

  const strategyScores = {
    成长: 65,
    价值: 72,
    动量: 58,
    高频: 35,
    保守: 80,
  };

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#0A0C10' }}>
      <div className="mx-auto max-w-[1600px] px-4 py-6 md:px-6">
        <div className="flex flex-col gap-6 lg:flex-row">
          {/* 左侧边栏 - 桌面端 260px */}
          <aside
            className="hidden w-full shrink-0 lg:block lg:w-[260px]"
            style={{ backgroundColor: '#14171C', border: '1px solid #2A2E36', borderRadius: 16, alignSelf: 'flex-start' }}
          >
            <div className="space-y-4 p-4">
              <h3 className="text-sm font-semibold" style={{ color: '#94A3B8' }}>系统状态</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span style={{ color: '#64748B' }}>延迟</span>
                  <span style={{ color: '#22C55E' }}>12ms</span>
                </div>
                <div className="flex justify-between">
                  <span style={{ color: '#64748B' }}>运行时间</span>
                  <span style={{ color: '#F1F5F9' }}>2d 4h</span>
                </div>
              </div>
              <div className="border-t pt-4" style={{ borderColor: '#2A2E36' }}>
                <h3 className="mb-2 text-sm font-semibold" style={{ color: '#94A3B8' }}>快捷导航</h3>
                <nav className="space-y-1">
                  {['Dashboard', 'Strategy Lab', 'Market', 'Portfolio'].map((label) => (
                    <a key={label} href="#" className="block rounded-lg px-3 py-2 text-sm transition hover:bg-white/5" style={{ color: '#94A3B8' }}>
                      {label}
                    </a>
                  ))}
                </nav>
              </div>
            </div>
          </aside>

          {/* 右侧主内容 */}
          <main className="min-w-0 flex-1 space-y-6">
            {/* 顶部卡片：控制区 */}
            <div
              className="rounded-2xl p-6 transition hover:shadow-lg"
              style={{ backgroundColor: '#14171C', border: '1px solid #2A2E36', boxShadow: '0 2px 8px rgba(0,0,0,0.2)' }}
            >
              <div className="mb-4 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <ShareholderHeader
                  searchResults={searchResults}
                  searchLoading={searchLoading}
                  selected={selectedShareholder}
                  onQueryChange={setSearchQuery}
                  onSearchSubmit={handleSearchSubmit}
                  onSelect={handleSelectShareholder}
                  onCompare={() => setCompareModalOpen(true)}
                />
              </div>
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex flex-wrap items-center gap-3">
                  <label className="text-sm" style={{ color: '#94A3B8' }}>报告期</label>
                  <select
                    value={startQuarter}
                    onChange={(e) => setStartQuarter(e.target.value)}
                    className="rounded-lg px-3 py-2 text-sm"
                    style={{ backgroundColor: '#0A0C10', border: '1px solid #2A2E36', color: '#F1F5F9' }}
                  >
                    {QUARTERS.map((q) => (
                      <option key={q} value={q}>{q}</option>
                    ))}
                  </select>
                  <span style={{ color: '#64748B' }}>至</span>
                  <select
                    value={endQuarter}
                    onChange={(e) => setEndQuarter(e.target.value)}
                    className="rounded-lg px-3 py-2 text-sm"
                    style={{ backgroundColor: '#0A0C10', border: '1px solid #2A2E36', color: '#F1F5F9' }}
                  >
                    {QUARTERS.map((q) => (
                      <option key={q} value={q}>{q}</option>
                    ))}
                  </select>
                  <button
                    type="button"
                    className="rounded-lg px-4 py-2 text-sm font-medium transition hover:opacity-90"
                    style={{ backgroundColor: '#FF3B30', color: '#FFF' }}
                  >
                    应用筛选
                  </button>
                </div>
                <div className="text-right text-xs" style={{ color: '#64748B' }}>
                  最后更新：{new Date().toISOString().slice(0, 10)} · 数据源正常
                </div>
              </div>
            </div>

            {error && (
              <div className="rounded-xl px-4 py-2 text-sm" style={{ backgroundColor: 'rgba(255,59,48,0.1)', border: '1px solid rgba(255,59,48,0.3)', color: '#FF3B30' }}>
                {error}
              </div>
            )}

            {/* 中部卡片：核心指标 KPI */}
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <KPICard
                title="分析股票数"
                value={summary.total_stocks_analyzed ?? 0}
                change={2.1}
                sparklineData={[80, 82, 85, 83, 88, 90, summary.total_stocks_analyzed ?? 0]}
              />
              <KPICard
                title="候选股数"
                value={summary.candidate_count ?? 0}
                change={5.3}
                sparklineData={[12, 15, 14, 18, 20, 22, summary.candidate_count ?? 0]}
              />
              <KPICard
                title="平均持股集中度"
                value={`${summary.avg_top10_ratio ?? '—'}%`}
                change={-0.5}
                sparklineData={[68, 70, 69, 71, 70, 72, Number(summary.avg_top10_ratio) || 70]}
              />
              <KPICard
                title="平均机构数"
                value={summary.avg_institution_count ?? '—'}
                change={1.2}
                sparklineData={[4, 5, 4, 5, 6, 5, Number(summary.avg_institution_count) || 5]}
              />
            </div>

            {/* 下部卡片：表格 + 可视化 */}
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
              <div className="overflow-hidden xl:col-span-7">
                <div
                  className="rounded-2xl overflow-hidden"
                  style={{ backgroundColor: '#14171C', border: '1px solid #2A2E36', boxShadow: '0 2px 8px rgba(0,0,0,0.2)' }}
                >
                  <div className="border-b px-4 py-3" style={{ borderColor: '#2A2E36' }}>
                    <h3 className="font-semibold" style={{ color: '#F1F5F9' }}>候选股票列表</h3>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr style={{ backgroundColor: '#0A0C10', color: '#94A3B8' }}>
                          <th className="cursor-pointer px-4 py-3 text-left hover:opacity-80" onClick={() => handleSort('stock_code')}>股票</th>
                          <th className="cursor-pointer px-4 py-3 text-left" onClick={() => handleSort('top10_ratio')}>持股集中度</th>
                          <th className="cursor-pointer px-4 py-3 text-left" onClick={() => handleSort('institution_count_current')}>机构数</th>
                          <th className="cursor-pointer px-4 py-3 text-left" onClick={() => handleSort('turnover_avg')}>换主频率</th>
                          <th className="px-4 py-3 text-left">机构纯度</th>
                          <th className="cursor-pointer px-4 py-3 text-left" onClick={() => handleSort('latest_report_date')}>报告期</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(poolLoading ? [] : sortedPool).slice(0, 30).map((row) => (
                          <tr
                            key={row.stock_code}
                            className="cursor-pointer transition hover:bg-white/5"
                            style={{ borderBottom: '1px solid #1E2229' }}
                            onClick={() => setDrawerStock(row)}
                          >
                            <td className="px-4 py-3">
                              <span className="font-medium" style={{ color: '#F1F5F9' }}>{row.stock_name}</span>
                              <span className="ml-1 font-mono text-xs" style={{ color: '#64748B' }}>{row.stock_code}</span>
                            </td>
                            <td className="px-4 py-3" style={{ color: row.top10_ratio >= 70 ? '#22C55E' : '#F1F5F9' }}>{row.top10_ratio}%</td>
                            <td className="px-4 py-3" style={{ color: '#F1F5F9' }}>{row.institution_count_current}</td>
                            <td className="px-4 py-3" style={{ color: '#94A3B8' }}>{row.turnover_avg != null ? row.turnover_avg.toFixed(2) : '—'}</td>
                            <td className="px-4 py-3" style={{ color: '#FF3B30' }}>
                              <InstitutionStars count={row.institution_count_current} />
                            </td>
                            <td className="px-4 py-3" style={{ color: '#64748B' }}>{row.latest_report_date ?? '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {poolLoading && (
                    <div className="py-12 text-center" style={{ color: '#64748B' }}>加载中...</div>
                  )}
                </div>
              </div>

              <div className="space-y-6 xl:col-span-5">
                <div
                  className="rounded-2xl overflow-hidden"
                  style={{ backgroundColor: '#14171C', border: '1px solid #2A2E36', boxShadow: '0 2px 8px rgba(0,0,0,0.2)' }}
                >
                  <div className="border-b px-4 py-3" style={{ borderColor: '#2A2E36' }}>
                    <h3 className="font-semibold" style={{ color: '#F1F5F9' }}>股东策略风格雷达</h3>
                  </div>
                  <div className="p-4">
                    <StrategyRadarChart scores={strategyScores} height={240} />
                  </div>
                </div>
                <div
                  className="rounded-2xl overflow-hidden"
                  style={{ backgroundColor: '#14171C', border: '1px solid #2A2E36', boxShadow: '0 2px 8px rgba(0,0,0,0.2)' }}
                >
                  <div className="border-b px-4 py-3" style={{ borderColor: '#2A2E36' }}>
                    <h3 className="font-semibold" style={{ color: '#F1F5F9' }}>筹码稳定性热力图</h3>
                  </div>
                  <div className="p-4">
                    <ConcentrationHeatmap stocks={sortedPool.slice(0, 10)} quarters={QUARTERS.slice(-8)} height={180} />
                  </div>
                </div>
              </div>
            </div>

            {/* 股东策略详情区 - 有选中的股东时显示 */}
            {selectedShareholder && (holdings.length > 0 || changes.length > 0) && (
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
                <div className="lg:col-span-5">
                  <ShareholderSidebarLeft
                    holdings={filteredHoldings}
                    changes={filteredChanges}
                    timeQuarter={timeQuarter}
                    quarters={QUARTERS}
                    onTimeChange={setViewQuarter}
                    onRowClick={(h) => setHighlightStock(h.stockCode)}
                    onBacktest={setBacktestStock}
                    onExportCsv={handleExportCsv}
                  />
                </div>
                <div className="lg:col-span-7">
                  <ShareholderSidebarRight
                    radarData={radarData}
                    bubbleData={bubbleData}
                    holdings={holdings}
                    timeQuarter={timeQuarter}
                    highlightStock={highlightStock}
                    onStockHover={setHighlightStock}
                  />
                </div>
              </div>
            )}
          </main>
        </div>
      </div>

      <StockDrawer open={!!drawerStock} onClose={() => setDrawerStock(null)} stock={drawerStock} />

      <CompareModal
        open={compareModalOpen}
        onClose={() => setCompareModalOpen(false)}
        shareholderA={selectedShareholder}
        shareholders={searchResults.map(toShareholder)}
        holdingsA={holdings}
      />
      <BacktestModal open={!!backtestStock} onClose={() => setBacktestStock(null)} stock={backtestStock} />
    </div>
  );
}
