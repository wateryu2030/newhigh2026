import { useState, useEffect } from 'react';
import { Layout, Card, Input, List, Spin, Tag, Typography, Select, Button, Segmented, message } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import TradingChart from '../components/TradingChart';
import SignalMarkers from '../components/SignalMarkers';
import { api, type NewsItem } from '../api/client';
import type { KlineBar, Signal, AiScore, MaPoint } from '../types';
import { pinyin } from 'pinyin-pro';

const { Sider, Content } = Layout;
const { Text } = Typography;

function isInExtendedTradingWindow(now: Date): boolean {
  // A 股交易时段：09:30-11:30, 13:00-15:00
  // 这里按要求前后各加 30 分钟，得到：
  // 09:00-12:00 与 12:30-15:30
  const h = now.getHours();
  const m = now.getMinutes();
  const minutes = h * 60 + m;
  const morningStart = 9 * 60; // 09:00
  const morningEnd = 12 * 60; // 12:00
  const afternoonStart = 12 * 60 + 30; // 12:30
  const afternoonEnd = 15 * 60 + 30; // 15:30
  return (minutes >= morningStart && minutes <= morningEnd) || (minutes >= afternoonStart && minutes <= afternoonEnd);
}

function getNewsRefreshIntervalMs(now: Date = new Date()): number {
  // 交易时段前后各 30 分钟：每 30 分钟刷新
  // 其余时间：每 1 小时刷新
  return isInExtendedTradingWindow(now) ? 30 * 60 * 1000 : 60 * 60 * 1000;
}

// 与后端既有策略一致，供买卖点信号选择
const SIGNAL_STRATEGY_OPTIONS = [
  { value: 'ma_cross', label: '均线交叉' },
  { value: 'rsi', label: 'RSI' },
  { value: 'macd', label: 'MACD' },
  { value: 'kdj', label: 'KDJ' },
  { value: 'breakout', label: '突破' },
  { value: 'swing_newhigh', label: '新高' },
];

function loadStocksIntoState(
  setStocks: (v: { order_book_id: string; symbol: string; name: string }[]) => void,
  setSearchMeta: (v: Record<string, { full: string; first: string }>) => void,
  setSelected: (fn: (prev: string | null) => string | null) => void,
) {
  return api.stocks().then((r) => {
    const list = r.stocks || [];
    setStocks(list);
    const meta: Record<string, { full: string; first: string }> = {};
    list.forEach((s) => {
      const name = (s.name || '').trim();
      if (!name) return;
      try {
        const fullArr = pinyin(name, { toneType: 'none', type: 'array' });
        const firstArr = pinyin(name, { pattern: 'first', type: 'array' });
        meta[s.order_book_id] = {
          full: fullArr.join('').toLowerCase(),
          first: firstArr.join('').toLowerCase(),
        };
      } catch {
        /* ignore */
      }
    });
    setSearchMeta(meta);
    setSelected((prev) => (prev === null && list.length > 0 ? list[0].order_book_id : prev));
    return list;
  });
}

