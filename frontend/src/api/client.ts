/** Gateway 地址：浏览器与 SSR 均请求此 origin，避免 404。可通过 NEXT_PUBLIC_API_TARGET 覆盖。 */
const API_BASE = process.env.NEXT_PUBLIC_API_TARGET || 'http://127.0.0.1:8000';

export async function apiGet<T>(path: string): Promise<T> {
  const url = path.startsWith('http') ? path : `${API_BASE}/api${path}`;
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) throw new Error(`API ${path}: ${res.status}`);
  return res.json();
}

export interface StockItem {
  ts_code: string;
  name: string;
  industry: string;
}

export interface MarketSummaryResponse {
  total_stocks: number;
  market: string;
  daily_bars?: number;
  date_min?: string | null;
  date_max?: string | null;
}

export const api = {
  baseURL: () => API_BASE + '/api',
  dashboard: () => apiGet<DashboardResponse>('/dashboard'),
  dataStatus: () => apiGet<DataStatusResponse>('/data/status'),
  marketSummary: () => apiGet<MarketSummaryResponse>('/market/summary'),
  stocks: (limit?: number) => apiGet<StockItem[]>(`/stocks${limit != null ? `?limit=${limit}` : ''}`),
  strategies: () => apiGet<StrategiesResponse>('/strategies'),
  strategiesMarket: (limit?: number) =>
    apiGet<StrategiesMarketResponse>(`/strategies/market${limit != null ? `?limit=${limit}` : ''}`),
  portfolio: () => apiGet<PortfolioResponse>('/portfolio/weights'),
  risk: () => apiGet<RiskResponse>('/risk/status'),
  market: (symbol?: string, interval?: string) =>
    apiGet<MarketResponse>(`/market/klines?symbol=${encodeURIComponent(symbol || 'BTCUSDT')}&interval=${interval || '1h'}`),
  ashareStocks: () => apiGet<AshareStocksResponse>('/market/ashare/stocks'),
  news: (symbol?: string, limit?: number) =>
    apiGet<NewsResponse>(`/news?limit=${limit ?? 100}${symbol ? `&symbol=${encodeURIComponent(symbol)}` : ''}`),
  trades: () => apiGet<TradesResponse>('/trades'),
  evolution: () => apiGet<EvolutionResponse>('/evolution'),
  alphaLab: () => apiGet<AlphaLabResponse>('/alpha-lab'),
  positions: () => apiGet<PositionsResponse>('/positions'),
  marketEmotion: () => apiGet<MarketEmotionResponse>('/market/emotion'),
  marketHotmoney: (limit?: number) => apiGet<HotmoneySeatItem[]>(`/market/hotmoney${limit != null ? `?limit=${limit}` : ''}`),
  marketMainThemes: (limit?: number) => apiGet<MainThemeItem[]>(`/market/main-themes${limit != null ? `?limit=${limit}` : ''}`),
  strategySignals: (limit?: number) => apiGet<TradeSignalItem[]>(`/strategy/signals${limit != null ? `?limit=${limit}` : ''}`),
  sniperCandidates: (limit?: number) => apiGet<SniperCandidateItem[]>(`/market/sniper-candidates${limit != null ? `?limit=${limit}` : ''}`),
  systemStatus: (limit?: number) =>
    apiGet<SystemStatusResponse>(`/system/status${limit != null ? `?limit=${limit}` : ''}`),
  aiDecision: () => apiGet<AiDecisionResponse>('/ai/decision'),
  backtestResult: (params?: { symbol?: string; start_date?: string; end_date?: string; signal_source?: string }) => {
    const p = params || {};
    const q = new URLSearchParams();
    if (p.symbol != null) q.set('symbol', p.symbol);
    if (p.start_date != null) q.set('start_date', p.start_date);
    if (p.end_date != null) q.set('end_date', p.end_date);
    if (p.signal_source != null) q.set('signal_source', p.signal_source);
    const query = q.toString();
    return apiGet<BacktestResultResponse>(`/backtest/result${query ? `?${query}` : ''}`);
  },
  executionEquityCurve: (limit?: number) =>
    apiGet<{ equity_curve: { date: string; value: number }[] }>(
      `/execution/equity_curve${limit != null ? `?limit=${limit}` : ''}`
    ),
  executionMode: () => apiGet<{ mode: string; error?: string }>('/execution/mode'),
  ensureStocks: () =>
    fetch(`${API_BASE}/api/data/ensure-stocks`, { method: 'POST', cache: 'no-store' }).then((r) => r.json() as Promise<{ ok: boolean; rows: number; error?: string }>),
  simulatedOrders: (limit?: number, status?: string) => {
    const q = new URLSearchParams();
    if (limit != null) q.set('limit', String(limit));
    if (status) q.set('status', status);
    const query = q.toString();
    return apiGet<{ orders: SimulatedOrder[] }>(`/simulated/orders${query ? `?${query}` : ''}`);
  },
  simulatedPositions: (limit?: number) =>
    apiGet<{ positions: SimulatedPosition[] }>(`/simulated/positions${limit != null ? `?limit=${limit}` : ''}`),
  // OpenClaw 进化与 Skill 统计（系统监控页）
  triggerEvolution: (taskType: string = 'strategy_generation', populationLimit?: number, symbol?: string) => {
    const params = new URLSearchParams({ task_type: taskType });
    if (populationLimit != null) params.set('population_limit', String(populationLimit));
    if (symbol) params.set('symbol', symbol);
    return fetch(`${API_BASE}/api/evolution/trigger?${params}`, { method: 'POST', cache: 'no-store' }).then(
      (r) => r.json() as Promise<{ task_id: string; status: string }>
    );
  },
  getEvolutionStatus: (taskId: string) =>
    apiGet<{ task_id: string; status: string; result: unknown }>(`/evolution/status/${encodeURIComponent(taskId)}`),
  getEvolutionTasks: (limit?: number) =>
    apiGet<{ tasks: EvolutionTaskItem[] }>(`/evolution/tasks${limit != null ? `?limit=${limit}` : ''}`),
  getSkillStats: () =>
    apiGet<{ call_count: number; last_call_time: string | null }>('/skill/stats'),
};

