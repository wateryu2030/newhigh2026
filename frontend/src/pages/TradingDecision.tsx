import { useState, useEffect } from 'react';
import { Layout, Card, Input, List, Spin, Tag, Typography, Select } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import KLineChart from '../components/KLineChart';
import SignalMarkers from '../components/SignalMarkers';
import { api } from '../api/client';
import type { KlineBar, Signal, AiScore } from '../types';

const { Sider, Content } = Layout;
const { Text } = Typography;

// 与后端既有策略一致，供买卖点信号选择
const SIGNAL_STRATEGY_OPTIONS = [
  { value: 'ma_cross', label: '均线交叉' },
  { value: 'rsi', label: 'RSI' },
  { value: 'macd', label: 'MACD' },
  { value: 'kdj', label: 'KDJ' },
  { value: 'breakout', label: '突破' },
  { value: 'swing_newhigh', label: '新高' },
];

export default function TradingDecision() {
  const [stocks, setStocks] = useState<{ order_book_id: string; symbol: string; name: string }[]>([]);
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const [kline, setKline] = useState<KlineBar[]>([]);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [aiScore, setAiScore] = useState<AiScore | null>(null);
  const [loading, setLoading] = useState(false);
  const [signalStrategy, setSignalStrategy] = useState<string>('ma_cross');

  useEffect(() => {
    api.stocks().then((r) => {
      const list = r.stocks || [];
      setStocks(list);
      setSelected((prev) => (prev === null && list.length > 0 ? list[0].order_book_id : prev));
    }).catch(() => setStocks([]));
  }, []);

  useEffect(() => {
    if (!selected) {
      setKline([]);
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
      api.kline(selected, startStr, endStr),
      api.signals(selected, signalStrategy),
      api.aiScore(selected),
    ])
      .then(([k, s, a]) => {
        setKline(Array.isArray(k) ? k : []);
        setSignals((s as { signals?: Signal[] })?.signals || []);
        setAiScore((a as AiScore) || null);
      })
      .catch(() => {
        setKline([]);
        setSignals([]);
        setAiScore(null);
      })
      .finally(() => setLoading(false));
  }, [selected, signalStrategy]);

  const filteredStocks = stocks.filter(
    (s) =>
      !search.trim() ||
      s.symbol.includes(search) ||
      (s.name && s.name.includes(search))
  );

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
          <List
            size="small"
            dataSource={filteredStocks.slice(0, 200)}
            renderItem={(item) => (
              <List.Item
                style={{
                  cursor: 'pointer',
                  background: selected === item.order_book_id ? 'rgba(16,185,129,0.15)' : undefined,
                  borderRadius: 4,
                  padding: '4px 8px',
                }}
                onClick={() => setSelected(item.order_book_id)}
              >
                <Text strong={selected === item.order_book_id}>{item.symbol}</Text>
                <Text type="secondary" style={{ fontSize: 12 }}>{item.name || '-'}</Text>
              </List.Item>
            )}
          />
        </Card>
      </Sider>
      <Content style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
        <Card
          title={selected ? `K 线 · ${selected}` : '选择左侧股票加载 K 线'}
          style={{ background: '#111827', flex: 1 }}
        >
          {loading && (
            <div style={{ textAlign: 'center', padding: 48 }}>
              <Spin size="large" />
            </div>
          )}
          {!loading && kline.length > 0 && (
            <KLineChart data={kline} signals={signals.map((s) => ({ date: s.date, type: s.type, price: s.price }))} height={420} />
          )}
          {!loading && selected && kline.length === 0 && (
            <div style={{ color: '#6b7280', textAlign: 'center', padding: 48 }}>暂无 K 线数据</div>
          )}
        </Card>
      </Content>
      <Sider width={320} style={{ background: '#111827', padding: 12 }}>
        <Card size="small" title="AI 评分与建议" style={{ background: '#0f172a', marginBottom: 12 }}>
          {aiScore ? (
            <>
              <div style={{ marginBottom: 8 }}>
                <Text type="secondary">评分 </Text>
                <Tag color={aiScore.score >= 60 ? 'green' : aiScore.score >= 40 ? 'orange' : 'red'}>
                  {aiScore.score?.toFixed(0) ?? '-'} / 100
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
