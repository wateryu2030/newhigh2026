import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Card, Button, Progress, Statistic, Row, Col, InputNumber, message } from 'antd';
import { api, type RLPerformanceResponse } from '../api/client';

export default function RLTrainingDashboard() {
  const [loading, setLoading] = useState(false);
  const [perf, setPerf] = useState<RLPerformanceResponse | null>(null);
  const [symbol, setSymbol] = useState('000001');
  const [totalTimesteps, setTotalTimesteps] = useState(30000);
  const [startDate, setStartDate] = useState('2023-01-01');
  const [endDate, setEndDate] = useState('2024-12-31');

  const loadPerformance = useCallback(async () => {
    try {
      const data = await api.rl.performance();
      setPerf(data);
    } catch (e) {
      setPerf(null);
    }
  }, []);

  useEffect(() => {
    loadPerformance();
  }, [loadPerformance]);

  const handleTrain = async () => {
    setLoading(true);
    try {
      const res = await api.rl.train({
        symbol,
        start_date: startDate,
        end_date: endDate,
        total_timesteps: totalTimesteps,
      });
      if (res.success) {
        message.success('训练已启动/完成');
        await loadPerformance();
      } else {
        message.error(res.error || '训练失败');
      }
    } catch (e: unknown) {
      message.error(String(e));
    } finally {
      setLoading(false);
    }
  };

  const rewards = perf?.rewards ?? [];
  const actions = perf?.actions ?? {};
  const hold = actions[0] ?? 0;
  const buy = actions[1] ?? 0;
  const sell = actions[2] ?? 0;
  const total = hold + buy + sell;

  return (
    <div style={{ padding: 8, color: '#f1f5f9', maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ marginBottom: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <Link to="/rl/performance">
          <Button type="default" style={{ borderColor: '#2d3a4f', color: '#94a3b8' }}>查看绩效</Button>
        </Link>
        <Link to="/rl/decision">
          <Button type="default" style={{ borderColor: '#2d3a4f', color: '#94a3b8' }}>AI 决策</Button>
        </Link>
      </div>
      <Card
        title={<span style={{ color: '#f1f5f9', fontWeight: 600 }}>RL 训练仪表盘</span>}
        style={{ background: '#1a2332', border: '1px solid #2d3a4f', marginBottom: 16 }}
      >
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={6}>
            <InputNumber
              addonBefore="标的"
              value={symbol}
              onChange={(v) => setSymbol(String(v ?? '000001'))}
              style={{ width: '100%' }}
              stringMode
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <InputNumber addonBefore="步数" value={totalTimesteps} onChange={(v) => setTotalTimesteps(Number(v) || 30000)} style={{ width: '100%' }} />
          </Col>
          <Col xs={24} sm={8} md={4}>
            <input
              type="text"
              placeholder="开始日期"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              style={{ width: '100%', padding: '4px 8px', background: '#1e293b', border: '1px solid #334155', color: '#f1f5f9', borderRadius: 4 }}
            />
          </Col>
          <Col xs={24} sm={8} md={4}>
            <input
              type="text"
              placeholder="结束日期"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              style={{ width: '100%', padding: '4px 8px', background: '#1e293b', border: '1px solid #334155', color: '#f1f5f9', borderRadius: 4 }}
            />
          </Col>
          <Col xs={24} sm={8} md={4}>
            <Button type="primary" loading={loading} onClick={handleTrain} style={{ width: '100%' }}>
              开始训练
            </Button>
          </Col>
        </Row>
      </Card>

      <Row gutter={16}>
        <Col xs={24} md={12}>
          <Card title="训练曲线 (Reward)" style={{ background: '#1a2332', border: '1px solid #2d3a4f' }}>
            {rewards.length > 0 ? (
              <div style={{ height: 200, overflow: 'auto' }}>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                  {rewards.slice(-200).map((r, i) => (
                    <div
                      key={i}
                      style={{
                        width: 4,
                        height: Math.max(2, Math.min(40, (r + 0.1) * 80)),
                        background: r >= 0 ? '#22c55e' : '#f87171',
                        borderRadius: 1,
                      }}
                    />
                  ))}
                </div>
              </div>
            ) : (
              <div style={{ color: '#94a3b8', textAlign: 'center', padding: 24 }}>暂无训练数据，请先执行训练</div>
            )}
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="实时指标" style={{ background: '#1a2332', border: '1px solid #2d3a4f' }}>
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Statistic title="总收益率" value={(perf?.total_return ?? 0) * 100} suffix="%" valueStyle={{ color: '#22c55e' }} />
              </Col>
              <Col span={12}>
                <Statistic title="夏普比率" value={perf?.sharpe ?? 0} valueStyle={{ color: '#f1f5f9' }} />
              </Col>
              <Col span={12}>
                <Statistic title="最大回撤" value={(perf?.max_drawdown ?? 0) * 100} suffix="%" valueStyle={{ color: '#f87171' }} />
              </Col>
              <Col span={12}>
                <Statistic title="训练步数" value={perf?.train_log?.total_timesteps ?? 0} valueStyle={{ color: '#94a3b8' }} />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      <Card title="AI 行为分布" style={{ background: '#1a2332', border: '1px solid #2d3a4f', marginTop: 16 }}>
        <Row gutter={16}>
          <Col xs={8}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 28, color: '#22c55e' }}>{buy}</div>
              <div style={{ color: '#94a3b8' }}>买入</div>
            </div>
          </Col>
          <Col xs={8}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 28, color: '#94a3b8' }}>{hold}</div>
              <div style={{ color: '#94a3b8' }}>持仓</div>
            </div>
          </Col>
          <Col xs={8}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 28, color: '#f87171' }}>{sell}</div>
              <div style={{ color: '#94a3b8' }}>卖出</div>
            </div>
          </Col>
        </Row>
        {total > 0 && (
          <Progress
            percent={Math.round((buy / total) * 100)}
            success={{ percent: Math.round((hold / total) * 100) }}
            format={() => `买${Math.round((buy / total) * 100)}% 持${Math.round((hold / total) * 100)}% 卖${Math.round((sell / total) * 100)}%`}
            style={{ marginTop: 12 }}
          />
        )}
      </Card>
    </div>
  );
}
