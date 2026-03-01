/**
 * 持仓面板：展示当前持仓列表。
 */
import { useState, useEffect } from 'react';
import { Card, Table, Typography } from 'antd';

const BASE = '/api';

export default function PositionPanel() {
  const [positions, setPositions] = useState<Record<string, { qty?: number; cost?: number; market_value?: number }>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${BASE}/account`)
      .then((r) => r.json())
      .then((d) => {
        if (d.success && d.positions) setPositions(d.positions);
      })
      .finally(() => setLoading(false));
  }, []);

  const rows = Object.entries(positions).map(([symbol, p]) => ({
    symbol,
    qty: p?.qty ?? 0,
    cost: p?.cost ?? 0,
    market_value: p?.market_value ?? p?.cost ?? 0,
  })).filter((r) => r.qty > 0);

  return (
    <Card size="small" title="持仓">
      <Table
        size="small"
        loading={loading}
        dataSource={rows}
        columns={[
          { title: '代码', dataIndex: 'symbol', key: 'symbol' },
          { title: '数量', dataIndex: 'qty', key: 'qty' },
          { title: '市值', dataIndex: 'market_value', key: 'market_value', render: (v: number) => (v ?? 0).toFixed(2) },
        ]}
        rowKey="symbol"
        pagination={false}
      />
      {rows.length === 0 && !loading && <Typography.Text type="secondary">暂无持仓</Typography.Text>}
    </Card>
  );
}
