import { useState } from 'react';
import { Card, Form, Input, Button, Table, Row, Col, Select } from 'antd';
import ReactECharts from 'echarts-for-react';
import { api } from '../api/client';
import type { BacktestResult } from '../types';

// 与后端 strategies/__init__.py PLUGIN_STRATEGIES 一致，引用既有策略
const STRATEGY_OPTIONS = [
  { value: 'ma_cross', label: '均线交叉 (ma_cross)' },
  { value: 'rsi', label: 'RSI (rsi)' },
  { value: 'macd', label: 'MACD (macd)' },
  { value: 'kdj', label: 'KDJ (kdj)' },
  { value: 'breakout', label: '突破 (breakout)' },
  { value: 'swing_newhigh', label: '新高 (swing_newhigh)' },
];

export default function StrategyLab() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [form] = Form.useForm();

  const onRun = async () => {
    const v = await form.validateFields().catch(() => null);
    if (!v) return;
    setLoading(true);
    try {
      const r = await api.backtest({
        strategy: v.strategy || 'ma_cross',
        symbol: v.symbol,
        start: v.start,
        end: v.end,
      });
      setResult(r as BacktestResult);
    } catch (e) {
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const equityOption = result?.equity_curve?.length
    ? {
        backgroundColor: 'transparent',
        grid: { left: 48, right: 24, top: 24, bottom: 40 },
        xAxis: { type: 'category', data: result.equity_curve.map((p) => p.date), axisLine: { lineStyle: { color: '#1f2937' } }, axisLabel: { color: '#9ca3af' } },
        yAxis: { type: 'value', axisLine: { show: false }, splitLine: { lineStyle: { color: '#1f2937' } }, axisLabel: { color: '#9ca3af' } },
        series: [{ type: 'line', data: result.equity_curve.map((p) => p.value), smooth: true, lineStyle: { color: '#10b981' }, areaStyle: { color: 'rgba(16,185,129,0.2)' } }],
      }
    : null;

  const heatmapOption = result?.monthly_heatmap?.length
    ? {
        backgroundColor: 'transparent',
        tooltip: {},
        grid: { left: 60, bottom: 40 },
        xAxis: { type: 'category', data: result.monthly_heatmap.map((p) => p.month), axisLabel: { color: '#9ca3af' } },
        yAxis: { type: 'value', name: '收益%', axisLabel: { color: '#9ca3af' } },
        visualMap: { min: -10, max: 10, inRange: { color: ['#ef4444', '#1f2937', '#10b981'] }, textStyle: { color: '#9ca3af' } },
        series: [{ type: 'bar', data: result.monthly_heatmap.map((p) => p.return) }],
      }
    : null;

  return (
    <div style={{ padding: 8 }}>
      <Card title="策略回测" style={{ background: '#111827', marginBottom: 16 }}>
        <Form form={form} layout="inline" onFinish={onRun} initialValues={{
          strategy: 'ma_cross',
          symbol: '000001.XSHE',
          start: new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
          end: new Date().toISOString().slice(0, 10),
        }}>
          <Form.Item name="strategy" label="策略" rules={[{ required: true }]}>
            <Select options={STRATEGY_OPTIONS} style={{ width: 180 }} placeholder="选择策略" />
          </Form.Item>
          <Form.Item name="symbol" label="标的" rules={[{ required: true }]}>
            <Input placeholder="000001.XSHE" style={{ width: 140 }} />
          </Form.Item>
          <Form.Item name="start" label="开始" rules={[{ required: true }]}>
            <Input type="date" style={{ width: 140 }} />
          </Form.Item>
          <Form.Item name="end" label="结束" rules={[{ required: true }]}>
            <Input type="date" style={{ width: 140 }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading}>运行回测</Button>
          </Form.Item>
        </Form>
      </Card>
      {result && (
        <>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Card size="small" title="总收益率" style={{ background: '#111827' }}>
                <span style={{ color: (result.total_return ?? 0) >= 0 ? '#10b981' : '#ef4444', fontSize: 20, fontWeight: 700 }}>
                  {((result.total_return ?? 0) * 100).toFixed(2)}%
                </span>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" title="最大回撤" style={{ background: '#111827' }}>
                <span style={{ color: '#ef4444', fontSize: 20, fontWeight: 700 }}>
                  {((result.max_drawdown ?? 0) * 100).toFixed(2)}%
                </span>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" title="夏普比率" style={{ background: '#111827' }}>
                <span style={{ color: '#e0e6ed', fontSize: 20, fontWeight: 700 }}>
                  {(result.sharpe_ratio ?? 0).toFixed(3)}
                </span>
              </Card>
            </Col>
          </Row>
          {equityOption && (
            <Card title="收益曲线" style={{ background: '#111827', marginBottom: 16 }}>
              <ReactECharts option={equityOption} style={{ height: 280 }} />
            </Card>
          )}
          {heatmapOption && (
            <Card title="月度收益" style={{ background: '#111827', marginBottom: 16 }}>
              <ReactECharts option={heatmapOption} style={{ height: 220 }} />
            </Card>
          )}
          {result.trades?.length > 0 && (
            <Card title="交易列表" style={{ background: '#111827' }}>
              <Table
                size="small"
                dataSource={result.trades}
                columns={[
                  { title: '日期', dataIndex: 'date', key: 'date', width: 120 },
                  { title: '类型', dataIndex: 'type', key: 'type', width: 80 },
                  { title: '价格', dataIndex: 'price', key: 'price', render: (v: number) => v?.toFixed(2) },
                  { title: '盈亏', dataIndex: 'pnl', key: 'pnl', render: (v: number) => v != null ? (v >= 0 ? '+' : '') + v.toFixed(2) : '-' },
                ]}
                pagination={{ pageSize: 10 }}
                rowKey={(_, i) => String(i)}
              />
            </Card>
          )}
        </>
      )}
    </div>
  );
}
