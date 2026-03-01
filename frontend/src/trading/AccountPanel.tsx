/**
 * 资金面板：总资产、可用、冻结。
 */
import { useState, useEffect } from 'react';
import { Card, Statistic } from 'antd';

const BASE = '/api';

export default function AccountPanel() {
  const [balance, setBalance] = useState<{ total_asset?: number; cash?: number; frozen?: number }>({});

  useEffect(() => {
    fetch(`${BASE}/account`)
      .then((r) => r.json())
      .then((d) => {
        if (d.success && d.balance) setBalance(d.balance);
      });
  }, []);

  const total = balance.total_asset ?? 0;
  const cash = balance.cash ?? 0;
  const frozen = balance.frozen ?? 0;

  return (
    <Card size="small" title="资金">
      <Statistic title="总资产" value={total} precision={2} />
      <Statistic title="可用" value={cash} precision={2} style={{ marginTop: 8 }} />
      <Statistic title="冻结" value={frozen} precision={2} style={{ marginTop: 8 }} />
    </Card>
  );
}
