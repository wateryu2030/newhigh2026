const BASE = '/api';

async function get<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = path.startsWith('http') ? new URL(path) : new URL(path, window.location.origin);
  if (params) Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const url = path.startsWith('http') ? path : `${window.location.origin}${path.startsWith(BASE) ? path : BASE + path}`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  if (!res.ok) {
    try {
      const j = JSON.parse(text) as { error?: string; message?: string };
      throw new Error(j.error || j.message || text);
    } catch (e) {
      if (e instanceof Error && e.message !== text) throw e;
      throw new Error(text || `HTTP ${res.status}`);
    }
  }
  return text ? (JSON.parse(text) as T) : ({} as T);
}

export interface KlineOptions {
  indicators?: 'ma';
  period?: 'day' | 'week' | 'month';
}

export interface NewsItem {
  title: string;
  content: string;
  url: string;
  source_site: string;
  source: string;
  publish_time?: string;
  keyword?: string;
  tag?: string;
  sentiment_score?: number;
  sentiment_label?: string;
}

export interface NewsResponse {
  success: boolean;
  symbol: string;
  news: NewsItem[];
  sentiment: {
    avg_score: number;
    positive_ratio: number;
    negative_ratio: number;
    neutral_ratio: number;
    count: number;
  };
  count: number;
}

/** K 线：不传 indicators 返回 KlineBar[]；indicators=ma 返回 { kline, ma5, ma10, ma20 } */
export const api = {
  kline: (
    symbol: string,
    start: string,
    end: string,
    options?: KlineOptions
  ): Promise<KlineBar[] | import('../types').KlineWithIndicatorsResponse> => {
    const params: Record<string, string> = { symbol, start, end };
    if (options?.indicators === 'ma') params.indicators = 'ma';
    if (options?.period && options.period !== 'day') params.period = options.period;
    return get(BASE + '/kline', params);
  },

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

  /** 补全 DuckDB stocks 表名称（从 AKShare 拉取 A 股代码+名称），保证列表显示完整 */
  backfillStockNames: () =>
    post<{ success: boolean; message?: string }>(BASE + '/backfill_stock_names', {}),

  news: (params: { symbol: string; sources?: string; limit?: number }) => {
    const q: Record<string, string> = { symbol: params.symbol };
    if (params.sources) q.sources = params.sources;
    if (params.limit != null) q.limit = String(params.limit);
    return get<NewsResponse>(BASE + '/news', q);
  },

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
