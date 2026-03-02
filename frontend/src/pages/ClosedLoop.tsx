/**
 * 机构级闭环：情绪回测验证 / 龙虎榜胜率统计 / 每周报告
 * 对应 docs/INSTITUTIONAL_CLOSED_LOOP.md
 */
import { useState, useEffect } from 'react';
import { Card, Tabs, Button, Spin, Alert, Table, Tag, Space, Typography } from 'antd';
import { PlayCircleOutlined, ReloadOutlined } from '@ant-design/icons';
import { api, type ClosedLoopEmotionReport, type ClosedLoopLHBReport, type ClosedLoopWeeklyReport } from '../api/client';

const { Title, Text } = Typography;

type TabKey = 'emotion' | 'lhb' | 'weekly';

export default function ClosedLoop() {
  const [activeTab, setActiveTab] = useState<TabKey>('emotion');
  const [emotionReport, setEmotionReport] = useState<ClosedLoopEmotionReport | null | undefined>(undefined);
  const [lhbReport, setLhbReport] = useState<ClosedLoopLHBReport | null | undefined>(undefined);
  const [weeklyReport, setWeeklyReport] = useState<ClosedLoopWeeklyReport | null | undefined>(undefined);
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<Record<string, string>>({});

  const loadEmotion = async () => {
    setLoading((l) => ({ ...l, emotion: true }));
    setError((e) => ({ ...e, emotion: '' }));
    try {
      const res = await api.closedLoop.emotionReport();
      setEmotionReport(res.report ?? null);
    } catch (err) {
      setError((e) => ({ ...e, emotion: err instanceof Error ? err.message : String(err) }));
      setEmotionReport(null);
    } finally {
      setLoading((l) => ({ ...l, emotion: false }));
    }
  };

  const loadLhb = async () => {
    setLoading((l) => ({ ...l, lhb: true }));
    setError((e) => ({ ...e, lhb: '' }));
    try {
      const res = await api.closedLoop.lhbReport();
      setLhbReport(res.report ?? null);
    } catch (err) {
      setError((e) => ({ ...e, lhb: err instanceof Error ? err.message : String(err) }));
      setLhbReport(null);
    } finally {
      setLoading((l) => ({ ...l, lhb: false }));
    }
  };

  const loadWeekly = async () => {
    setLoading((l) => ({ ...l, weekly: true }));
    setError((e) => ({ ...e, weekly: '' }));
    try {
      const res = await api.closedLoop.weeklyReport();
      setWeeklyReport(res.report ?? null);
    } catch (err) {
      setError((e) => ({ ...e, weekly: err instanceof Error ? err.message : String(err) }));
      setWeeklyReport(null);
    } finally {
      setLoading((l) => ({ ...l, weekly: false }));
    }
  };

  const runEmotion = async () => {
    setLoading((l) => ({ ...l, runEmotion: true }));
    setError((e) => ({ ...e, runEmotion: '' }));
    try {
      const res = await api.closedLoop.runEmotion();
      if (res.success && res.report) {
        setEmotionReport(res.report);
      } else {
        setError((e) => ({ ...e, runEmotion: res.error || '执行失败' }));
      }
    } catch (err) {
      setError((e) => ({ ...e, runEmotion: err instanceof Error ? err.message : String(err) }));
    } finally {
      setLoading((l) => ({ ...l, runEmotion: false }));
    }
  };

  const runLhb = async () => {
    setLoading((l) => ({ ...l, runLhb: true }));
    setError((e) => ({ ...e, runLhb: '' }));
    try {
      const res = await api.closedLoop.runLhb();
      if (res.success && res.report) {
        setLhbReport(res.report);
      } else {
        setError((e) => ({ ...e, runLhb: res.error || '执行失败' }));
      }
    } catch (err) {
      setError((e) => ({ ...e, runLhb: err instanceof Error ? err.message : String(err) }));
    } finally {
      setLoading((l) => ({ ...l, runLhb: false }));
    }
  };

  const runWeekly = async () => {
    setLoading((l) => ({ ...l, runWeekly: true }));
    setError((e) => ({ ...e, runWeekly: '' }));
    try {
      const res = await api.closedLoop.runWeekly();
      if (res.success && res.report) {
        setWeeklyReport(res.report);
      } else {
        setError((e) => ({ ...e, runWeekly: res.error || '执行失败' }));
      }
    } catch (err) {
      setError((e) => ({ ...e, runWeekly: err instanceof Error ? err.message : String(err) }));
    } finally {
      setLoading((l) => ({ ...l, runWeekly: false }));
    }
  };

  useEffect(() => {
    if (activeTab === 'emotion' && emotionReport === undefined) loadEmotion();
    if (activeTab === 'lhb' && lhbReport === undefined) loadLhb();
    if (activeTab === 'weekly' && weeklyReport === undefined) loadWeekly();
  }, [activeTab]);

  const emotionColumns = [
    { title: '情绪阶段', dataIndex: 'emotion', key: 'emotion', width: 100 },
    { title: '胜率', dataIndex: 'win_rate', key: 'win_rate', render: (v: number) => (v != null ? (v * 100).toFixed(2) + '%' : '—') },
    { title: '平均收益', dataIndex: 'mean_return', key: 'mean_return', render: (v: number) => (v != null ? (v * 100).toFixed(4) + '%' : '—') },
    { title: '盈亏比', dataIndex: 'profit_factor', key: 'profit_factor', render: (v: number) => (v != null ? v.toFixed(2) : '—') },
    { title: '最大回撤', dataIndex: 'max_drawdown', key: 'max_drawdown', render: (v: number) => (v != null ? (v * 100).toFixed(2) + '%' : '—') },
    { title: '夏普', dataIndex: 'sharpe', key: 'sharpe', render: (v: number) => (v != null ? v.toFixed(2) : '—') },
    { title: '交易日数', dataIndex: 'count', key: 'count', width: 90 },
  ];

  const lhbRankColumns = [
    { title: '排名', dataIndex: 'rank', key: 'rank', width: 60, render: (_: unknown, __: unknown, i: number) => i + 1 },
    { title: '席位', dataIndex: 'seat', key: 'seat' },
    { title: '+5日胜率', dataIndex: 'win_rate_5d', key: 'win_rate_5d', render: (v: number) => (v != null ? (v * 100).toFixed(2) + '%' : '—') },
  ];

  return (
    <div style={{ padding: 16, background: '#0b0f17', minHeight: 'calc(100vh - 100px)' }}>
      <Title level={4} style={{ color: '#22c55e', marginBottom: 16 }}>
        机构级闭环：自我验证 · 胜率统计 · 持续优化
      </Title>
      <Card style={{ background: '#1a2332', border: '1px solid #2d3a4f' }}>
        <Tabs
          activeKey={activeTab}
          onChange={(k) => setActiveTab(k as TabKey)}
          items={[
            {
              key: 'emotion',
              label: '情绪周期回测',
              children: (
                <Space direction="vertical" style={{ width: '100%' }} size="middle">
                  <Space>
                    <Button type="primary" icon={<PlayCircleOutlined />} loading={loading.runEmotion} onClick={runEmotion}>
                      执行情绪回测
                    </Button>
                    <Button icon={<ReloadOutlined />} loading={loading.emotion} onClick={loadEmotion}>
                      刷新报告
                    </Button>
                  </Space>
                  {error.runEmotion && <Alert type="error" message={error.runEmotion} />}
                  {loading.emotion || loading.runEmotion ? (
                    <Spin tip="加载中..." />
                  ) : emotionReport ? (
                    <>
                      {emotionReport.summary && (
                        <div>
                          <Text strong style={{ color: '#94a3b8' }}>全市场汇总：</Text>
                          <Text style={{ marginLeft: 8 }}>
                            胜率 {(emotionReport.summary.win_rate * 100).toFixed(2)}% · 最大回撤 {(emotionReport.summary.max_drawdown != null ? (emotionReport.summary.max_drawdown * 100).toFixed(2) : '—')}% · 夏普 {emotionReport.summary.sharpe?.toFixed(2) ?? '—'}
                          </Text>
                        </div>
                      )}
                      <Table
                        size="small"
                        dataSource={emotionReport.by_emotion ? Object.entries(emotionReport.by_emotion).map(([emotion, v]) => ({ key: emotion, emotion, ...v })) : []}
                        columns={emotionColumns}
                        pagination={false}
                        style={{ background: 'transparent' }}
                      />
                    </>
                  ) : (
                    <Alert type="info" message="暂无报告，点击「执行情绪回测」生成（需数据库有日线）" />
                  )}
                </Space>
              ),
            },
            {
              key: 'lhb',
              label: '龙虎榜胜率',
              children: (
                <Space direction="vertical" style={{ width: '100%' }} size="middle">
                  <Space>
                    <Button type="primary" icon={<PlayCircleOutlined />} loading={loading.runLhb} onClick={runLhb}>
                      执行龙虎榜统计
                    </Button>
                    <Button icon={<ReloadOutlined />} loading={loading.lhb} onClick={loadLhb}>
                      刷新报告
                    </Button>
                  </Space>
                  {error.runLhb && <Alert type="error" message={error.runLhb} />}
                  {loading.lhb || loading.runLhb ? (
                    <Spin tip="加载中..." />
                  ) : lhbReport ? (
                    <>
                      <div>
                        <Text strong style={{ color: '#94a3b8' }}>统计区间：</Text>
                        <Text style={{ marginLeft: 8 }}>{lhbReport.start_date} ~ {lhbReport.end_date}</Text>
                        <Text style={{ marginLeft: 16 }}>记录数：{lhbReport.total_records ?? 0}</Text>
                      </div>
                      <Table
                        size="small"
                        rowKey="seat"
                        dataSource={lhbReport.ranking ?? []}
                        columns={lhbRankColumns}
                        pagination={{ pageSize: 15 }}
                        style={{ background: 'transparent' }}
                      />
                    </>
                  ) : (
                    <Alert type="info" message="暂无报告，点击「执行龙虎榜统计」生成（会拉取近2年龙虎榜）" />
                  )}
                </Space>
              ),
            },
            {
              key: 'weekly',
              label: '每周报告',
              children: (
                <Space direction="vertical" style={{ width: '100%' }} size="middle">
                  <Space>
                    <Button type="primary" icon={<PlayCircleOutlined />} loading={loading.runWeekly} onClick={runWeekly}>
                      执行每周闭环
                    </Button>
                    <Button icon={<ReloadOutlined />} loading={loading.weekly} onClick={loadWeekly}>
                      刷新报告
                    </Button>
                  </Space>
                  {error.runWeekly && <Alert type="error" message={error.runWeekly} />}
                  {loading.weekly || loading.runWeekly ? (
                    <Spin tip="加载中..." />
                  ) : weeklyReport ? (
                    <Card size="small" style={{ background: '#0f1419', border: '1px solid #2d3a4f' }}>
                      <p><Text strong>生成时间：</Text>{weeklyReport.generated_at ?? '—'}</p>
                      <p><Text strong>区间：</Text>{weeklyReport.start_date} ~ {weeklyReport.end_date}</p>
                      {weeklyReport.emotion_backtest_error && <Alert type="warning" message={`情绪回测：${weeklyReport.emotion_backtest_error}`} style={{ marginTop: 8 }} />}
                      {weeklyReport.lhb_statistics_error && <Alert type="warning" message={`龙虎榜统计：${weeklyReport.lhb_statistics_error}`} style={{ marginTop: 8 }} />}
                      {weeklyReport.lhb_statistics?.ranking_sample && weeklyReport.lhb_statistics.ranking_sample.length > 0 && (
                        <p style={{ marginTop: 8 }}>
                          <Text strong>龙虎榜排名示例：</Text>
                          {weeklyReport.lhb_statistics.ranking_sample.slice(0, 5).map((r, i) => (
                            <Tag key={i} style={{ marginLeft: 4 }}>{r.seat} {(r.win_rate_5d != null ? (r.win_rate_5d * 100).toFixed(1) : '—')}%</Tag>
                          ))}
                        </p>
                      )}
                    </Card>
                  ) : (
                    <Alert type="info" message="暂无报告，点击「执行每周闭环」生成（情绪回测 + 龙虎榜统计）" />
                  )}
                </Space>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
}