export interface EvolutionTaskItem {
  id: string;
  status: string;
  result: unknown;
  created_at: string | null;
}

export interface SimulatedOrder {
  id: number;
  code: string;
  side: string;
  qty: number;
  price: number;
  status: string;
  created_at: string;
  filled_at?: string | null;
}

export interface SimulatedPosition {
  code: string;
  side: string;
  qty: number;
  avg_price: number;
  updated_at?: string;
}

export interface AiDecisionResponse {
  signal: 'BUY' | 'SELL' | 'HOLD';
  reason: string;
  factors: string[];
}

export interface BacktestResultResponse {
  symbol: string;
  start_date?: string;
  end_date?: string;
  signal_source?: string;
  equity_curve: { date: string; value: number }[];
  sharpe_ratio: number | null;
  max_drawdown: number | null;
  total_return: number | null;
  win_rate_pct: number | null;
  profit_factor: number | null;
  total_profit: number | null;
  trade_count: number | null;
  error: string | null;
}

export interface SystemStatusResponse {
  data_pipeline: 'running' | 'error' | 'idle';
  scanner: 'running' | 'error' | 'idle';
  ai_models: 'running' | 'error' | 'idle';
  strategy_engine: 'running' | 'error' | 'idle';
  last_update: string | null;
  evolution_task_id?: string | null;
  evolution_status?: string | null;
  skill_call_count?: number;
  skill_last_call_time?: string | null;
  history: {
    data_status?: string;
    scanner_status?: string;
    ai_status?: string;
    strategy_status?: string;
    snapshot_time?: string;
  }[];
}

export interface SniperCandidateItem {
  code: string;
  theme: string;
  sniper_score: number;
  confidence: number;
  snapshot_time?: string;
}

export interface MarketEmotionResponse {
  state: string;
  stage: string;
  limit_up_count: number;
  score: number;
  trade_date?: string | null;
  max_height?: number;
  market_volume?: number;
}

export interface HotmoneySeatItem {
  seat_name: string;
  trade_count: number;
  win_rate: number;
  avg_return: number;
  snapshot_time?: string;
}

export interface MainThemeItem {
  sector: string;
  total_volume: number;
  rank: number;
  snapshot_time?: string;
}

export interface TradeSignalItem {
  code: string;
  signal: string;
  confidence: number;
  target_price: number;
  stop_loss: number;
  strategy_id?: string;
  signal_score?: number;
  snapshot_time?: string;
}

export interface DashboardResponse {
  total_equity: number;
  daily_return_pct: number;
  sharpe_ratio: number;
  max_drawdown_pct: number;
  equity_curve: number[];
  top_strategies: { id: string; name: string; return_pct: number }[];
  ai_generated_today: number;
  strategies_alive: number;
  strategies_live: number;
}

export interface StrategiesResponse {
  strategies: { id: string; name: string }[];
}

export interface StrategyMarketItem {
  id: string;
  name: string;
  return_pct: number | null;
  sharpe_ratio: number | null;
  max_drawdown: number | null;
  status: string;
}

export interface StrategiesMarketResponse {
  items: StrategyMarketItem[];
}

export interface PortfolioResponse {
  weights: Record<string, number>;
  capital: number;
}

export interface RiskResponse {
  drawdown_ok: boolean;
  exposure_ok: boolean;
  volatility_ok: boolean;
}

export interface MarketResponse {
  symbol: string;
  interval: string;
  limit: number;
  data: { t: string; o: number; h: number; l: number; c: number; close?: number; v: number }[];
}

export interface AshareStocksResponse {
  stocks: { symbol: string; name: string }[];
  source: string | null;
}

export interface NewsItem {
  symbol?: string;
  source_site?: string;
  source?: string;
  title?: string;
  content?: string;
  url?: string;
  keyword?: string;
  tag?: string;
  publish_time?: string;
  sentiment_score?: number;
  sentiment_label?: string;
}

export interface NewsResponse {
  news: NewsItem[];
  source: string | null;
  sentiment?: { count: number; avg_score?: number; positive_ratio?: number } | null;
}

export interface DataStatusResponse {
  ok: boolean;
  source: string | null;
  stocks: number;
  daily_bars: number;
  date_min: string | null;
  date_max: string | null;
}

export interface TradesResponse {
  trades: { time: string; strategy: string; symbol: string; side: string; qty: number; price: number }[];
}

export interface EvolutionResponse {
  current_generation: number;
  best_strategy: { id: string; sharpe: number; return_pct: number };
  generations: { gen: number }[];
}

export interface AlphaLabResponse {
  generated_today: number;
  passed_backtest: number;
  passed_risk: number;
  deployed: number;
}

export interface PositionsResponse {
  positions: unknown[];
}
