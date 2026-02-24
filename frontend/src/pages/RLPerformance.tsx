import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Card, Row, Col, Statistic, Button } from 'antd';
import { api, type RLPerformanceResponse } from '../api/client';

export default function RLPerformance() {
  const [data, setData] = useState<RLPerformanceResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.rl.performance();
        if (!cancelled) setData(res);
      } catch (e) {
        if (!cancelled) setData(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const curve = data?.curve ?? [];
  const maxVal = curve.length ? Math.max(...curve.map((c) => c.value)) : 1;
  const minVal = curve.length ? Math.min(...curve.map((c) => c.value)) : 0;

  return (
    <div style={{ padding: 8, color: '#f1f5f9', maxWidth: 1000, margin: '0 auto' }}>
      <div style={{ marginBottom: 12 }}>
        <Link to="/rl"><Button type="link" style={{ color: '#94a3b8', padding: 0 }}>← 返回 RL 仪表盘</Button></Link>
      </div>
      <Card
        title={<span style={{ color: '#f1f5f9', fontWeight: 600 }}>RL 策略绩效</span>}
        style={{ background: '#1a2332', border: '1px solid #2d3a4f' }}
        loading={loading}
      >
        <Row gutter={[16, 16]}>
          <Col xs={12} md={6}>
            <Statistic title="总收益率" value={((data?.total_return ?? 0) * 100).toFixed(2)} suffix="%" valueStyle={{ color: '#22c55e' }} />
          </Col>
          <Col xs={12} md={6}>
            <Statistic title="夏普比率" value={data?.sharpe ?? 0} valueStyle={{ color: '#f1f5f9' }} />
          </Col>
          <Col xs={12} md={6}>
            <Statistic title="最大回撤" value={((data?.max_drawdown ?? 0) * 100).toFixed(2)} suffix="%" valueStyle={{ color: '#f87171' }} />
          </Col>
          <Col xs={12} md={6}>
            <Statistic title="样本数" value={curve.length} valueStyle={{ color: '#94a3b8' }} />
          </Col>
        </Row>

        <div style={{ marginTop: 24 }}>
          <div style={{ color: '#94a3b8', marginBottom: 8 }}>净值曲线</div>
          {curve.length > 0 ? (
            <div
              style={{
                height: 280,
                display: 'flex',
                alignItems: 'flex-end',
                gap: 2,
                padding: '8px 0',
              }}
            >
              {curve.filter((_, i) => i % Math.max(1, Math.floor(curve.length / 120)) === 0).map((c, i) => (
                <div
                  key={i}
                  title={`${c.date} ${(c.value * 100).toFixed(2)}%`}
                  style={{
                    flex: 1,
                    minWidth: 4,
                    height: `${((c.value - minVal) / (maxVal - minVal || 1)) * 100}%`,
                    background: c.action === 1 ? '#22c55e' : c.action === 2 ? '#f87171' : '#64748b',
                    borderRadius: 2,
                  }}
                />
              ))}
            </div>
          ) : (
            <div style={{ color: '#64748b', textAlign: 'center', padding: 32 }}>暂无回测曲线，请先训练并评估</div>
          )}
        </div>

        {data?.actions && (
          <Row gutter={16} style={{ marginTop: 16 }}>
            <Col span={8}>
              <Statistic title="买入次数" value={data.actions[1] ?? 0} valueStyle={{ color: '#22c55e' }} />
            </Col>
            <Col span={8}>
              <Statistic title="持仓次数" value={data.actions[0] ?? 0} valueStyle={{ color: '#94a3b8' }} />
            </Col>
            <Col span={8}>
              <Statistic title="卖出次数" value={data.actions[2] ?? 0} valueStyle={{ color: '#f87171' }} />
            </Col>
          </Row>
        )}
      </Card>
    </div>
  );
}
