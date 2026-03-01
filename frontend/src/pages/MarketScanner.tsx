import { useState, useEffect, useCallback, useMemo } from 'react';
import { Card, Tabs, Table, Tag, Spin, Button, Space, Dropdown, Alert, Drawer, Descriptions, Select } from 'antd';
import { DownloadOutlined, DownOutlined, FilterOutlined } from '@ant-design/icons';
import type { MenuProps } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { api } from '../api/client';
import type { ScanItem, KlineBar, MaPoint } from '../types';
import TradingChart from '../components/TradingChart';

function fmtWanYi(val: number | null | undefined): string {
  if (val == null || Number.isNaN(val)) return '—';
  const yi = val / 1e8;
  if (yi >= 10000) return (yi / 10000).toFixed(2) + '万亿';
  if (yi >= 1) return yi.toFixed(2) + '亿';
  return (val / 1e4).toFixed(2) + '万';
}

type SortOrder = 'ascend' | 'descend' | null;

function buildColumns(sortField: string | undefined, sortOrder: SortOrder): ColumnsType<ScanItem> {
  const num = (a: number | null | undefined, b: number | null | undefined) => {
    const va = a ?? -Infinity;
    const vb = b ?? -Infinity;
    return va - vb;
  };
  const str = (a: string | null | undefined, b: string | null | undefined) =>
    (a ?? '').localeCompare(b ?? '', 'zh-CN');
  const sortTooltip = { title: '点击排序' as const };
  return [
    { title: '标的', dataIndex: 'symbol', key: 'symbol', width: 90, sorter: (a, b) => str(a.symbol, b.symbol), sortOrder: sortField === 'symbol' ? sortOrder : null, showSorterTooltip: sortTooltip },
    { title: '名称', dataIndex: 'name', key: 'name', ellipsis: true, width: 100, sorter: (a, b) => str(a.name, b.name), sortOrder: sortField === 'name' ? sortOrder : null, showSorterTooltip: sortTooltip },
    { title: '信号', dataIndex: 'signal', key: 'signal', width: 72, render: (v: string) => v && <Tag color={v === 'BUY' ? 'green' : 'red'}>{v}</Tag>, sorter: (a, b) => str(a.signal, b.signal), sortOrder: sortField === 'signal' ? sortOrder : null, showSorterTooltip: sortTooltip },
    { title: '价格', dataIndex: 'price', key: 'price', width: 72, render: (v: number) => v != null ? v.toFixed(2) : '—', sorter: (a, b) => num(a.price, b.price), sortOrder: sortField === 'price' ? sortOrder : null, showSorterTooltip: sortTooltip },
    { title: '买点概率', dataIndex: 'buy_prob', key: 'buy_prob', width: 88, render: (v: number) => v != null ? v + '%' : '—', sorter: (a, b) => num(a.buy_prob ?? null, b.buy_prob ?? null), sortOrder: sortField === 'buy_prob' ? sortOrder : null, showSorterTooltip: sortTooltip },
    { title: '去年营收', dataIndex: 'revenue_ly', key: 'revenue_ly', width: 96, render: (v: number | null | undefined) => fmtWanYi(v), sorter: (a, b) => num(a.revenue_ly, b.revenue_ly), sortOrder: sortField === 'revenue_ly' ? sortOrder : null, showSorterTooltip: sortTooltip },
    { title: '去年净利润', dataIndex: 'profit_ly', key: 'profit_ly', width: 96, render: (v: number | null | undefined) => fmtWanYi(v), sorter: (a, b) => num(a.profit_ly, b.profit_ly), sortOrder: sortField === 'profit_ly' ? sortOrder : null, showSorterTooltip: sortTooltip },
    { title: '市盈率', dataIndex: 'pe_ratio', key: 'pe_ratio', width: 72, render: (v: number | null | undefined) => v != null ? v.toFixed(1) : '—', sorter: (a, b) => num(a.pe_ratio, b.pe_ratio), sortOrder: sortField === 'pe_ratio' ? sortOrder : null, showSorterTooltip: sortTooltip },
    { title: '市净率', dataIndex: 'pb_ratio', key: 'pb_ratio', width: 72, render: (v: number | null | undefined) => v != null ? v.toFixed(2) : '—', sorter: (a, b) => num(a.pb_ratio, b.pb_ratio), sortOrder: sortField === 'pb_ratio' ? sortOrder : null, showSorterTooltip: sortTooltip },
    { title: '行业', dataIndex: 'industry', key: 'industry', width: 90, ellipsis: true, render: (v: string | null | undefined) => v || '—', sorter: (a, b) => str(a.industry, b.industry), sortOrder: sortField === 'industry' ? sortOrder : null, showSorterTooltip: sortTooltip },
    { title: '区域', dataIndex: 'region', key: 'region', width: 64, render: (v: string | null | undefined) => v || '—', sorter: (a, b) => str(a.region, b.region), sortOrder: sortField === 'region' ? sortOrder : null, showSorterTooltip: sortTooltip },
    { title: '说明', dataIndex: 'reason', key: 'reason', ellipsis: true, sorter: (a, b) => str(a.reason, b.reason), sortOrder: sortField === 'reason' ? sortOrder : null, showSorterTooltip: sortTooltip },
  ];
}

type TabKey = 'breakout' | 'strong' | 'ai' | 'multi_agent';

// 多智能体扫描结果类型
type ThemeData = {
  name: string;
  stage?: string;
  tier?: string;
  confidence?: number;
};

type MultiAgentPick = {
  symbol: string;
  name?: string;
  theme?: string;
  strategy?: string;
  strategy_cn?: string;
  current_price?: number;
  rsi?: number;
  risk_level?: string;
  logic?: string;
  stop_loss?: string;
  observe?: string;
  ma20?: number;
  ma60?: number;
  trend?: string;
  revenue_ly?: number | null;
  profit_ly?: number | null;
  pe_ratio?: number | null;
  pb_ratio?: number | null;
  industry?: string | null;
  region?: string | null;
};