export default function TradingDecision() {
  const [stocks, setStocks] = useState<{ order_book_id: string; symbol: string; name: string }[]>([]);
  const [stocksLoading, setStocksLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const [kline, setKline] = useState<KlineBar[]>([]);
  const [ma5, setMa5] = useState<MaPoint[]>([]);
  const [ma10, setMa10] = useState<MaPoint[]>([]);
  const [ma20, setMa20] = useState<MaPoint[]>([]);
  const [ma30, setMa30] = useState<MaPoint[]>([]);
  const [ma60, setMa60] = useState<MaPoint[]>([]);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [aiScore, setAiScore] = useState<AiScore | null>(null);
  const [loading, setLoading] = useState(false);
  const [signalStrategy, setSignalStrategy] = useState<string>('ma_cross');
  const [news, setNews] = useState<NewsItem[]>([]);
  const [newsLoading, setNewsLoading] = useState(false);
  const [nextNewsRefresh, setNextNewsRefresh] = useState<string | null>(null);
  const [searchMeta, setSearchMeta] = useState<Record<string, { full: string; first: string }>>({});
  const [chartPeriod, setChartPeriod] = useState<'day' | 'week' | 'month'>('day');
  const [chartMaSet, setChartMaSet] = useState<'basic' | 'full'>('full');
  const [chartSubCharts, setChartSubCharts] = useState<'none' | 'kdj' | 'macd' | 'both'>('both');

  useEffect(() => {
    setStocksLoading(true);
    loadStocksIntoState(setStocks, setSearchMeta, setSelected)
      .catch(() => setStocks([]))
      .finally(() => setStocksLoading(false));
  }, []);

  useEffect(() => {
    if (!selected) {
      setKline([]);
      setMa5([]);
      setMa10([]);
      setMa20([]);
      setMa30([]);
      setMa60([]);
      setSignals([]);
      setAiScore(null);
      return;
    }
    setLoading(true);
    const end = new Date();
    const start = new Date();
    start.setFullYear(start.getFullYear() - 1);
    const startStr = start.toISOString().slice(0, 10);
    const endStr = end.toISOString().slice(0, 10);
    Promise.all([
      api.kline(selected, startStr, endStr, { indicators: 'ma', period: chartPeriod }),
      api.signals(selected, signalStrategy),
      api.aiScore(selected),
    ])
      .then(([k, s, a]) => {
        if (Array.isArray(k)) {
          setKline(k);
          setMa5([]);
          setMa10([]);
          setMa20([]);
          setMa30([]);
          setMa60([]);
        } else {
          const kr = k as { kline?: KlineBar[]; ma5?: MaPoint[]; ma10?: MaPoint[]; ma20?: MaPoint[]; ma30?: MaPoint[]; ma60?: MaPoint[] };
          setKline(kr.kline || []);
          setMa5(kr.ma5 || []);
          setMa10(kr.ma10 || []);
          setMa20(kr.ma20 || []);
          setMa30(kr.ma30 || []);
          setMa60(kr.ma60 || []);
        }
        setSignals((s as { signals?: Signal[] })?.signals || []);
        setAiScore((a as AiScore) || null);
      })
      .catch(() => {
        setKline([]);
        setMa5([]);
        setMa10([]);
        setMa20([]);
        setMa30([]);
        setMa60([]);
        setSignals([]);
        setAiScore(null);
      })
      .finally(() => setLoading(false));
  }, [selected, signalStrategy, chartPeriod]);

  // 新闻热点：根据交易时段自动调整刷新频率，并触发后端存库
  useEffect(() => {
    if (!selected) {
      setNews([]);
      return;
    }
    let timer: number | undefined;
    let cancelled = false;

    const loadNews = async () => {
      try {
        setNewsLoading(true);
        const symbolCode = selected.split('.')[0];
        const res = await api.news({ symbol: symbolCode, sources: 'eastmoney,caixin', limit: 30 });
        if (!cancelled && res.success) {
          setNews(res.news || []);
        }
      } catch {
        if (!cancelled) {
          setNews([]);
        }
      } finally {
        if (!cancelled) {
          setNewsLoading(false);
          const interval = getNewsRefreshIntervalMs(new Date());
          const nextAt = new Date(Date.now() + interval);
          setNextNewsRefresh(nextAt.toTimeString().slice(0, 5));
          timer = window.setTimeout(loadNews, interval);
        }
      }
    };

    loadNews();

    return () => {
      cancelled = true;
      if (timer) {
        window.clearTimeout(timer);
      }
    };
  }, [selected]);

  const filteredStocks = stocks.filter((s) => {
    const q = search.trim().toLowerCase();
    if (!q) return true;
    const symbol = (s.symbol || '').toLowerCase();
    const name = (s.name || '').toLowerCase();
    if (symbol.includes(q) || name.includes(q)) return true;
    const meta = searchMeta[s.order_book_id];
    if (meta && (meta.full.includes(q) || meta.first.includes(q))) return true;
    return false;
  });

  const selectedStock = selected ? stocks.find((s) => s.order_book_id === selected) : undefined;
  const klineTitle = selectedStock
    ? `K 线 · ${selectedStock.symbol} ${selectedStock.name && selectedStock.name !== selectedStock.symbol ? `· ${selectedStock.name}` : ''}`
    : selected
      ? `K 线 · ${selected}`
      : '选择左侧股票加载 K 线';

  return (
    <Layout style={{ background: '#0b0f17', minHeight: 'calc(100vh - 100px)' }}>
      <Sider width={280} style={{ background: '#111827', padding: 12 }}>
        <Input
          placeholder="搜索股票"
          prefix={<SearchOutlined />}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ marginBottom: 12 }}
          allowClear
        />
        <Card size="small" title="股票列表" style={{ background: '#0f172a' }}>
          {stocksLoading && (
            <div style={{ textAlign: 'center', padding: 24 }}>
              <Spin size="small" /> 加载中…
            </div>
          )}
          {!stocksLoading && filteredStocks.length === 0 && (
            <div style={{ textAlign: 'center', padding: 24, color: '#9ca3af', fontSize: 12 }}>
              <div style={{ marginBottom: 8 }}>暂无股票数据</div>
              <div style={{ marginBottom: 12 }}>请确认后端服务已启动且数据库已有日线或股票表数据</div>
              <Button size="small" type="primary" onClick={() => { setStocksLoading(true); loadStocksIntoState(setStocks, setSearchMeta, setSelected).catch(() => setStocks([])).finally(() => setStocksLoading(false)); }}>刷新列表</Button>
            </div>
          )}
          {!stocksLoading && filteredStocks.length > 0 && (
            <div style={{ marginBottom: 8, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <Button size="small" onClick={() => { setStocksLoading(true); loadStocksIntoState(setStocks, setSearchMeta, setSelected).catch(() => setStocks([])).finally(() => setStocksLoading(false)); }}>刷新列表</Button>
              <Button size="small" onClick={() => { api.backfillStockNames().then((r) => { if (r?.success) message.success(r.message || '已启动补全，请稍后点击刷新列表'); }).catch((e) => message.error(e?.message || '补全失败')); }}>补全名称</Button>
            </div>
          )}
          {!stocksLoading && filteredStocks.length > 0 && (
          <List
            size="small"
            dataSource={filteredStocks.slice(0, 200)}
            renderItem={(item) => {
              const displayName = item.name && item.name !== item.symbol ? item.name : item.symbol;
              const subText = item.name && item.name !== item.symbol ? `${item.symbol} · ${item.order_book_id}` : item.order_book_id;
              return (
                <List.Item
                  style={{
                    cursor: 'pointer',
                    background: selected === item.order_book_id ? 'rgba(16,185,129,0.15)' : undefined,
                    borderRadius: 4,
                    padding: '4px 8px',
                  }}
                  onClick={() => setSelected(item.order_book_id)}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', width: '100%' }}>
                    <Text strong={selected === item.order_book_id} style={{ fontSize: 13 }}>
                      {displayName} {item.name && item.name !== item.symbol ? item.symbol : ''}
                    </Text>
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      {subText}
                    </Text>
                  </div>
                </List.Item>
              );
            }}
          />
          )}
        </Card>
      </Sider>
      <Content style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
        <Card
          title={klineTitle}
          style={{ background: '#111827', flex: 1 }}
        >
          {/* 图表展示组合：周期、均线、副图 */}
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              gap: 16,
              marginBottom: 12,
              paddingBottom: 12,
              borderBottom: '1px solid #1f2937',
            }}
          >
            <span style={{ color: '#9ca3af', fontSize: 12 }}>周期</span>
            <Segmented
              size="small"
              value={chartPeriod}
              onChange={(v) => setChartPeriod(v as 'day' | 'week' | 'month')}
              options={[
                { value: 'day', label: '日K' },
                { value: 'week', label: '周K' },
                { value: 'month', label: '月K' },
              ]}
            />
            <span style={{ color: '#9ca3af', fontSize: 12, marginLeft: 8 }}>均线</span>
            <Segmented
              size="small"
              value={chartMaSet}
              onChange={(v) => setChartMaSet(v as 'basic' | 'full')}
              options={[
                { value: 'basic', label: 'MA5/10/20' },
                { value: 'full', label: 'MA5/10/20/30/60' },
              ]}
            />
            <span style={{ color: '#9ca3af', fontSize: 12, marginLeft: 8 }}>副图</span>
            <Segmented
              size="small"
              value={chartSubCharts}
              onChange={(v) => setChartSubCharts(v as 'none' | 'kdj' | 'macd' | 'both')}
              options={[
                { value: 'none', label: '无' },
                { value: 'kdj', label: 'KDJ' },
                { value: 'macd', label: 'MACD' },
                { value: 'both', label: 'KDJ+MACD' },
              ]}
            />
          </div>
          {loading && (
            <div style={{ textAlign: 'center', padding: 48 }}>
              <Spin size="large" />
            </div>
          )}
          {!loading && kline.length > 0 && (
            <TradingChart
              data={kline}
              signals={signals.map((s) => ({ date: s.date, type: s.type, price: s.price }))}
              ma5={ma5}
              ma10={ma10}
              ma20={ma20}
              ma30={ma30}
              ma60={ma60}
              height={380}
              maSet={chartMaSet}
              showKDJ={chartSubCharts === 'kdj' || chartSubCharts === 'both'}
              showMACD={chartSubCharts === 'macd' || chartSubCharts === 'both'}
            />
          )}
          {!loading && selected && kline.length === 0 && (
            <div style={{ color: '#6b7280', textAlign: 'center', padding: 48 }}>暂无 K 线数据</div>
          )}
        </Card>
      </Content>
      <Sider width={320} style={{ background: '#111827', padding: 12 }}>
        <Card
          size="small"
          title="新闻热点"
          style={{ background: '#0f172a', marginBottom: 12, maxHeight: 280, overflowY: 'auto' }}
        >
          {newsLoading && (
            <div style={{ textAlign: 'center', padding: 12 }}>
              <Spin size="small" />
            </div>
          )}
          {!newsLoading && news.length === 0 && (
            <>
              <Text type="secondary" style={{ fontSize: 12 }}>
                暂无新闻，系统会按时段自动刷新。
              </Text>
              <div style={{ marginTop: 8 }}>
                <Button size="small" onClick={() => { setNewsLoading(true); const code = selected?.split('.')[0]; if (code) api.news({ symbol: code, sources: 'eastmoney,caixin', limit: 30 }).then((r) => { if (r.success) setNews(r.news || []); }).finally(() => setNewsLoading(false)); }}>刷新新闻</Button>
              </div>
            </>
          )}
          {!newsLoading && news.length > 0 && (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                {nextNewsRefresh && <span style={{ fontSize: 11, color: '#9ca3af' }}>下次刷新 {nextNewsRefresh}</span>}
                <Button size="small" type="link" style={{ padding: 0, fontSize: 12 }} onClick={() => { setNewsLoading(true); const code = selected?.split('.')[0]; if (code) api.news({ symbol: code, sources: 'eastmoney,caixin', limit: 30 }).then((r) => { if (r.success) setNews(r.news || []); }).finally(() => setNewsLoading(false)); }}>刷新</Button>
              </div>
              <List
                size="small"
                split={false}
                dataSource={news.slice(0, 20)}
                renderItem={(item) => (
                  <List.Item style={{ padding: '4px 0' }}>
                    <div>
                      <a
                        href={item.url || '#'}
                        target="_blank"
                        rel="noreferrer"
                        style={{ color: '#e5e7eb', fontSize: 13 }}
                      >
                        {item.title || item.source || '新闻'}
                      </a>
                      <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>
                        {(item.source || item.source_site) && `${item.source || item.source_site} · `}
                        {item.publish_time || ''}
                        {item.sentiment_label && ` · 情绪 ${item.sentiment_label}`}
                      </div>
                    </div>
                  </List.Item>
                )}
              />
            </>
          )}
        </Card>
        <Card size="small" title="AI 评分与建议" style={{ background: '#0f172a', marginBottom: 12 }}>
          {aiScore ? (
            aiScore.score != null && aiScore.suggestion != null ? (
              <>
                <div style={{ marginBottom: 8 }}>
                  <Text type="secondary">评分 </Text>
                  <Tag color={Number(aiScore.score) >= 60 ? 'green' : Number(aiScore.score) >= 40 ? 'orange' : 'red'}>
                    {Number(aiScore.score).toFixed(0)} / 100
                  </Tag>
                </div>
                <div style={{ marginBottom: 8 }}>
                  <Text type="secondary">建议 </Text>
                  <Tag color={aiScore.suggestion === 'BUY' ? 'green' : aiScore.suggestion === 'SELL' ? 'red' : 'default'}>
                    {aiScore.suggestion}
                  </Tag>
                </div>
                {aiScore.position_pct != null && (
                  <div style={{ marginBottom: 8 }}>
                    <Text type="secondary">建议仓位 </Text>
                    <Text>{aiScore.position_pct.toFixed(1)}%</Text>
                  </div>
                )}
                {aiScore.risk_level && (
                  <div style={{ marginBottom: 8 }}>
                    <Text type="secondary">风险等级 </Text>
                    <Text>{aiScore.risk_level}</Text>
                  </div>
                )}
                {aiScore.latest_signal && (
                  <div>
                    <Text type="secondary">最新信号 </Text>
                    <Text>{aiScore.latest_signal}</Text>
                  </div>
                )}
              </>
            ) : (
              <Text type="secondary" style={{ fontSize: 12 }}>暂无 AI 评分（需训练模型或数据充足）</Text>
            )
          ) : (
            <Text type="secondary">选择股票后加载</Text>
          )}
        </Card>
        <div style={{ marginBottom: 8 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>信号策略 </Text>
          <Select
            size="small"
            options={SIGNAL_STRATEGY_OPTIONS}
            value={signalStrategy}
            onChange={setSignalStrategy}
            style={{ width: '100%', marginTop: 4 }}
          />
        </div>
        <SignalMarkers signals={signals} symbol={selected || undefined} />
      </Sider>
    </Layout>
  );
}
