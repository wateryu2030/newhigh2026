'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { api, type SimulatedOrder, type SimulatedPosition } from '@/api/client';
import { useLang } from '@/context/LangContext';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { ErrorMessage } from '@/components/ErrorMessage';

const LOAD_TIMEOUT_MS = 8000;

export default function TradePage() {
  const { t } = useLang();
  const [mode, setMode] = useState<string | null>(null);
  const [orders, setOrders] = useState<SimulatedOrder[]>([]);
  const [positions, setPositions] = useState<SimulatedPosition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeoutHit, setTimeoutHit] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    setTimeoutHit(false);
    const timer = setTimeout(() => {
      setTimeoutHit(true);
      setError('加载超时，请确认 Gateway 已启动（http://127.0.0.1:8000）');
      setLoading(false);
      setMode('simulated');
      setOrders([]);
      setPositions([]);
    }, LOAD_TIMEOUT_MS);

    try {
      const [modeRes, ordersRes, positionsRes] = await Promise.all([
        api.executionMode().catch(() => ({ mode: 'simulated' })),
        api.simulatedOrders(50).catch(() => ({ orders: [] })),
        api.simulatedPositions(100).catch(() => ({ positions: [] })),
      ]);
      clearTimeout(timer);
      setMode(modeRes.mode ?? 'simulated');
      setOrders(ordersRes.orders ?? []);
      setPositions(positionsRes.positions ?? []);
    } catch (e) {
      clearTimeout(timer);
      setError(e instanceof Error ? e.message : '请求失败');
      setMode('simulated');
      setOrders([]);
      setPositions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading && !timeoutHit) {
    return (
      <div className="space-y-6 min-h-screen pb-24 md:pb-6">
        <h1 className="text-2xl font-bold text-white">{t('trade.title')}</h1>
        <div className="flex items-center gap-3 text-slate-400">
          <LoadingSpinner />
          <span>加载执行模式、持仓与订单…</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6 min-h-screen pb-24 md:pb-6">
        <h1 className="text-2xl font-bold text-white">{t('trade.title')}</h1>
        <ErrorMessage message={error} onRetry={fetchData} />
      </div>
    );
  }

  const hasAny = orders.length > 0 || positions.length > 0;

  return (
    <div className="space-y-6 min-h-screen pb-24 md:pb-6">
      <h1 className="text-2xl font-bold text-white">{t('trade.title')}</h1>

      {/* 执行模式 */}
      <div className="rounded-xl border border-slate-700 bg-slate-800/50 px-4 py-3">
        <span className="text-slate-400 text-sm">执行模式</span>
        <p className="text-lg font-medium text-white">
          {mode === 'live' ? '实盘' : '模拟盘'}
          {mode === 'simulated' && (
            <span className="ml-2 text-xs text-slate-500">（订单与持仓仅本地模拟，不真实下单）</span>
          )}
        </p>
      </div>

      {/* 当前持仓 */}
      <section>
        <h2 className="text-lg font-semibold text-white mb-2">当前持仓</h2>
        {positions.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-600 bg-slate-800/30 px-4 py-6 text-center text-slate-500 text-sm">
            暂无持仓。执行一次模拟步或等待策略信号触发生成订单后，此处会显示持仓。
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-700 bg-slate-800/50">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-600 text-slate-400">
                  <th className="p-3 font-medium">标的</th>
                  <th className="p-3 font-medium">方向</th>
                  <th className="p-3 font-medium">数量</th>
                  <th className="p-3 font-medium">成本价</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((p, i) => (
                  <tr key={`${p.code}-${i}`} className="border-b border-slate-700/50">
                    <td className="p-3 font-mono text-white">{p.code}</td>
                    <td className="p-3 text-slate-300">{p.side}</td>
                    <td className="p-3 text-slate-300">{p.qty}</td>
                    <td className="p-3 text-slate-300">{p.avg_price?.toLocaleString() ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* 最近订单 */}
      <section>
        <h2 className="text-lg font-semibold text-white mb-2">最近订单</h2>
        {orders.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-600 bg-slate-800/30 px-4 py-6 text-center text-slate-500 text-sm">
            暂无订单。可通过 API 执行 <code className="bg-slate-700 px-1 rounded">POST /api/simulated/step</code> 或由定时任务根据信号生成模拟订单。
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-700 bg-slate-800/50">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-600 text-slate-400">
                  <th className="p-3 font-medium">时间</th>
                  <th className="p-3 font-medium">标的</th>
                  <th className="p-3 font-medium">方向</th>
                  <th className="p-3 font-medium">数量</th>
                  <th className="p-3 font-medium">价格</th>
                  <th className="p-3 font-medium">状态</th>
                </tr>
              </thead>
              <tbody>
                {orders.slice(0, 30).map((o) => (
                  <tr key={o.id} className="border-b border-slate-700/50">
                    <td className="p-3 text-slate-300">
                      {o.created_at ? new Date(o.created_at).toLocaleString() : '—'}
                    </td>
                    <td className="p-3 font-mono text-white">{o.code}</td>
                    <td className={`p-3 font-medium ${o.side === 'BUY' ? 'text-emerald-400' : 'text-red-400'}`}>
                      {o.side}
                    </td>
                    <td className="p-3 text-slate-300">{o.qty}</td>
                    <td className="p-3 text-slate-300">{o.price?.toLocaleString() ?? '—'}</td>
                    <td className="p-3">
                      <span
                        className={
                          o.status === 'filled'
                            ? 'text-emerald-400'
                            : o.status === 'cancelled'
                            ? 'text-slate-500'
                            : 'text-amber-400'
                        }
                      >
                        {o.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* 无数据时的引导 */}
      {!hasAny && (
        <div className="rounded-xl border border-slate-600 bg-slate-800/30 p-4">
          <p className="text-slate-400 text-sm mb-2">更多信息</p>
          <ul className="text-sm text-slate-300 space-y-1">
            <li>
              · <Link href="/portfolio" className="text-fund-indigo hover:underline">组合页</Link> 可查看执行层资金曲线与总资产
            </li>
            <li>
              · <Link href="/ai-trading" className="text-fund-indigo hover:underline">AI 交易</Link> 可查看当前信号与情绪
            </li>
            <li>
              · 定时任务（方式一）每日跑扫描与信号后，执行模拟步会写入订单与持仓
            </li>
          </ul>
        </div>
      )}
    </div>
  );
}