type ExecutionLog = {
  step: string;
  status: string;
  message?: string;
};

export default function MarketScanner() {
  const [activeTab, setActiveTab] = useState<TabKey>('breakout');
  const [breakout, setBreakout] = useState<ScanItem[]>([]);
  const [strong, setStrong] = useState<ScanItem[]>([]);
  const [aiRec, setAiRec] = useState<ScanItem[]>([]);
  // 多智能体扫描状态
  const [multiAgentPicks, setMultiAgentPicks] = useState<MultiAgentPick[]>([]);
  const [multiAgentThemes, setMultiAgentThemes] = useState<ThemeData[]>([]);
  const [multiAgentReport, setMultiAgentReport] = useState<string>('');
  const [multiAgentLogs, setMultiAgentLogs] = useState<ExecutionLog[]>([]);
  const [loadingMultiAgent, setLoadingMultiAgent] = useState(false);
  const [loadedMultiAgent, setLoadedMultiAgent] = useState(false);
  const [multiAgentError, setMultiAgentError] = useState<string | undefined>(undefined);
  // 多智能体参数控制
  const [maDaysLookback, setMaDaysLookback] = useState<number>(3);
  const [maTopNThemes, setMaTopNThemes] = useState<number>(10);
  const [maTopNStocks, setMaTopNStocks] = useState<number>(20);
  const [maUseLlm, setMaUseLlm] = useState<boolean>(false);
  const [maRelaxedFilter, setMaRelaxedFilter] = useState<boolean>(false);
  const [maStats, setMaStats] = useState<{candidates_count: number; filtered_count: number; theme_stock_count: number}>({candidates_count: 0, filtered_count: 0, theme_stock_count: 0});
  const [loadingBreakout, setLoadingBreakout] = useState(false);
  const [loadingStrong, setLoadingStrong] = useState(false);
  const [loadingAi, setLoadingAi] = useState(false);
  const [loadedBreakout, setLoadedBreakout] = useState(false);
  const [loadedStrong, setLoadedStrong] = useState(false);
  const [loadedAi, setLoadedAi] = useState(false);
  const [aiError, setAiError] = useState<string | undefined>(undefined);
  const [sortField, setSortField] = useState<string | undefined>(undefined);
  const [sortOrder, setSortOrder] = useState<SortOrder>(null);
  const [industryFilter, setIndustryFilter] = useState<string | undefined>(undefined);
  const [selectedRow, setSelectedRow] = useState<ScanItem | null>(null);
  const [detailKline, setDetailKline] = useState<KlineBar[]>([]);
  const [detailMa5, setDetailMa5] = useState<MaPoint[]>([]);
  const [detailMa10, setDetailMa10] = useState<MaPoint[]>([]);
  const [detailMa20, setDetailMa20] = useState<MaPoint[]>([]);
  const [detailSignals, setDetailSignals] = useState<{ date: string; type: 'BUY' | 'SELL'; price: number }[]>([]);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const loadMode = useCallback(async (mode: TabKey, forceRefresh = false) => {
    if (mode === 'breakout') {
      if (loadedBreakout && !forceRefresh) return;
      setLoadingBreakout(true);
      try {
        const r = await api.scan('breakout').catch(() => ({ results: [] }));
        setBreakout((r as { results: ScanItem[] }).results || []);
        setLoadedBreakout(true);
      } finally {
        setLoadingBreakout(false);
      }
    } else if (mode === 'strong') {
      if (loadedStrong && !forceRefresh) return;
      setLoadingStrong(true);
      try {
        const r = await api.scan('strong').catch(() => ({ results: [] }));
        setStrong((r as { results: ScanItem[] }).results || []);
        setLoadedStrong(true);
      } finally {
        setLoadingStrong(false);
      }
    } else if (mode === 'ai') {
      if (loadedAi && !forceRefresh) return;
      setLoadingAi(true);
      setAiError(undefined);
      try {
        const r = await api.scan('ai').catch((err: Error) => ({ results: [] as ScanItem[], error: err?.message || '请求失败' }));
        const body = r as { results?: ScanItem[]; error?: string };
        setAiRec(body.results || []);
        if (body.error) setAiError(body.error);
        setLoadedAi(true);
      } finally {
        setLoadingAi(false);
      }
    } else if (mode === 'multi_agent') {
      if (loadedMultiAgent && !forceRefresh) return;
      setLoadingMultiAgent(true);
      setMultiAgentError(undefined);
      try {
        // 调用多智能体扫描API
        const response = await fetch('/api/scan/multi_agent', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            days_lookback: maDaysLookback,
            top_n_themes: maTopNThemes,
            top_n_stocks: maTopNStocks,
            use_llm: maUseLlm,
            relaxed_filter: maRelaxedFilter,
          }),
        });
        const data = await response.json();
        if (data.success) {
          setMultiAgentPicks(data.picks || []);
          setMultiAgentThemes(data.themes || []);
          setMultiAgentReport(data.report || '');
          setMultiAgentLogs(data.execution_log || []);
          setMaStats(data.stats || {candidates_count: 0, filtered_count: 0, theme_stock_count: 0});
        } else {
          setMultiAgentError(data.error || '扫描失败');
        }
        setLoadedMultiAgent(true);
      } catch (err) {
        setMultiAgentError(err instanceof Error ? err.message : '请求失败');
        setLoadedMultiAgent(true);
      } finally {
        setLoadingMultiAgent(false);
      }
    }
  }, [loadedBreakout, loadedStrong, loadedAi, loadedMultiAgent, maDaysLookback, maTopNThemes, maTopNStocks, maUseLlm, maRelaxedFilter]);

  // 进入页面只拉当前 Tab；切换 Tab 时仅在该 Tab 未加载过时拉取
  useEffect(() => {
    loadMode(activeTab);
  }, [activeTab, loadMode]);

  const onTabChange = (key: string) => {
    setActiveTab(key as TabKey);
    setIndustryFilter(undefined);
  };

  const handleRefresh = () => {
    loadMode(activeTab, true);
  };

  const currentData = activeTab === 'breakout' ? breakout : activeTab === 'strong' ? strong : activeTab === 'ai' ? aiRec : [];
  
  // 多智能体选股结果转ScanItem格式用于详情展示（补齐名称与财务信息）
  const multiAgentToScanItem = (pick: MultiAgentPick): ScanItem => ({
    symbol: pick.symbol,
    name: (pick.name && pick.name !== pick.symbol ? pick.name : undefined) || pick.symbol,
    signal: 'BUY',
    price: pick.current_price ?? 0,
    buy_prob: undefined,
    industry: pick.industry ?? pick.theme ?? '',
    reason: `${pick.strategy_cn || pick.strategy || ''}: ${pick.logic || ''}`,
    revenue_ly: pick.revenue_ly ?? undefined,
    profit_ly: pick.profit_ly ?? undefined,
    pe_ratio: pick.pe_ratio ?? undefined,
    pb_ratio: pick.pb_ratio ?? undefined,
    region: pick.region ?? undefined,
  });

  const industryOptions = useMemo(() => {
    const set = new Set<string>();
    currentData.forEach((r) => {
      const ind = r.industry?.trim();
      if (ind) set.add(ind);
    });
    return Array.from(set).sort((a, b) => a.localeCompare(b, 'zh-CN'));
  }, [currentData]);

  const industryFilterKeyword = useMemo(() => {
    if (!industryFilter?.trim()) return '';
    const s = industryFilter.trim();
    const keyword = s.replace(/(Ⅱ|Ⅲ|Ⅳ|开发|服务|行业|板块|制造|设备)$/, '').trim() || s;
    return keyword;
  }, [industryFilter]);

  const filteredByIndustry = useMemo(() => {
    if (!industryFilterKeyword) return currentData;
    return currentData.filter((r) => (r.industry ?? '').includes(industryFilterKeyword));
  }, [currentData, industryFilterKeyword]);

  const sortedData = useMemo(() => {
    const src = filteredByIndustry;
    if (!sortField || !sortOrder) return src;
    const key = sortField as keyof ScanItem;
    const cmp = sortOrder === 'ascend' ? 1 : -1;
    return [...src].sort((a, b) => {
      const va = a[key];
      const vb = b[key];
      if (typeof va === 'number' && typeof vb === 'number') return cmp * (va - vb);
      return cmp * String(va ?? '').localeCompare(String(vb ?? ''), 'zh-CN');
    });
  }, [filteredByIndustry, sortField, sortOrder]);

  useEffect(() => {
    if (!selectedRow?.symbol) {
      setDetailKline([]);
      setDetailMa5([]);
      setDetailMa10([]);
      setDetailMa20([]);
      setDetailSignals([]);
      return;
    }
    setLoadingDetail(true);
    const end = new Date();
    const start = new Date(end);
    start.setDate(start.getDate() - 120);
    const startStr = start.toISOString().slice(0, 10);
    const endStr = end.toISOString().slice(0, 10);
    Promise.all([
      api.kline(selectedRow.symbol, startStr, endStr, { indicators: 'ma' }),
      api.signals(selectedRow.symbol).catch(() => ({ signals: [] })),
    ])
      .then(([kline, sigRes]) => {
        if (Array.isArray(kline)) {
          setDetailKline(kline);
          setDetailMa5([]);
          setDetailMa10([]);
          setDetailMa20([]);
        } else {
          const r = kline as { kline: KlineBar[]; ma5?: MaPoint[]; ma10?: MaPoint[]; ma20?: MaPoint[] };
          setDetailKline(r.kline || []);
          setDetailMa5(r.ma5 || []);
          setDetailMa10(r.ma10 || []);
          setDetailMa20(r.ma20 || []);
        }
        const sigs = (sigRes as { signals?: { date: string; type: 'BUY' | 'SELL'; price: number }[] }).signals ?? [];
        setDetailSignals(sigs.map((s) => ({ date: s.date, type: s.type, price: s.price })));
      })
      .catch(() => {
        setDetailKline([]);
        setDetailMa5([]);
        setDetailMa10([]);
        setDetailMa20([]);
        setDetailSignals([]);
      })
      .finally(() => setLoadingDetail(false));
  }, [selectedRow?.symbol]);

  const tabLabel = activeTab === 'breakout' ? '突破股票' : activeTab === 'strong' ? '强势股' : activeTab === 'ai' ? 'AI推荐' : '智能扫描';
  const columns = useMemo(() => buildColumns(sortField, sortOrder), [sortField, sortOrder]);

  const onTableChange = (_: unknown, __: unknown, sorter: unknown) => {
    const raw = Array.isArray(sorter) ? (sorter as { field?: string; columnKey?: string; order?: SortOrder }[])[0] : (sorter as { field?: string; columnKey?: string; order?: SortOrder });
    const field = raw?.field ?? raw?.columnKey;
    const order = raw?.order ?? null;
    if (field != null && order != null) {
      setSortField(String(field));
      setSortOrder(order);
    } else {
      setSortField(undefined);
      setSortOrder(null);
    }
  };

  const dataToExport = industryFilter ? filteredByIndustry : currentData;

  const exportCSV = () => {
    if (dataToExport.length === 0) return;
    const headers = ['标的', '名称', '信号', '价格', '买点概率', '去年营收', '去年净利润', '市盈率', '市净率', '行业', '区域', '说明'];
    const escape = (v: unknown) => {
      const s = v == null ? '' : String(v);
      return /[,"\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    };
    const rows = dataToExport.map((r) =>
      [r.symbol, r.name ?? '', r.signal ?? '', r.price ?? '', r.buy_prob ?? '', r.revenue_ly ?? '', r.profit_ly ?? '', r.pe_ratio ?? '', r.pb_ratio ?? '', r.industry ?? '', r.region ?? '', r.reason ?? ''].map(escape).join(',')
    );
    const bom = '\uFEFF';
    const csv = bom + headers.join(',') + '\r\n' + rows.join('\r\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${tabLabel}_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportJSON = () => {
    if (dataToExport.length === 0) return;
    const blob = new Blob([JSON.stringify(dataToExport, null, 2)], { type: 'application/json;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${tabLabel}_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportExcel = () => {
    if (currentData.length === 0) return;
    import('xlsx').then((XLSX) => {
      const rows = dataToExport.map((r) => ({
        '标的': r.symbol ?? '',
        '名称': r.name ?? '',
        '信号': r.signal ?? '',
        '价格': r.price != null ? r.price : '',
        '买点概率': r.buy_prob != null ? r.buy_prob : '',
        '去年营收': r.revenue_ly != null ? fmtWanYi(r.revenue_ly) : '—',
        '去年净利润': r.profit_ly != null ? fmtWanYi(r.profit_ly) : '—',
        '市盈率': r.pe_ratio != null ? r.pe_ratio : '',
        '市净率': r.pb_ratio != null ? r.pb_ratio : '',
        '行业': r.industry ?? '',
        '区域': r.region ?? '',
        '说明': r.reason ?? '',
      }));
      const ws = XLSX.utils.json_to_sheet(rows);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, tabLabel.slice(0, 31));
      XLSX.writeFile(wb, `${tabLabel}_${new Date().toISOString().slice(0, 10)}.xlsx`);
    }).catch(() => {});
  };

  const exportPDF = () => {
    if (dataToExport.length === 0) return;
    Promise.all([import('jspdf'), import('jspdf-autotable')]).then(([jsPDFModule]) => {
      const { default: jsPDF } = jsPDFModule;
      const doc = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' });
      doc.setFontSize(14);
      doc.text(`市场扫描器 - ${tabLabel}`, 14, 12);
      const headers = [['标的', '名称', '信号', '价格', '买点概率', '去年营收', '去年净利润', '市盈率', '市净率', '行业', '区域', '说明']];
      const body = dataToExport.map((r) => [
        r.symbol ?? '',
        r.name ?? '',
        r.signal ?? '',
        r.price != null ? String(r.price) : '',
        r.buy_prob != null ? String(r.buy_prob) : '',
        r.revenue_ly != null ? fmtWanYi(r.revenue_ly) : '—',
        r.profit_ly != null ? fmtWanYi(r.profit_ly) : '—',
        r.pe_ratio != null ? String(r.pe_ratio) : '—',
        r.pb_ratio != null ? String(r.pb_ratio) : '—',
        (r.industry ?? '').slice(0, 12),
        r.region ?? '—',
        (r.reason ?? '').slice(0, 20),
      ]);
      (doc as unknown as { autoTable: (opts: Record<string, unknown>) => void }).autoTable({
        head: headers,
        body,
        startY: 18,
        styles: { fontSize: 8 },
        margin: { left: 14 },
      });
      doc.save(`${tabLabel}_${new Date().toISOString().slice(0, 10)}.pdf`);
    }).catch(() => {});
  };

  const exportMenuItems: MenuProps['items'] = [
    { key: 'csv', label: '导出 CSV', onClick: exportCSV, disabled: dataToExport.length === 0 },
    { key: 'json', label: '导出 JSON', onClick: exportJSON, disabled: dataToExport.length === 0 },
    { key: 'excel', label: '导出 Excel', onClick: exportExcel, disabled: dataToExport.length === 0 },
    { key: 'pdf', label: '导出 PDF', onClick: exportPDF, disabled: dataToExport.length === 0 },
  ];

  const hasNoFinancials = currentData.length > 0 && currentData.every((r) => r.revenue_ly == null && r.profit_ly == null);

  return (
    <div style={{ padding: 8, color: '#f1f5f9' }}>
      <Card
        title={<span style={{ color: '#f1f5f9', fontWeight: 600 }}>市场扫描器</span>}
        style={{ background: '#1a2332', marginBottom: 16, border: '1px solid #2d3a4f' }}
        extra={
          <Space wrap>
            <Button type="primary" size="small" onClick={handleRefresh}>刷新</Button>
            <Dropdown menu={{ items: exportMenuItems }} placement="bottomRight">
              <Button size="small" icon={<DownloadOutlined />} disabled={currentData.length === 0}>
                导出 <DownOutlined />
              </Button>
            </Dropdown>
          </Space>
        }
      >
        {hasNoFinancials && (
          <Alert
            type="info"
            showIcon
            message={<span style={{ color: '#e2e8f0', fontWeight: 600 }}>去年营收、去年净利润</span>}
            description={
              <span style={{ color: '#cbd5e1', lineHeight: 1.5 }}>
                运行 <code style={{ background: '#334155', padding: '2px 6px', borderRadius: 4, color: '#f1f5f9' }}>python scripts/update_financials_cache.py</code> 可生成财务缓存（含市盈率、市净率、行业、区域），加 <code style={{ background: '#334155', padding: '2px 6px', borderRadius: 4, color: '#f1f5f9' }}>--region-limit 500</code> 可拉取区域信息（需 akshare）。
              </span>
            }
            style={{
              marginBottom: 12,
              background: '#1e293b',
              border: '1px solid #334155',
              color: '#e2e8f0',
            }}
          />
        )}
        <Tabs
          activeKey={activeTab}
          onChange={onTabChange}
          items={[
            {
              key: 'breakout',
              label: '突破股票',
              children: (
                loadingBreakout ? <Spin tip="加载中…" /> : (
                  breakout.length === 0 ? <div style={{ color: '#94a3b8', textAlign: 'center', padding: 24 }}>暂无突破股票，点击刷新可重新拉取</div> : (
                    <>
                      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                        <span style={{ color: '#64748b', fontSize: 12 }}>点击表头排序 · 点击行查看详情与 K 线</span>
                        <Select
                          placeholder="按行业筛选（选某类则显示包含该关键词）"
                          allowClear
                          value={industryFilter ?? ''}
                          onChange={(v) => setIndustryFilter(v && v !== '' ? v : undefined)}
                          options={[
                            { value: '', label: '全部行业' },
                            ...industryOptions.map((ind) => ({ value: ind, label: ind })),
                          ]}
                          style={{ width: 200, minWidth: 180 }}
                          suffixIcon={<FilterOutlined />}
                          dropdownStyle={{ background: '#1a2332' }}
                        />
                        {industryFilter && (
                          <span style={{ color: '#94a3b8', fontSize: 12 }}>
                            已筛选包含「{industryFilterKeyword}」共 {filteredByIndustry.length} 只
                          </span>
                        )}
                      </div>
                      <Table
                        size="small"
                        dataSource={sortedData}
                        columns={columns}
                        rowKey="symbol"
                        pagination={{ pageSize: 15 }}
                        onChange={onTableChange}
                        onRow={(record) => ({
                          onClick: () => setSelectedRow(record),
                          style: { cursor: 'pointer' },
                          onMouseEnter: (e) => { (e.currentTarget as HTMLElement).style.background = 'rgba(45,58,79,0.6)'; },
                          onMouseLeave: (e) => { (e.currentTarget as HTMLElement).style.background = ''; },
                        })}
                        style={{ color: '#f1f5f9' }}
                      />
                    </>
                  )
                )
              ),
            },
            {
              key: 'strong',
              label: '强势股',
              children: (
                loadingStrong ? <Spin tip="加载中…" /> : (
                  strong.length === 0 ? <div style={{ color: '#94a3b8', textAlign: 'center', padding: 24 }}>暂无强势股，点击刷新可重新拉取</div> : (
                    <>
                      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                        <span style={{ color: '#64748b', fontSize: 12 }}>点击表头排序 · 点击行查看详情与 K 线</span>
                        <Select
                          placeholder="按行业筛选（选某类则显示包含该关键词）"
                          allowClear
                          value={industryFilter ?? ''}
                          onChange={(v) => setIndustryFilter(v && v !== '' ? v : undefined)}
                          options={[
                            { value: '', label: '全部行业' },
                            ...industryOptions.map((ind) => ({ value: ind, label: ind })),
                          ]}
                          style={{ width: 200, minWidth: 180 }}
                          suffixIcon={<FilterOutlined />}
                          dropdownStyle={{ background: '#1a2332' }}
                        />
                        {industryFilter && (
                          <span style={{ color: '#94a3b8', fontSize: 12 }}>
                            已筛选包含「{industryFilterKeyword}」共 {filteredByIndustry.length} 只
                          </span>
                        )}
                      </div>
                      <Table
                        size="small"
                        dataSource={sortedData}
                        columns={columns}
                        rowKey="symbol"
                        pagination={{ pageSize: 15 }}
                        onChange={onTableChange}
                        onRow={(record) => ({
                          onClick: () => setSelectedRow(record),
                          style: { cursor: 'pointer' },
                          onMouseEnter: (e) => { (e.currentTarget as HTMLElement).style.background = 'rgba(45,58,79,0.6)'; },
                          onMouseLeave: (e) => { (e.currentTarget as HTMLElement).style.background = ''; },
                        })}
                        style={{ color: '#f1f5f9' }}
                      />
                    </>
                  )
                )
              ),
            },
            {
              key: 'ai',
              label: 'AI 推荐',
              children: (
                loadingAi ? (
                  <div style={{ textAlign: 'center', padding: 48 }}>
                    <Spin size="large" tip="AI 推荐较慢，约 30 秒…" />
                  </div>
                ) : aiError && aiRec.length === 0 ? (
                  <Alert
                    type="warning"
                    showIcon
                    message="加载失败"
                    description={aiError + '。可先使用「突破股票」或「强势股」，或稍后重试。'}
                    style={{ margin: 16 }}
                  />
                ) : (
                  <>
                    {aiError && (
                      <Alert
                        type="info"
                        showIcon
                        message={<span style={{ color: '#e2e8f0' }}>已降级为组合信号</span>}
                        description={<span style={{ color: '#cbd5e1' }}>{aiError}</span>}
                        style={{ marginBottom: 12, background: '#1e293b', border: '1px solid #334155' }}
                      />
                    )}
                    {aiRec.length === 0 ? (
                  <div style={{ color: '#94a3b8', textAlign: 'center', padding: 24 }}>暂无 AI 推荐，点击刷新可重新拉取</div>
                ) : (
                      <>
                        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                          <span style={{ color: '#64748b', fontSize: 12 }}>点击表头排序 · 点击行查看详情与 K 线</span>
                          <Select
                            placeholder="按行业筛选（选某类则显示包含该关键词）"
                            allowClear
                            value={industryFilter ?? ''}
                            onChange={(v) => setIndustryFilter(v && v !== '' ? v : undefined)}
                            options={[
                              { value: '', label: '全部行业' },
                              ...industryOptions.map((ind) => ({ value: ind, label: ind })),
                            ]}
                            style={{ width: 200, minWidth: 180 }}
                            suffixIcon={<FilterOutlined />}
                            dropdownStyle={{ background: '#1a2332' }}
                          />
                          {industryFilter && (
                            <span style={{ color: '#94a3b8', fontSize: 12 }}>
                              已筛选包含「{industryFilterKeyword}」共 {filteredByIndustry.length} 只
                            </span>
                          )}
                        </div>
                        <Table
                          size="small"
                          dataSource={sortedData}
                          columns={columns}
                          rowKey="symbol"
                          pagination={{ pageSize: 15 }}
                          onChange={onTableChange}
                          onRow={(record) => ({
                            onClick: () => setSelectedRow(record),
                            style: { cursor: 'pointer' },
                            onMouseEnter: (e) => { (e.currentTarget as HTMLElement).style.background = 'rgba(45,58,79,0.6)'; },
                            onMouseLeave: (e) => { (e.currentTarget as HTMLElement).style.background = ''; },
                          })}
                          style={{ color: '#f1f5f9' }}
                        />
                      </>
                    )}
                  </>
                )
              ),
            },
            {
              key: 'multi_agent',
              label: '智能扫描',
              children: (
                <div style={{ color: '#f1f5f9' }}>
                  {/* 参数控制面板 */}
                  <Card
                    title={<span style={{ color: '#f1f5f9', fontWeight: 600 }}>扫描参数设置</span>}
                    style={{ background: '#0f172a', marginBottom: 16, border: '1px solid #1e293b' }}
                    headStyle={{ background: '#0f172a', borderBottom: '1px solid #1e293b' }}
                    extra={
                      <Space>
                        <Button 
                          type="primary" 
                          size="small" 
                          onClick={() => loadMode('multi_agent', true)}
                          loading={loadingMultiAgent}
                        >
                          开始扫描
                        </Button>
                      </Space>
                    }
                  >
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16 }}>
                      <div>
                        <div style={{ color: '#94a3b8', fontSize: 12, marginBottom: 4 }}>新闻回溯天数</div>
                        <Select
                          value={maDaysLookback}
                          onChange={setMaDaysLookback}
                          options={[
                            { value: 1, label: '1天' },
                            { value: 3, label: '3天' },
                            { value: 7, label: '7天' },
                            { value: 14, label: '14天' },
                          ]}
                          style={{ width: 100 }}
                          disabled={loadingMultiAgent}
                        />
                      </div>
                      <div>
                        <div style={{ color: '#94a3b8', fontSize: 12, marginBottom: 4 }}>主题数量</div>
                        <Select
                          value={maTopNThemes}
                          onChange={setMaTopNThemes}
                          options={[
                            { value: 5, label: '5个' },
                            { value: 10, label: '10个' },
                            { value: 15, label: '15个' },
                            { value: 20, label: '20个' },
                          ]}
                          style={{ width: 100 }}
                          disabled={loadingMultiAgent}
                        />
                      </div>
                      <div>
                        <div style={{ color: '#94a3b8', fontSize: 12, marginBottom: 4 }}>选股上限</div>
                        <Select
                          value={maTopNStocks}
                          onChange={setMaTopNStocks}
                          options={[
                            { value: 10, label: '10只' },
                            { value: 20, label: '20只' },
                            { value: 30, label: '30只' },
                            { value: 50, label: '50只' },
                          ]}
                          style={{ width: 100 }}
                          disabled={loadingMultiAgent}
                        />
                      </div>
                      <div>
                        <div style={{ color: '#94a3b8', fontSize: 12, marginBottom: 4 }}>过滤条件</div>
                        <Select
                          value={maRelaxedFilter ? 'relaxed' : 'strict'}
                          onChange={(v) => setMaRelaxedFilter(v === 'relaxed')}
                          options={[
                            { value: 'strict', label: '严格过滤' },
                            { value: 'relaxed', label: '宽松过滤' },
                          ]}
                          style={{ width: 120 }}
                          disabled={loadingMultiAgent}
                        />
                      </div>
                      <div>
                        <div style={{ color: '#94a3b8', fontSize: 12, marginBottom: 4 }}>LLM深度分析</div>
                        <Select
                          value={maUseLlm ? 'yes' : 'no'}
                          onChange={(v) => setMaUseLlm(v === 'yes')}
                          options={[
                            { value: 'no', label: '关闭（更快）' },
                            { value: 'yes', label: '开启（更准）' },
                          ]}
                          style={{ width: 140 }}
                          disabled={loadingMultiAgent}
                        />
                      </div>
                    </div>
                    <div style={{ marginTop: 12, fontSize: 12, color: '#64748b' }}>
                      提示：如结果为空，可尝试「宽松过滤」或增加「新闻回溯天数」
                    </div>
                  </Card>

                  {loadingMultiAgent && (
                    <div style={{ textAlign: 'center', padding: 48 }}>
                      <Spin size="large" tip="多智能体扫描中，约需30-60秒…" />
                      <div style={{ color: '#64748b', fontSize: 12, marginTop: 12 }}>
                        正在执行13步智能分析流程：新闻采集 → 主题提取 → 策略选择 → 选股推荐
                      </div>
                    </div>
                  )}

                  {multiAgentError && multiAgentPicks.length === 0 && !loadingMultiAgent && (
                    <Alert
                      type="warning"
                      showIcon
                      message="扫描失败"
                      description={multiAgentError + '。请检查后端服务或稍后重试。'}
                      style={{ marginBottom: 16 }}
                    />
                  )}

                  {!loadingMultiAgent && (
                    <>
                    {/* 主题热点区域 */}
                    {multiAgentThemes.length > 0 && (
                      <Card
                        title={<span style={{ color: '#f1f5f9', fontWeight: 600 }}>主题热点（Canonical Themes）</span>}
                        style={{ background: '#0f172a', marginBottom: 16, border: '1px solid #1e293b' }}
                        headStyle={{ background: '#0f172a', borderBottom: '1px solid #1e293b' }}
                      >
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                          {multiAgentThemes.map((theme, idx) => (
                            <Tag
                              key={idx}
                              color={theme.tier === 'Tier1' ? 'gold' : theme.tier === 'Tier2' ? 'blue' : 'default'}
                              style={{ fontSize: 14, padding: '4px 12px' }}
                            >
                              {theme.name}
                              {theme.stage && <span style={{ marginLeft: 4, fontSize: 12 }}>({theme.stage})</span>}
                              {theme.confidence !== undefined && (
                                <span style={{ marginLeft: 4, fontSize: 11, opacity: 0.8 }}>
                                  {Math.round((theme.confidence || 0) * 100)}%
                                </span>
                              )}
                            </Tag>
                          ))}
                        </div>
                      </Card>
                    )}

                    {/* 选股结果区域 */}
                    <Card
                      title={
                        <Space>
                          <span style={{ color: '#f1f5f9', fontWeight: 600 }}>
                            多因子选股结果 ({multiAgentPicks.length}只)
                          </span>
                          {multiAgentPicks.length > 0 && (
                            <Tag color="green" style={{ fontSize: 12 }}>
                              已通过风险校验
                            </Tag>
                          )}
                        </Space>
                      }
                      style={{ background: '#0f172a', marginBottom: 16, border: '1px solid #1e293b' }}
                      headStyle={{ background: '#0f172a', borderBottom: '1px solid #1e293b' }}
                    >
                      {multiAgentPicks.length === 0 ? (
                        <div style={{ color: '#94a3b8', textAlign: 'center', padding: 24 }}>
                          <div style={{ fontSize: 16, marginBottom: 12 }}>暂无选股结果</div>
                          {maStats.theme_stock_count > 0 && (
                            <div style={{ fontSize: 13, color: '#64748b', marginBottom: 12 }}>
                              候选股票：{maStats.theme_stock_count}只 | 过滤掉：{maStats.filtered_count}只
                            </div>
                          )}
                          <div style={{ fontSize: 12, marginBottom: 8 }}>
                            可能原因：当前市场无明确主题热点，或过滤条件较严格
                          </div>
                          <div style={{ fontSize: 12, color: '#64748b' }}>
                            建议：① 切换到「宽松过滤」模式 ② 增加「新闻回溯天数」③ 查看下方执行日志
                          </div>
                        </div>
                      ) : (
                        <Table
                          size="small"
                          dataSource={multiAgentPicks}
                          rowKey="symbol"
                          pagination={{ pageSize: 10 }}
                          columns={[
                            { 
                              title: '标的', 
                              dataIndex: 'symbol', 
                              key: 'symbol', 
                              width: 100,
                              render: (v: string, record: MultiAgentPick) => (
                                <div>
                                  <div style={{ fontWeight: 600 }}>{v}</div>
                                  {record.name && (
                                    <div style={{ fontSize: 12, color: '#94a3b8' }}>{record.name}</div>
                                  )}
                                </div>
                              ),
                            },
                            { 
                              title: '所属主题', 
                              dataIndex: 'theme', 
                              key: 'theme', 
                              width: 120,
                              render: (v: string) => <Tag color="purple">{v}</Tag>,
                            },
                            { 
                              title: '策略标签', 
                              dataIndex: 'strategy_cn', 
                              key: 'strategy_cn', 
                              width: 110,
                              render: (v: string, record: MultiAgentPick) => (
                                <Tag color="cyan">{v || record.strategy}</Tag>
                              ),
                            },
                            { 
                              title: '当前价', 
                              dataIndex: 'current_price', 
                              key: 'current_price', 
                              width: 80,
                              render: (v: number) => v != null ? v.toFixed(2) : '—',
                            },
                            { 
                              title: 'RSI', 
                              dataIndex: 'rsi', 
                              key: 'rsi', 
                              width: 70,
                              render: (v: number) => v != null ? (
                                <span style={{ 
                                  color: v > 70 ? '#f87171' : v < 30 ? '#4ade80' : '#f1f5f9' 
                                }}>
                                  {v.toFixed(1)}
                                </span>
                              ) : '—',
                            },
                            { 
                              title: '均线趋势', 
                              key: 'trend', 
                              width: 120,
                              render: (_: unknown, record: MultiAgentPick) => (
                                <div style={{ fontSize: 12 }}>
                                  {record.ma20 && <div>MA20: {record.ma20.toFixed(2)}</div>}
                                  {record.ma60 && <div>MA60: {record.ma60.toFixed(2)}</div>}
                                  {record.trend && (
                                    <span
                                      style={{
                                        marginTop: 4,
                                        padding: '2px 8px',
                                        borderRadius: 4,
                                        fontSize: 12,
                                        background: record.trend.includes('UP') ? '#166534' : record.trend.includes('DOWN') ? '#991b1b' : '#374151',
                                        color: '#f1f5f9',
                                        display: 'inline-block',
                                      }}
                                    >
                                      {record.trend}
                                    </span>
                                  )}
                                </div>
                              ),
                            },
                            { 
                              title: '风险等级', 
                              dataIndex: 'risk_level', 
                              key: 'risk_level', 
                              width: 90,
                              render: (v: string) => (
                                <Tag 
                                  color={v === '低风险' ? 'green' : v === '中风险' ? 'orange' : v === '高风险' ? 'red' : 'default'}
                                >
                                  {v || '未知'}
                                </Tag>
                              ),
                            },
                            { 
                              title: '选股逻辑', 
                              dataIndex: 'logic', 
                              key: 'logic', 
                              ellipsis: true,
                              render: (v: string) => (
                                <span style={{ color: '#cbd5e1', fontSize: 12 }}>{v || '—'}</span>
                              ),
                            },
                            {
                              title: '操作',
                              key: 'action',
                              width: 80,
                              render: (_: unknown, record: MultiAgentPick) => (
                                <Button 
                                  size="small" 
                                  type="primary"
                                  onClick={() => setSelectedRow(multiAgentToScanItem(record))}
                                >
                                  详情
                                </Button>
                              ),
                            },
                          ]}
                          onRow={(record) => ({
                            onClick: () => setSelectedRow(multiAgentToScanItem(record)),
                            style: { cursor: 'pointer' },
                            onMouseEnter: (e) => { (e.currentTarget as HTMLElement).style.background = 'rgba(45,58,79,0.6)'; },
                            onMouseLeave: (e) => { (e.currentTarget as HTMLElement).style.background = ''; },
                          })}
                        />
                      )}
                    </Card>

                    {/* 执行日志区域 */}
                    {multiAgentLogs.length > 0 && (
                      <Card
                        title={<span style={{ color: '#f1f5f9', fontWeight: 600 }}>执行日志</span>}
                        style={{ background: '#0f172a', marginBottom: 16, border: '1px solid #1e293b' }}
                        headStyle={{ background: '#0f172a', borderBottom: '1px solid #1e293b' }}
                        bodyStyle={{ maxHeight: 300, overflow: 'auto' }}
                      >
                        <div style={{ fontFamily: 'monospace', fontSize: 12 }}>
                          {multiAgentLogs.map((log, idx) => (
                            <div 
                              key={idx} 
                              style={{ 
                                padding: '4px 0', 
                                borderBottom: '1px solid #1e293b',
                                color: log.status === 'error' ? '#f87171' : 
                                       log.status === 'done' ? '#4ade80' : '#94a3b8',
                              }}
                            >
                              <span style={{ color: '#64748b' }}>[{log.step}]</span>
                              <span style={{ marginLeft: 8 }}>{log.status}</span>
                              {log.message && (
                                <span style={{ marginLeft: 8, color: '#cbd5e1' }}>{log.message}</span>
                              )}
                            </div>
                          ))}
                        </div>
                      </Card>
                    )}

                    {/* 研报区域 */}
                    {multiAgentReport && (
                      <Card
                        title={<span style={{ color: '#f1f5f9', fontWeight: 600 }}>智能研报</span>}
                        style={{ background: '#0f172a', border: '1px solid #1e293b' }}
                        headStyle={{ background: '#0f172a', borderBottom: '1px solid #1e293b' }}
                      >
                        <div 
                          style={{ 
                            color: '#e2e8f0', 
                            lineHeight: 1.8, 
                            whiteSpace: 'pre-wrap',
                            fontSize: 13,
                          }}
                        >
                          {multiAgentReport}
                        </div>
                      </Card>
                    )}
                  </>
                  )}
                </div>
              ),
            },
          ]}
        />
      </Card>

      <Drawer
        title={selectedRow ? (selectedRow.name && selectedRow.name !== selectedRow.symbol ? `${selectedRow.name} (${selectedRow.symbol})` : `${selectedRow.symbol}`) : '股票详情'}
        placement="right"
        width={Math.min(560, window.innerWidth * 0.9)}
        open={selectedRow != null}
        onClose={() => setSelectedRow(null)}
        styles={{ body: { background: '#1a2332', color: '#f1f5f9' }, header: { background: '#1a2332', color: '#f1f5f9', borderBottom: '1px solid #2d3a4f' } }}
      >
        {selectedRow && (
          <>
            <Descriptions
              column={1}
              size="small"
              labelStyle={{ color: '#94a3b8', width: 90 }}
              contentStyle={{ color: '#f1f5f9' }}
              items={[
                { label: '标的', children: selectedRow.symbol },
                { label: '名称', children: selectedRow.name ?? '—' },
                { label: '信号', children: selectedRow.signal ? <Tag color={selectedRow.signal === 'BUY' ? 'green' : 'red'}>{selectedRow.signal}</Tag> : '—' },
                { label: '价格', children: selectedRow.price != null ? selectedRow.price.toFixed(2) : '—' },
                { label: '买点概率', children: selectedRow.buy_prob != null ? selectedRow.buy_prob + '%' : '—' },
                { label: '去年营收', children: fmtWanYi(selectedRow.revenue_ly) },
                { label: '去年净利润', children: fmtWanYi(selectedRow.profit_ly) },
                { label: '市盈率', children: selectedRow.pe_ratio != null ? selectedRow.pe_ratio.toFixed(1) : '—' },
                { label: '市净率', children: selectedRow.pb_ratio != null ? selectedRow.pb_ratio.toFixed(2) : '—' },
                { label: '行业', children: selectedRow.industry ?? '—' },
                { label: '区域', children: selectedRow.region ?? '—' },
                { label: '说明', children: selectedRow.reason ?? '—' },
              ]}
            />
            <div style={{ marginTop: 16 }}>
              <div style={{ color: '#94a3b8', marginBottom: 8 }}>K 线</div>
              {loadingDetail ? (
                <Spin tip="加载 K 线…" />
              ) : detailKline.length > 0 ? (
                <TradingChart
                  data={detailKline}
                  signals={detailSignals}
                  ma5={detailMa5}
                  ma10={detailMa10}
                  ma20={detailMa20}
                  height={320}
                />
              ) : (
                <div style={{ color: '#64748b', textAlign: 'center', padding: 24 }}>暂无 K 线数据</div>
              )}
            </div>
          </>
        )}
      </Drawer>
    </div>
  );
}
