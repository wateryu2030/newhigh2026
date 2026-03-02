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

  /** 北交所股票列表（独立接口，与主列表合并后保证北交所 Tab 有数据） */
  stocksBj: () =>
    get<{ stocks: { order_book_id: string; symbol: string; name: string }[] }>(BASE + '/stocks/bj'),

  /** 补全 DuckDB stocks 表名称（从 AKShare 拉取 A 股代码+名称）。sync=true 时同步执行并返回更新条数 */
  backfillStockNames: (options?: { sync?: boolean }) =>
    post<{ success: boolean; message?: string; updated?: number }>(
      BASE + '/backfill_stock_names',
      options?.sync ? { sync: true } : {}
    ),

  /** 全量 A 股同步：后台拉取沪深京全部股票日线（含北交所），断点续传 */
  syncAllAStocks: () =>
    post<{ success: boolean; message?: string }>(BASE + '/sync_all_a_stocks', {}),

  /** 数据状态：股票数、日线数 */
  dbStats: () => get<{ stocks: number; daily_bars: number }>(BASE + '/db_stats'),

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

  /** 机构级闭环：情绪回测 / 龙虎榜胜率 / 每周报告 */
  closedLoop: {
    emotionReport: () => get<{ success: boolean; report: ClosedLoopEmotionReport | null; message?: string }>(BASE + '/closed_loop/emotion_report'),
    lhbReport: () => get<{ success: boolean; report: ClosedLoopLHBReport | null; message?: string }>(BASE + '/closed_loop/lhb_report'),
    weeklyReport: () => get<{ success: boolean; report: ClosedLoopWeeklyReport | null; message?: string }>(BASE + '/closed_loop/weekly_report'),
    runEmotion: () => post<{ success: boolean; report?: ClosedLoopEmotionReport; path?: string; error?: string }>(BASE + '/closed_loop/run/emotion', {}),
    runLhb: () => post<{ success: boolean; report?: ClosedLoopLHBReport; error?: string }>(BASE + '/closed_loop/run/lhb', {}),
    runWeekly: () => post<{ success: boolean; report?: ClosedLoopWeeklyReport; stdout?: string; error?: string }>(BASE + '/closed_loop/run/weekly', {}),
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

export interface ClosedLoopEmotionReport {
  start_date?: string;
  end_date?: string;
  by_emotion?: Record<string, { win_rate: number; avg_win: number; avg_loss: number; profit_factor: number; max_drawdown: number; sharpe: number; total_return: number; mean_return: number; count: number }>;
  summary?: { win_rate: number; max_drawdown: number; sharpe: number; total_return: number; mean_return: number; count: number };
  trade_days?: number;
}

export interface ClosedLoopLHBReport {
  start_date?: string;
  end_date?: string;
  by_seat?: Record<string, Record<string, { win_rate: number; profit_factor: number; max_drawdown: number; total_return: number }> & { high_win_rate?: boolean }>;
  ranking?: { seat: string; win_rate_5d?: number }[];
  total_records?: number;
}

export interface ClosedLoopWeeklyReport {
  generated_at?: string;
  start_date?: string;
  end_date?: string;
  emotion_backtest?: unknown;
  lhb_statistics?: { by_seat_count?: number; ranking_sample?: { seat: string; win_rate_5d?: number }[] };
  emotion_report_path?: string;
  lhb_report_path?: string;
  emotion_backtest_error?: string;
  lhb_statistics_error?: string;
}
