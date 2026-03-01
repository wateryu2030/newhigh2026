import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Card, Button, Tag, List, Input, message } from 'antd';
import { api, type RLDecisionResponse } from '../api/client';
import type { KlineBar, MaPoint } from '../types';
import TradingChart from '../components/TradingChart';

function dateOffset(d: Date, days: number): string {
  const x = new Date(d);
  x.setDate(x.getDate() + days);
  return x.toISOString().slice(0, 10);
}

export default function RLDecisionView() {
  const [symbol, setSymbol] = useState('000001');
  const [positionPct, setPositionPct] = useState(0);
  const [decision, setDecision] = useState<RLDecisionResponse | null>(null);
  const [kline, setKline] = useState<KlineBar[]>([]);
  const [ma5, setMa5] = useState<MaPoint[]>([]);
  const [ma10, setMa10] = useState<MaPoint[]>([]);
  const [ma20, setMa20] = useState<MaPoint[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchDecision = async () => {
    if (!symbol.trim()) return;
    setLoading(true);
    try {
      const res = await api.rl.decision({ symbol: symbol.trim(), position_pct: positionPct });
      setDecision(res);
    } catch (e) {
      message.error(String(e));
      setDecision(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDecision();
  }, []);

  useEffect(() => {
    if (!symbol.trim()) {
      setKline([]);
      setMa5([]);
      setMa10([]);
      setMa20([]);
      return;
    }
    const end = new Date();
    const start = dateOffset(end, -120);
    api
      .kline(symbol.trim(), start, end.toISOString().slice(0, 10), { indicators: 'ma' })
      .then((k) => {
        if (Array.isArray(k)) {
          setKline(k);
          setMa5([]);
          setMa10([]);
          setMa20([]);
        } else {
          const r = k as { kline: KlineBar[]; ma5?: MaPoint[]; ma10?: MaPoint[]; ma20?: MaPoint[] };
          setKline(r.kline || []);
          setMa5(r.ma5 || []);
          setMa10(r.ma10 || []);
          setMa20(r.ma20 || []);
        }
      })
      .catch(() => {
        setKline([]);
        setMa5([]);
        setMa10([]);
        setMa20([]);
      });
  }, [symbol]);

  const confPct = decision ? Math.round(decision.confidence * 100) : 0;
  const decisionColor = decision?.decision === 'BUY' ? 'green' : decision?.decision === 'SELL' ? 'red' : 'default';

  return (
    <div style={{ padding: 8, color: '#f1f5f9', maxWidth: 800, margin: '0 auto' }}>
      <div style={{ marginBottom: 12 }}>
        <Link to="/rl"><Button type="link" style={{ color: '#94a3b8', padding: 0 }}>← 返回 RL 仪表盘</Button></Link>
      </div>
      <Card
        title={<span style={{ color: '#f1f5f9', fontWeight: 600 }}>AI 决策可视化</span>}
        style={{ background: '#1a2332', border: '1px solid #2d3a4f', marginBottom: 16 }}
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center', marginBottom: 16 }}>
          <Input
            placeholder="股票代码"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            style={{ width: 120, background: '#1e293b', border: '1px solid #334155', color: '#f1f5f9' }}
          />
          <Input
            type="number"
            placeholder="当前仓位%"
            value={positionPct || ''}
            onChange={(e) => setPositionPct(Number(e.target.value) || 0)}
            style={{ width: 100, background: '#1e293b', border: '1px solid #334155', color: '#f1f5f9' }}
          />
          <Button type="primary" loading={loading} onClick={fetchDecision}>
            获取 AI 决策
          </Button>
        </div>

        {decision && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16 }}>
            <div>
              <div style={{ color: '#94a3b8', fontSize: 12, marginBottom: 4 }}>决策</div>
              <Tag color={decisionColor} style={{ fontSize: 16, padding: '4px 12px' }}>
                {decision.decision}
              </Tag>
            </div>
            <div>
              <div style={{ color: '#94a3b8', fontSize: 12, marginBottom: 4 }}>AI 信心</div>
              <span style={{ fontSize: 18, color: '#22c55e' }}>{confPct}%</span>
            </div>
            <div>
              <div style={{ color: '#94a3b8', fontSize: 12, marginBottom: 4 }}>当前状态</div>
              <span style={{ color: '#f1f5f9' }}>{decision.state_summary}</span>
            </div>
            <div>
              <div style={{ color: '#94a3b8', fontSize: 12, marginBottom: 4 }}>建议仓位</div>
              <span style={{ color: '#f1f5f9' }}>{decision.suggested_position_pct}%</span>
            </div>
          </div>
        )}
      </Card>

      {decision?.reason && decision.reason.length > 0 && (
        <Card
          title="AI 为什么这样决策"
          style={{ background: '#1a2332', border: '1px solid #2d3a4f', marginBottom: 16 }}
        >
          <List
            size="small"
            dataSource={decision.reason}
            renderItem={(item) => (
              <List.Item style={{ border: 'none', color: '#cbd5e1' }}>
                <span style={{ marginRight: 8 }}>•</span>
                {item}
              </List.Item>
            )}
          />
        </Card>
      )}

      {kline.length > 0 && (
        <Card title="K 线 + AI 决策" style={{ background: '#1a2332', border: '1px solid #2d3a4f' }}>
          <TradingChart
            data={kline}
            signals={
              decision
                ? [
                    {
                      date: (kline[kline.length - 1]?.time || '').toString().slice(0, 10),
                      type: decision.decision as 'BUY' | 'SELL' | 'HOLD',
                      price: kline[kline.length - 1]?.close ?? 0,
                    },
                  ]
                : []
            }
            ma5={ma5}
            ma10={ma10}
            ma20={ma20}
            height={360}
          />
        </Card>
      )}
    </div>
  );
}
