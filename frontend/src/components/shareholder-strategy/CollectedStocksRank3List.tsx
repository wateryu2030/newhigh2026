'use client';

import { useState, useEffect } from 'react';
import { api, type CollectedStocksAllRanksItem } from '@/api/client';

export function CollectedStocksRank3List() {
  const [data, setData] = useState<CollectedStocksAllRanksItem[]>([]);
  const [reportDate, setReportDate] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api
      .collectedStocksAllRanks(200)
      .then((res) => {
        if (res.ok && res.data) {
          setData(res.data);
          setReportDate(res.report_date);
        } else {
          setData([]);
        }
      })
      .catch((err) => {
        setError(err?.message || '加载失败');
        setData([]);
      })
      .finally(() => setLoading(false));
  }, []);

  const stockCount = new Set(data.map((r) => r.stock_code)).size;

  if (loading) {
    return (
      <div className="card">
        <h3 className="mb-3 text-sm font-medium text-slate-300">已采集股票 · 十大股东</h3>
        <div className="py-8 text-center text-slate-500">加载中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <h3 className="mb-3 text-sm font-medium text-slate-300">已采集股票 · 十大股东</h3>
        <div className="py-4 text-center text-amber-400">{error}</div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="card">
        <h3 className="mb-3 text-sm font-medium text-slate-300">已采集股票 · 十大股东</h3>
        <div className="py-4 text-center text-slate-500">暂无数据</div>
      </div>
    );
  }

  return (
    <div className="card space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-slate-300">
          已采集股票 · 十大股东
          {reportDate && (
            <span className="ml-2 text-xs text-slate-500">报告期 {reportDate}</span>
          )}
        </h3>
        <span className="text-xs text-slate-500">{stockCount} 只 · {data.length} 条</span>
      </div>
      <div className="max-h-80 overflow-auto rounded border border-slate-600">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-slate-800">
            <tr className="text-left text-slate-400">
              <th className="px-3 py-2 font-medium">代码</th>
              <th className="px-3 py-2 font-medium">名称</th>
              <th className="px-3 py-2 font-medium w-8">排名</th>
              <th className="px-3 py-2 font-medium">股东名称</th>
              <th className="px-3 py-2 font-medium">类型</th>
              <th className="px-3 py-2 font-medium text-right">持股(万股)</th>
              <th className="px-3 py-2 font-medium text-right">流通比%</th>
            </tr>
          </thead>
          <tbody>
            {data.map((row, i) => (
              <tr
                key={`${row.stock_code}-${row.rank}-${i}`}
                className="border-t border-slate-700/50 hover:bg-slate-800/50"
              >
                <td className="px-3 py-2 font-mono text-slate-300">{row.stock_code}</td>
                <td className="px-3 py-2 text-white">{row.stock_name}</td>
                <td className="px-3 py-2 text-slate-400">{row.rank}</td>
                <td className="px-3 py-2 text-slate-300 max-w-[140px] truncate" title={row.shareholder_name}>
                  {row.shareholder_name || '—'}
                </td>
                <td className="px-3 py-2 text-slate-500 text-xs">{row.shareholder_type || '—'}</td>
                <td className="px-3 py-2 text-right text-slate-400">
                  {row.share_count > 0 ? (row.share_count / 10000).toFixed(2) : '—'}
                </td>
                <td className="px-3 py-2 text-right text-slate-400">
                  {row.share_ratio > 0 ? row.share_ratio.toFixed(2) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
