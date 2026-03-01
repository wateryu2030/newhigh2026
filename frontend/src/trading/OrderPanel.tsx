/**
 * 下单面板：下单、撤单。
 */
import { useState } from 'react';
import { Button, Input, Select, Card, message } from 'antd';

const BASE = '/api';

export default function OrderPanel() {
  const [symbol, setSymbol] = useState('');
  const [qty, setQty] = useState('');
  const [side, setSide] = useState<'BUY' | 'SELL'>('BUY');
  const [loading, setLoading] = useState(false);

  const placeOrder = async () => {
    if (!symbol.trim() || !qty || Number(qty) <= 0) {
      message.warning('请填写代码与数量');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${BASE}/order`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol: symbol.trim(), qty: Number(qty), side }),
      });
      const data = await res.json();
      if (data.success) message.success('委托已提交');
      else message.error(data.error || '下单失败');
    } catch (e) {
      message.error(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card size="small" title="下单">
      <Input
        placeholder="股票代码"
        value={symbol}
        onChange={(e) => setSymbol(e.target.value)}
        style={{ marginBottom: 8 }}
      />
      <Input
        type="number"
        placeholder="数量"
        value={qty}
        onChange={(e) => setQty(e.target.value)}
        style={{ marginBottom: 8 }}
      />
      <Select
        value={side}
        onChange={setSide}
        style={{ width: '100%', marginBottom: 8 }}
        options={[
          { value: 'BUY', label: '买入' },
          { value: 'SELL', label: '卖出' },
        ]}
      />
      <Button type="primary" block loading={loading} onClick={placeOrder}>
        提交委托
      </Button>
    </Card>
  );
}
