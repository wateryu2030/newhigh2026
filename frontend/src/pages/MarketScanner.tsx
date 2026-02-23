import { useState, useEffect } from 'react';
import { Card, Tabs, Table, Tag, Spin } from 'antd';
import { api } from '../api/client';
import type { ScanItem } from '../types';

const columns = [
  { title: '标的', dataIndex: 'symbol', key: 'symbol', width: 100 },
  { title: '名称', dataIndex: 'name', key: 'name', ellipsis: true },
  { title: '信号', dataIndex: 'signal', key: 'signal', width: 80, render: (v: string) => v && <Tag color={v === 'BUY' ? 'green' : 'red'}>{v}</Tag> },
  { title: '价格', dataIndex: 'price', key: 'price', width: 80, render: (v: number) => v?.toFixed(2) },
  { title: '买点概率', dataIndex: 'buy_prob', key: 'buy_prob', width: 90, render: (v: number) => v != null ? v + '%' : '-' },
  { title: '说明', dataIndex: 'reason', key: 'reason', ellipsis: true },
];

export default function MarketScanner() {
  const [loading, setLoading] = useState(true);
  const [breakout, setBreakout] = useState<ScanItem[]>([]);
  const [strong, setStrong] = useState<ScanItem[]>([]);
  const [aiRec, setAiRec] = useState<ScanItem[]>([]);

  const load = async () => {
    setLoading(true);
    try {
      const [r1, r2, r3] = await Promise.all([
        api.scan('breakout').catch(() => ({ results: [] })),
        api.scan('strong').catch(() => ({ results: [] })),
        api.scan('ai').catch(() => ({ results: [] })),
      ]);
      setBreakout((r1 as { results: ScanItem[] }).results || []);
      setStrong((r2 as { results: ScanItem[] }).results || []);
      setAiRec((r3 as { results: ScanItem[] }).results || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div style={{ padding: 8 }}>
      <Card title="市场扫描器" style={{ background: '#111827', marginBottom: 16 }} extra={<a onClick={load}>刷新</a>}>
        <Tabs
          items={[
            {
              key: 'breakout',
              label: '突破股票',
              children: (
                loading ? <Spin /> : (
                  breakout.length === 0 ? <div style={{ color: '#6b7280', textAlign: 'center', padding: 24 }}>暂无突破股票</div> : <Table size="small" dataSource={breakout} columns={columns} rowKey="symbol" pagination={{ pageSize: 15 }} />
                )
              ),
            },
            {
              key: 'strong',
              label: '强势股',
              children: (
                loading ? <Spin /> : (
                  strong.length === 0 ? <div style={{ color: '#6b7280', textAlign: 'center', padding: 24 }}>暂无强势股</div> : <Table size="small" dataSource={strong} columns={columns} rowKey="symbol" pagination={{ pageSize: 15 }} />
                )
              ),
            },
            {
              key: 'ai',
              label: 'AI 推荐',
              children: (
                loading ? <Spin /> : (
                  aiRec.length === 0 ? <div style={{ color: '#6b7280', textAlign: 'center', padding: 24 }}>暂无 AI 推荐</div> : <Table size="small" dataSource={aiRec} columns={columns} rowKey="symbol" pagination={{ pageSize: 15 }} />
                )
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
}
