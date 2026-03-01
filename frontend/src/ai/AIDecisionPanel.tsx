/**
 * AI 决策面板：展示 AI 基金经理当前决策、市场状态、策略权重。
 */
import { useState, useEffect } from 'react';
import { Card, Tag, Typography } from 'antd';

const BASE = '/api';

export default function AIDecisionPanel() {
  const [regime, setRegime] = useState<string>('');
  const [weights, setWeights] = useState<Record<string, number>>({});

  useEffect(() => {
    fetch(`${BASE}/ai/decision`)
      .then((r) => r.json())
      .then((d) => {
        if (d.success) {
          setRegime(d.regime ?? '');
          setWeights(d.weights ?? {});
        }
      });
  }, []);

  return (
    <Card size="small" title="AI 组合决策">
      <div style={{ marginBottom: 8 }}>
        <Typography.Text type="secondary">市场状态 </Typography.Text>
        <Tag color={regime === 'bull' ? 'green' : regime === 'bear' ? 'red' : 'default'}>{regime || '-'}</Tag>
      </div>
      <Typography.Text type="secondary">策略权重</Typography.Text>
      <div style={{ marginTop: 4 }}>
        {Object.entries(weights).map(([k, v]) => (
          <span key={k} style={{ marginRight: 12 }}>
            {k}: <strong>{(Number(v) * 100).toFixed(0)}%</strong>
          </span>
        ))}
      </div>
    </Card>
  );
}
