const BASE = '/api';

async function get<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = path.startsWith('http') ? new URL(path) : new URL(path, window.location.origin);
  if (params) Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const url = path.startsWith(BASE) ? path : BASE + path;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export const api = {
  kline: (symbol: string, start: string, end: string) =>
    get<KlineBar[]>(BASE + '/kline', { symbol, start, end }),

  signals: (symbol: string, strategy?: string) =>
    get<{ signals: import('../types').Signal[] }>(BASE + '/signals', strategy ? { symbol, strategy } : { symbol }),

  aiScore: (symbol: string) =>
    get<import('../types').AiScore>(BASE + '/ai_score', { symbol }),

  backtest: (params: { strategy: string; symbol: string; start: string; end: string }) =>
    post<import('../types').BacktestResult>('/backtest', params),

  scan: (mode?: string) =>
    get<{ results: import('../types').ScanItem[] }>(BASE + '/scan', mode ? { mode } : {}),

  stocks: () =>
    get<{ stocks: { order_book_id: string; symbol: string; name: string }[] }>(BASE + '/stocks'),

  rl: {
    train: (body: { symbol?: string; start_date?: string; end_date?: string; total_timesteps?: number }) =>
      post<{ success: boolean; model_path?: string; total_timesteps?: number; error?: string }>(BASE + '/rl/train', body),
    performance: (params?: { symbol?: string; start_date?: string; end_date?: string }) =>
      get<RLPerformanceResponse>(BASE + '/rl/performance', params || {}),
    decision: (params: { symbol: string; position_pct?: number }) =>
      get<RLDecisionResponse>(BASE + '/rl/decision', { symbol: params.symbol, position_pct: String(params.position_pct ?? 0) }),
  },
};

export type KlineBar = import('../types').KlineBar;

export interface RLPerformanceResponse {
  rewards?: number[];
  curve?: { step: number; date: string; value: number; action: number }[];
  sharpe?: number;
  max_drawdown?: number;
  total_return?: number;
  actions?: Record<number, number>;
  train_log?: { symbol?: string; total_timesteps?: number };
}

export interface RLDecisionResponse {
  decision: string;
  confidence: number;
  reason: string[];
  state_summary: string;
  suggested_position_pct: number;
}
