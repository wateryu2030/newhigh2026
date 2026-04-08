'use client';

import { useState, useEffect } from 'react';
import { api, getApiBase } from '@/api/client';

interface StockBasic {
  ts_code: string;
  symbol: string;
  name: string;
  industry: string;
  list_date: string;
}

interface DailyPrice {
  trade_date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  vol: number;
  pct_chg: number;
}

interface FinanceIndicator {
  ts_code: string;
  end_date: string;
  pe: number;
  pb: number;
  roe: number;
  profit_rate: number;
  gross_profit_margin: number;
  net_profit_margin: number;
  total_revenue: number;
  net_profit: number;
}

interface LimitUpDownItem {
  ts_code: string;
  trade_date: string;
  name: string;
  close: number;
  pct_chg: number;
  up_down: string;
  limit_times: number;
}

interface IndustryRankingItem {
  ts_code: string;
  trade_date: string;
  close: number;
  pct_chg: number;
  vol: number;
}

export default function AShareDemoPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stockBasic, setStockBasic] = useState<StockBasic[]>([]);
  const [dailyPrice, setDailyPrice] = useState<DailyPrice[]>([]);
  const [financeIndicator, setFinanceIndicator] = useState<FinanceIndicator | null>(null);
  const [limitUpDown, setLimitUpDown] = useState<LimitUpDownItem[]>([]);
  const [industryRanking, setIndustryRanking] = useState<IndustryRankingItem[]>([]);
  const [marketOverview, setMarketOverview] = useState<any>(null);

  const testAllApis = async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. 测试股票基本信息
      console.log('测试股票基本信息API...');
      const basicRes = await fetch(`${getApiBase()}/api/skill/ashare/stock-basic?name=茅台`);
      const basicData = await basicRes.json();
      if (basicData.data) {
        setStockBasic(basicData.data);
      }

      // 2. 测试日线行情
      console.log('测试日线行情API...');
      const dailyRes = await fetch(`${getApiBase()}/api/skill/ashare/daily?ts_code=600519.SH&start_date=20240301`);
      const dailyData = await dailyRes.json();
      if (dailyData.data) {
        setDailyPrice(dailyData.data.slice(-5)); // 只显示最近5天
      }

      // 3. 测试财务指标
      console.log('测试财务指标API...');
      const financeRes = await fetch(`${getApiBase()}/api/skill/ashare/finance-indicator?ts_code=600519.SH`);
      const financeData = await financeRes.json();
      if (financeData.data) {
        setFinanceIndicator(financeData.data);
      }

      // 4. 测试涨停跌停
      console.log('测试涨停跌停API...');
      const limitRes = await fetch(`${getApiBase()}/api/skill/ashare/limit-up-down`);
      const limitData = await limitRes.json();
      if (limitData.data) {
        setLimitUpDown(limitData.data.slice(0, 10)); // 只显示前10个
      }

      // 5. 测试行业排行
      console.log('测试行业排行API...');
      const industryRes = await fetch(`${getApiBase()}/api/skill/ashare/industry-ranking?top_n=10`);
      const industryData = await industryRes.json();
      if (industryData.data) {
        setIndustryRanking(industryData.data);
      }

      // 6. 测试市场概览
      console.log('测试市场概览API...');
      const marketRes = await fetch(`${getApiBase()}/api/skill/ashare/market-overview`);
      const marketData = await marketRes.json();
      if (marketData.data) {
        setMarketOverview(marketData.data);
      }

    } catch (err: any) {
      setError(err.message || 'API测试失败');
      console.error('API测试错误:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // 页面加载时自动测试
    testAllApis();
  }, []);

  return (
    <div className="space-y-8 p-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-on-surface">A股数据Skill演示</h1>
          <p className="text-text-secondary mt-2">基于Tushare的A股数据查询功能演示</p>
        </div>
        <button
          onClick={testAllApis}
          disabled={loading}
          className="px-4 py-2 bg-primary-fixed hover:opacity-90 rounded-lg text-on-warm-fill font-medium disabled:opacity-50"
        >
          {loading ? '测试中...' : '重新测试所有API'}
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-[color:var(--color-error-banner-border)] bg-[color:var(--color-error-banner-bg)] p-4">
          <h3 className="font-medium text-accent-red">错误</h3>
          <p className="text-text-primary mt-1">{error}</p>
          <p className="text-text-dim text-sm mt-2">
            请确保Gateway已启动：<code className="bg-surface-container-high px-2 py-1 rounded">uvicorn gateway.app:app --host 127.0.0.1 --port 8000</code>
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 股票基本信息 */}
        <div className="card">
          <h2 className="text-xl font-semibold text-on-surface mb-4">股票基本信息</h2>
          {stockBasic.length > 0 ? (
            <div className="space-y-3">
              {stockBasic.map((stock) => (
                <div key={stock.ts_code} className="p-3 bg-surface-container-high/50 rounded-lg">
                  <div className="flex justify-between items-center">
                    <div>
                      <h3 className="font-medium text-on-surface">{stock.name}</h3>
                      <p className="text-text-secondary text-sm">{stock.ts_code}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-text-secondary text-sm">行业</p>
                      <p className="text-on-surface">{stock.industry || '—'}</p>
                    </div>
                  </div>
                  <div className="mt-2 text-sm text-text-dim">
                    上市日期：{stock.list_date}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-text-dim">暂无数据</p>
          )}
        </div>

        {/* 财务指标 */}
        <div className="card">
          <h2 className="text-xl font-semibold text-on-surface mb-4">财务指标（贵州茅台）</h2>
          {financeIndicator ? (
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-surface-container-high/50 rounded-lg">
                <p className="text-text-secondary text-sm">市盈率 (PE)</p>
                <p className="text-2xl font-bold text-on-surface">{financeIndicator.pe}</p>
              </div>
              <div className="p-3 bg-surface-container-high/50 rounded-lg">
                <p className="text-text-secondary text-sm">市净率 (PB)</p>
                <p className="text-2xl font-bold text-on-surface">{financeIndicator.pb}</p>
              </div>
              <div className="p-3 bg-surface-container-high/50 rounded-lg">
                <p className="text-text-secondary text-sm">净资产收益率 (ROE)</p>
                <p className="text-2xl font-bold text-on-surface">{financeIndicator.roe}%</p>
              </div>
              <div className="p-3 bg-surface-container-high/50 rounded-lg">
                <p className="text-text-secondary text-sm">毛利率</p>
                <p className="text-2xl font-bold text-on-surface">{financeIndicator.gross_profit_margin}%</p>
              </div>
              <div className="col-span-2 p-3 bg-surface-container-high/50 rounded-lg">
                <p className="text-text-secondary text-sm">报告期</p>
                <p className="text-on-surface">{financeIndicator.end_date}</p>
              </div>
            </div>
          ) : (
            <p className="text-text-dim">暂无数据</p>
          )}
        </div>

        {/* 日线行情 */}
        <div className="card">
          <h2 className="text-xl font-semibold text-on-surface mb-4">日线行情（最近5天）</h2>
          {dailyPrice.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-text-secondary border-b border-card-border">
                    <th className="py-2 pr-4 text-left">日期</th>
                    <th className="py-2 pr-4 text-left">开盘</th>
                    <th className="py-2 pr-4 text-left">收盘</th>
                    <th className="py-2 pr-4 text-left">涨跌幅</th>
                    <th className="py-2 text-left">成交量</th>
                  </tr>
                </thead>
                <tbody>
                  {dailyPrice.map((day, index) => (
                    <tr key={index} className="border-b border-[color:var(--color-border-subtle)]">
                      <td className="py-2 pr-4 text-text-primary">{day.trade_date}</td>
                      <td className="py-2 pr-4 text-on-surface">{day.open}</td>
                      <td className="py-2 pr-4 text-on-surface">{day.close}</td>
                      <td className={`py-2 pr-4 ${day.pct_chg >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                        {day.pct_chg >= 0 ? '+' : ''}{day.pct_chg}%
                      </td>
                      <td className="py-2 text-text-primary">{(day.vol / 10000).toFixed(0)}万手</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-text-dim">暂无数据</p>
          )}
        </div>

        {/* 涨停跌停 */}
        <div className="card">
          <h2 className="text-xl font-semibold text-on-surface mb-4">涨停/跌停股票</h2>
          {limitUpDown.length > 0 ? (
            <div className="space-y-2">
              {limitUpDown.map((item, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-surface-container-high/50 rounded-lg">
                  <div>
                    <h3 className="font-medium text-on-surface">{item.name}</h3>
                    <p className="text-text-secondary text-sm">{item.ts_code}</p>
                  </div>
                  <div className="text-right">
                    <span className={`px-2 py-1 rounded text-sm ${
                      item.up_down === 'U'
                        ? 'bg-[color:var(--color-success-alpha-15)] text-accent-green'
                        : 'bg-accent-red/15 text-accent-red'
                    }`}>
                      {item.up_down === 'U' ? '涨停' : '跌停'}
                    </span>
                    <p className="text-text-primary text-sm mt-1">{item.close}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-text-dim">暂无数据</p>
          )}
        </div>

        {/* 行业排行 */}
        <div className="card">
          <h2 className="text-xl font-semibold text-on-surface mb-4">行业涨幅排行</h2>
          {industryRanking.length > 0 ? (
            <div className="space-y-2">
              {industryRanking.map((industry, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-surface-container-high/50 rounded-lg">
                  <div>
                    <h3 className="font-medium text-on-surface">{industry.ts_code}</h3>
                    <p className="text-text-secondary text-sm">{industry.trade_date}</p>
                  </div>
                  <div className="text-right">
                    <p className={`text-lg font-bold ${industry.pct_chg >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                      {industry.pct_chg >= 0 ? '+' : ''}{industry.pct_chg}%
                    </p>
                    <p className="text-text-secondary text-sm">收盘: {industry.close}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-text-dim">暂无数据</p>
          )}
        </div>

        {/* 市场概览 */}
        <div className="card">
          <h2 className="text-xl font-semibold text-on-surface mb-4">市场概览</h2>
          {marketOverview ? (
            <div className="space-y-4">
              <div>
                <h3 className="text-text-secondary text-sm mb-2">主要指数</h3>
                <div className="space-y-2">
                  {marketOverview.indices?.map((index: any, i: number) => (
                    <div key={i} className="flex justify-between items-center p-2 bg-surface-container-high/50 rounded">
                      <span className="text-on-surface">{index.ts_code}</span>
                      <span className={`${index.pct_chg >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                        {index.close} ({index.pct_chg >= 0 ? '+' : ''}{index.pct_chg}%)
                      </span>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <h3 className="text-text-secondary text-sm mb-2">市场统计</h3>
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-surface-container-high/50 rounded">
                    <p className="text-text-secondary text-sm">总市值</p>
                    <p className="text-xl font-bold text-on-surface">{marketOverview.market_stats?.total_market_cap}万亿</p>
                  </div>
                  <div className="p-3 bg-surface-container-high/50 rounded">
                    <p className="text-text-secondary text-sm">流通市值</p>
                    <p className="text-xl font-bold text-on-surface">{marketOverview.market_stats?.circ_market_cap}万亿</p>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-text-dim">暂无数据</p>
          )}
        </div>
      </div>

      <div className="card bg-card-bg/80">
        <h2 className="text-lg font-semibold text-on-surface mb-4">API使用说明</h2>
        <div className="space-y-3 text-sm">
          <div>
            <h3 className="text-text-primary font-medium">可用API端点：</h3>
            <ul className="list-disc list-inside text-text-secondary mt-2 space-y-1">
              <li><code>GET /api/skill/ashare/stock-basic?name=茅台</code> - 股票基本信息</li>
              <li><code>GET /api/skill/ashare/daily?ts_code=600519.SH</code> - 日线行情</li>
              <li><code>GET /api/skill/ashare/finance-indicator?ts_code=600519.SH</code> - 财务指标</li>
              <li><code>GET /api/skill/ashare/limit-up-down</code> - 涨停跌停</li>
              <li><code>GET /api/skill/ashare/industry-ranking?top_n=10</code> - 行业排行</li>
              <li><code>GET /api/skill/ashare/market-overview</code> - 市场概览</li>
            </ul>
          </div>
          <div>
            <h3 className="text-text-primary font-medium">启动Gateway：</h3>
            <code className="block bg-terminal-bg p-3 rounded mt-2 text-text-primary">
              cd /Users/apple/ahope/newhigh && source .venv/bin/activate<br />
              uvicorn gateway.app:app --host 127.0.0.1 --port 8000
            </code>
          </div>
        </div>
      </div>
    </div>
  );
}