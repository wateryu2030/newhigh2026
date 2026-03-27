'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import {
  api,
  type ShareholderByNameItem,
  type AntiQuantPoolItem,
  type AntiQuantPoolResponse,
  type CoShareholderItem,
} from '@/api/client';
import { KPICard } from './KPICard';
import { ConcentrationHeatmap } from './ConcentrationHeatmap';
import { StockDrawer } from './StockDrawer';
import { ShareholderHeader } from './ShareholderHeader';
import { ShareholderSidebarLeft } from './ShareholderSidebarLeft';
import { ShareholderSidebarRight } from './ShareholderSidebarRight';
import { CompareModal } from './CompareModal';
import { BacktestModal } from './BacktestModal';
import { StockPenetrationPanel } from '@/components/StockPenetrationPanel';
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

type SortKey =
  | 'stock_code'
  | 'chip_score'
  | 'hhi_top10'
  | 'top10_delta_pp'
  | 'top10_ratio'
  | 'institution_count_current'
  | 'turnover_avg'
  | 'latest_report_date';
type SortDir = 'asc' | 'desc';

type MainTab = 'pool' | 'portrait';

export function ShareholderStrategyLayout() {
  const [poolRes, setPoolRes] = useState<AntiQuantPoolResponse | null>(null);
  const [poolLoading, setPoolLoading] = useState(true);
  const [poolFetchError, setPoolFetchError] = useState<string | null>(null);
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
  const [tableSort, setTableSort] = useState<{ key: SortKey; dir: SortDir }>({ key: 'chip_score', dir: 'desc' });
  const [compareModalOpen, setCompareModalOpen] = useState(false);
  const [backtestStock, setBacktestStock] = useState<Holding | null>(null);
  const [highlightStock, setHighlightStock] = useState<string | null>(null);
  const [mainTab, setMainTab] = useState<MainTab>('pool');
  const [searchHint, setSearchHint] = useState<string | null>(null);
  const [klineStock, setKlineStock] = useState<{ code: string; name: string } | null>(null);
  const [coShareholders, setCoShareholders] = useState<CoShareholderItem[]>([]);
  const searchDebounceRef = useRef<ReturnType<typeof setTimeout>>();
  const immediateSubmitRef = useRef(false);

  const timeQuarter = selectedShareholder ? viewQuarter : endQuarter;

  const runSearch = useCallback((q: string) => {
    const t = q.trim();
    if (!t) { setSearchResults([]); setError(null); setSearchHint(null); return; }
    setSearchLoading(true); setError(null);
    api.shareholderByName(t, 20)
      .then((r) => {
        setSearchResults(r.ok && r.data ? r.data : []);
        setSearchHint(r.ok && r.hint ? r.hint : null);
      })
      .catch((e) => {
        setError(`搜索失败：${e?.message || '请确认 Gateway 已启动'}`);
        setSearchHint(null);
      })
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
    if (!q || q.length < 1) { setSearchResults([]); setError(null); setSearchHint(null); return; }
    setSearchLoading(true);
    searchDebounceRef.current = setTimeout(() => runSearch(q), 300);
    return () => { if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current); };
  }, [searchQuery, runSearch]);

  const handleSelectShareholder = useCallback((name: string) => {
    setStrategyLoading(true); setError(null); setSearchHint(null);
    api.shareholderStrategy(name, 10)
      .then((res) => {
        if (!res.ok) {
          setError(res.error || '加载失败');
          setSelectedShareholder(null); setHoldings([]); setChanges([]); setCoShareholders([]);
          return;
        }
        setMainTab('portrait');
        const info = res.info;
        setSelectedShareholder(info ? {
          id: info.name, name: info.name,
          identity: (info.identity as Shareholder['identity']) || '私募',
          tags: info.tags || [], stats: info.stats,
        } : { id: name, name, identity: '私募', tags: [], stats: { totalMarketCap: 0, stockCount: res.holdings?.length || 0, avgHoldPeriod: 0, winRate: 0 } });
        setHoldings(res.holdings || []);
        setChanges(res.changes || []);
        setCoShareholders(res.co_shareholders ?? []);
        if (res.latest_quarter) { setEndQuarter(res.latest_quarter); setViewQuarter(res.latest_quarter); }
      })
      .catch((e) => {
        setError(e?.message || '网络错误');
        setSelectedShareholder(null); setHoldings([]); setChanges([]); setCoShareholders([]);
      })
      .finally(() => setStrategyLoading(false));
  }, []);

  useEffect(() => {
    setPoolLoading(true);
    setPoolFetchError(null);
    api
      .antiQuantPool(100, 50)
      .then((r) => {
        if (r.ok) setPoolRes(r as AntiQuantPoolResponse);
        else setPoolFetchError(r.error || '反量化池接口返回异常');
      })
      .catch((e) => setPoolFetchError(e?.message || '反量化池请求失败'))
      .finally(() => setPoolLoading(false));
  }, []);

  const handleApplyQuarterToPortrait = useCallback(() => {
    if (!selectedShareholder) {
      setError('请先选择股东：报告期仅作用于左侧「持仓 / 流水」视图，不会筛全市场候选池。');
      return;
    }
    setError(null);
    setViewQuarter(endQuarter);
  }, [selectedShareholder, endQuarter]);

  const summary = poolRes?.summary ?? {};
  const poolData = poolRes?.data ?? [];
  const poolStatusLine = poolLoading
    ? '正在加载全市场筹码候选池…'
    : poolFetchError
      ? `筹码池：${poolFetchError}`
      : poolRes?.ok && poolData.length === 0
        ? '筹码池已返回 0 条（请检查 DuckDB top_10_shareholders 与 Gateway /financial/anti-quant-pool）'
        : poolRes?.ok
          ? `筹码池已加载 · 候选 ${poolData.length} 条${poolRes.note ? ` · ${poolRes.note}` : ''}`
          : '筹码池状态未知';
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
      case 'chip_score':
        va = a.chip_score ?? -1;
        vb = b.chip_score ?? -1;
        break;
      case 'hhi_top10':
        va = a.hhi_top10 ?? -1;
        vb = b.hhi_top10 ?? -1;
        break;
      case 'top10_delta_pp':
        va = a.top10_delta_pp ?? -999;
        vb = b.top10_delta_pp ?? -999;
        break;
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
            <div
              className="flex flex-wrap gap-2 rounded-2xl p-1.5"
              style={{ backgroundColor: '#14171C', border: '1px solid #2A2E36' }}
              role="tablist"
              aria-label="股东策略"
            >
              {(['pool', 'portrait'] as const).map((tab) => (
                <button
                  key={tab}
                  type="button"
                  role="tab"
                  aria-selected={mainTab === tab}
                  onClick={() => setMainTab(tab)}
                  className="min-w-[104px] flex-1 rounded-xl px-4 py-2.5 text-sm font-medium transition sm:flex-initial"
                  style={{
                    backgroundColor: mainTab === tab ? '#FF3B30' : 'transparent',
                    color: mainTab === tab ? '#FFF' : '#94A3B8',
                  }}
                >
                  {tab === 'pool' ? '筹码池' : '股东画像'}
                </button>
              ))}
            </div>

            {error && (
              <div className="rounded-xl px-4 py-2 text-sm" style={{ backgroundColor: 'rgba(255,59,48,0.1)', border: '1px solid rgba(255,59,48,0.3)', color: '#FF3B30' }}>
                {error}
              </div>
            )}

            {mainTab === 'pool' && (
              <>
                <div
                  className="rounded-2xl px-4 py-3 text-xs leading-relaxed"
                  style={{ backgroundColor: '#14171C', border: '1px solid #2A2E36', color: '#64748B' }}
                >
                  全市场反量化筹码候选（<code className="text-[11px]" style={{ color: '#94A3B8' }}>/financial/anti-quant-pool</code>
                  ）。个股详情点击表格行；股东持仓与<strong style={{ color: '#94A3B8' }}>行业分布雷达</strong>在「股东画像」。
                </div>
                <div className="text-xs" style={{ color: '#64748B' }}>
                  {poolStatusLine}
                </div>

                <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
                  <KPICard title="分析股票数" value={summary.total_stocks_analyzed ?? 0} />
                  <KPICard title="候选股数" value={summary.candidate_count ?? 0} />
                  <KPICard title="平均持股集中度" value={`${summary.avg_top10_ratio ?? '—'}%`} />
                  <KPICard title="平均机构数" value={summary.avg_institution_count ?? '—'} />
                  <KPICard title="平均筹码得分" value={summary.avg_chip_score ?? '—'} />
                </div>
                <p className="text-xs" style={{ color: '#475569' }}>
                  上列为筹码池接口 summary，不含环比/走势图。
                </p>

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
                              <th className="cursor-pointer px-4 py-3 text-left" onClick={() => handleSort('chip_score')}>筹码分</th>
                              <th className="cursor-pointer px-4 py-3 text-left" onClick={() => handleSort('hhi_top10')}>HHI</th>
                              <th className="cursor-pointer px-4 py-3 text-left" onClick={() => handleSort('top10_delta_pp')}>前十Δ%</th>
                              <th className="cursor-pointer px-4 py-3 text-left" onClick={() => handleSort('top10_ratio')}>持股集中度</th>
                              <th className="cursor-pointer px-4 py-3 text-left" onClick={() => handleSort('institution_count_current')}>机构数</th>
                              <th className="cursor-pointer px-4 py-3 text-left" onClick={() => handleSort('turnover_avg')}>换主频率</th>
                              <th className="px-4 py-3 text-left">机构纯度</th>
                              <th className="cursor-pointer px-4 py-3 text-left" onClick={() => handleSort('latest_report_date')}>报告期</th>
                            </tr>
                          </thead>
                          <tbody>
                            {poolLoading && (
                              <tr>
                                <td colSpan={9} className="px-4 py-12 text-center" style={{ color: '#64748B' }}>
                                  加载候选列表…
                                </td>
                              </tr>
                            )}
                            {!poolLoading &&
                              sortedPool.length === 0 &&
                              (poolFetchError ? (
                                <tr>
                                  <td colSpan={9} className="px-4 py-8 text-center text-sm" style={{ color: '#FF3B30' }}>
                                    无法加载候选池：{poolFetchError}
                                  </td>
                                </tr>
                              ) : (
                                <tr>
                                  <td colSpan={9} className="px-4 py-8 text-center text-sm" style={{ color: '#64748B' }}>
                                    暂无候选数据（接口已成功但列表为空）。
                                  </td>
                                </tr>
                              ))}
                            {!poolLoading &&
                              sortedPool.slice(0, 30).map((row) => (
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
                                  <td className="px-4 py-3 font-medium" style={{ color: '#22D3EE' }}>{row.chip_score != null ? row.chip_score : '—'}</td>
                                  <td className="px-4 py-3" style={{ color: '#94A3B8' }}>{row.hhi_top10 != null ? row.hhi_top10 : '—'}</td>
                                  <td className="px-4 py-3" style={{ color: '#94A3B8' }}>
                                    {row.top10_delta_pp != null ? (row.top10_delta_pp > 0 ? `+${row.top10_delta_pp}` : row.top10_delta_pp) : '—'}
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
                    </div>
                  </div>

                  <div className="xl:col-span-5">
                    <div
                      className="rounded-2xl overflow-hidden"
                      style={{ backgroundColor: '#14171C', border: '1px solid #2A2E36', boxShadow: '0 2px 8px rgba(0,0,0,0.2)' }}
                    >
                      <div className="border-b px-4 py-3" style={{ borderColor: '#2A2E36' }}>
                        <h3 className="font-semibold" style={{ color: '#F1F5F9' }}>筹码稳定性热力图</h3>
                        <p className="mt-1 text-xs" style={{ color: '#64748B' }}>基于当前候选池前 10 只</p>
                      </div>
                      <div className="p-4">
                        <ConcentrationHeatmap stocks={sortedPool.slice(0, 10)} quarters={QUARTERS.slice(-8)} height={180} />
                      </div>
                    </div>
                  </div>
                </div>
              </>
            )}

            {mainTab === 'portrait' && (
              <>
                <div
                  className="rounded-2xl p-6 transition hover:shadow-lg"
                  style={{ backgroundColor: '#14171C', border: '1px solid #2A2E36', boxShadow: '0 2px 8px rgba(0,0,0,0.2)' }}
                >
                  <div className="mb-4 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                    <ShareholderHeader
                      searchResults={searchResults}
                      searchLoading={searchLoading}
                      selected={selectedShareholder}
                      searchHint={searchHint}
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
                        onClick={handleApplyQuarterToPortrait}
                        className="rounded-lg px-4 py-2 text-sm font-medium transition hover:opacity-90"
                        style={{ backgroundColor: '#FF3B30', color: '#FFF' }}
                      >
                        应用至画像
                      </button>
                    </div>
                    <div className="max-w-md text-right text-xs leading-relaxed md:max-w-lg" style={{ color: '#64748B' }}>
                      {poolStatusLine}
                    </div>
                  </div>
                  <p className="mt-2 text-xs" style={{ color: '#475569' }}>
                    报告期用于持仓/流水/行业雷达时间切片；「应用至画像」将视图季设为当前结束季。行业雷达数据来自持仓明细中的行业字段与
                    <code className="text-[11px]" style={{ color: '#64748B' }}> getIndustryRadarData</code>。
                  </p>
                </div>

                {strategyLoading && (
                  <div className="rounded-xl px-4 py-3 text-sm" style={{ backgroundColor: '#14171C', border: '1px solid #2A2E36', color: '#94A3B8' }}>
                    正在加载股东策略数据…
                  </div>
                )}

                {!selectedShareholder && !strategyLoading && (
                  <div
                    className="rounded-2xl px-6 py-14 text-center text-sm"
                    style={{ backgroundColor: '#14171C', border: '1px solid #2A2E36', color: '#94A3B8' }}
                  >
                    在上方搜索并选择股东后，可查看持仓、变动流水、<strong style={{ color: '#F1F5F9' }}>行业分布雷达</strong>与市值-估值气泡图。
                  </div>
                )}

                {selectedShareholder && !strategyLoading && (
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
                        changes={changes}
                        coShareholders={coShareholders}
                        timeQuarter={timeQuarter}
                        highlightStock={highlightStock}
                        onStockHover={setHighlightStock}
                        onPanoramaStockClick={(h) =>
                          setKlineStock({ code: h.stockCode, name: h.stockName })
                        }
                        onCoShareholderClick={handleSelectShareholder}
                      />
                    </div>
                  </div>
                )}
              </>
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

      {klineStock && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center p-4"
          style={{ backgroundColor: 'rgba(0,0,0,0.75)' }}
          onClick={() => setKlineStock(null)}
          role="presentation"
        >
          <div
            className="max-h-[92vh] w-full max-w-4xl overflow-y-auto rounded-2xl p-4 md:p-6"
            style={{ backgroundColor: '#14171C', border: '1px solid #2A2E36', boxShadow: '0 8px 40px rgba(0,0,0,0.5)' }}
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal
            aria-label="股票 K 线"
          >
            <StockPenetrationPanel
              row={{ code: klineStock.code, stock_name: klineStock.name }}
              onBack={() => setKlineStock(null)}
            />
          </div>
        </div>
      )}
    </div>
  );
}
