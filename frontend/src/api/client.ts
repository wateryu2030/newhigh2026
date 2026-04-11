/**
 * 可选：强制指定 API 根（如单独子域 https://api.xxx.com）。
 * 不填时浏览器默认走「当前站点同源 /api」，由 `next.config.js` rewrites 反代到 `API_PROXY_TARGET`（Gateway）。
 * 生产请在运行 Next 的环境中设置 `API_PROXY_TARGET`（或 `NEXT_PUBLIC_API_TARGET`），见 `.env.example`。
 * Cloudflare Tunnel 只暴露 :3000 时外网才能通，勿再请求 127.0.0.1:8000。
 */
export const API_BASE_STORAGE_KEY = 'newhigh_api_base';
/** JWT 存储键（与登录页一致） */
export const AUTH_TOKEN_STORAGE_KEY = 'newhigh_jwt_token';

const SERVER_API_BASE = process.env.NEXT_PUBLIC_API_TARGET || 'http://127.0.0.1:8000';

function getAuthHeaders(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  try {
    const token = localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)?.trim();
    if (token) return { Authorization: `Bearer ${token}` };
  } catch {
    /* ignore */
  }
  return {};
}

function redirectToLogin(): void {
  if (typeof window === 'undefined') return;
  if (window.location.pathname.startsWith('/login')) return;
  const next = encodeURIComponent(window.location.pathname + window.location.search);
  window.location.href = `/login?next=${next}`;
}

export function getApiBase(): string {
  if (typeof window === 'undefined') {
    return SERVER_API_BASE;
  }
  try {
    const v = localStorage.getItem(API_BASE_STORAGE_KEY)?.trim();
    if (
      v &&
      (v.startsWith('http://') || v.startsWith('https://')) &&
      v.length >= 12
    ) {
      return v.replace(/\/$/, '');
    }
  } catch {
    /* ignore */
  }
  /** 空字符串 → fetch(`/api/...`) 与页面同域（HTTPS），经 Next 反代到 Gateway */
  return '';
}

export type ApiGetOptions = { unwrapEnvelope?: boolean; /** 超时毫秒，避免后端长时间挂起导致前端永久「加载中」 */ timeoutMs?: number };

export async function apiGet<T>(path: string, options?: ApiGetOptions): Promise<T> {
  const base = getApiBase();
  const url = path.startsWith('http')
    ? path
    : base
      ? `${base}/api${path}`
      : `/api${path}`;
  const ms = options?.timeoutMs;
  const ctrl = typeof AbortController !== 'undefined' ? new AbortController() : undefined;
  const tid =
    ctrl != null && ms != null && ms > 0
      ? setTimeout(() => ctrl.abort(), ms)
      : undefined;
  let res: Response;
  try {
    res = await fetch(url, {
      cache: 'no-store',
      headers: { ...getAuthHeaders() },
      signal: ctrl?.signal,
    });
  } finally {
    if (tid != null) clearTimeout(tid);
  }
  if (res.status === 401) {
    redirectToLogin();
    throw new Error('Unauthorized');
  }
  if (!res.ok) throw new Error(`API ${path}: ${res.status}`);
  const json: unknown = await res.json();
  if (options?.unwrapEnvelope && json && typeof json === 'object' && 'ok' in json) {
    const o = json as { ok?: boolean; data?: unknown; error?: string };
    if (o.ok === false) throw new Error(o.error || 'API error');
    return o.data as T;
  }
  return json as T;
}

/** POST JSON，自动带 Bearer；401 跳转登录 */
export async function apiPostJson<T>(path: string, body?: unknown): Promise<T> {
  const base = getApiBase();
  const url = path.startsWith('http')
    ? path
    : base
      ? `${base}/api${path}`
      : `/api${path}`;
  const res = await fetch(url, {
    method: 'POST',
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: body !== undefined ? JSON.stringify(body) : '{}',
  });
  if (res.status === 401) {
    redirectToLogin();
    throw new Error('Unauthorized');
  }
  if (!res.ok) throw new Error(`API ${path}: ${res.status}`);
  return res.json() as Promise<T>;
}

function _apiErrorMessage(path: string, status: number, json: unknown): string {
  if (json && typeof json === 'object') {
    const o = json as { error?: string; detail?: unknown };
    if (typeof o.error === 'string' && o.error) return o.error;
    if (typeof o.detail === 'string') return o.detail;
  }
  return `API ${path}: ${status}`;
}

/** POST JSON，解包 { ok, data }；支持可选 X-Pipeline-Approve-Key 与超时（RSS 手刷等长任务） */
async function postPipelineEnvelope<T>(
  path: string,
  body: unknown,
  approveKey?: string,
  timeoutMs?: number,
): Promise<T> {
  const base = getApiBase();
  const url = base ? `${base}/api${path}` : `/api${path}`;
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...getAuthHeaders() };
  const k = approveKey?.trim();
  if (k) headers['X-Pipeline-Approve-Key'] = k;
  const ms = timeoutMs != null && timeoutMs > 0 ? timeoutMs : undefined;
  const ctrl = ms != null && typeof AbortController !== 'undefined' ? new AbortController() : undefined;
  const tid =
    ctrl != null && ms != null ? setTimeout(() => ctrl.abort(), ms) : undefined;
  let res: Response;
  try {
    res = await fetch(url, {
      method: 'POST',
      cache: 'no-store',
      headers,
      body: JSON.stringify(body ?? {}),
      signal: ctrl?.signal,
    });
  } finally {
    if (tid != null) clearTimeout(tid);
  }
  if (res.status === 401) {
    redirectToLogin();
    throw new Error('Unauthorized');
  }
  let json: unknown;
  try {
    json = await res.json();
  } catch {
    throw new Error(`API ${path}: ${res.status}`);
  }
  if (res.status >= 400) {
    throw new Error(_apiErrorMessage(path, res.status, json));
  }
  const env = json as { ok?: boolean; data?: T; error?: string };
  if (env.ok === false) {
    throw new Error(env.error || _apiErrorMessage(path, res.status, json));
  }
  return env.data as T;
}

export type PipelineRunMode = 'evolve_then_backtest' | 'backtest_only' | 'evolve_only';

export interface PipelineEvolutionParams {
  population_limit?: number;
  symbol?: string;
  offspring_size?: number;
  mutation_rate?: number;
  elite_size?: number;
}

export interface PipelineBacktestSpec {
  strategy_id: string;
  name?: string | null;
  symbol?: string;
  start_date?: string;
  end_date?: string;
  signal_source?: string;
  strategy_id_filter?: string | null;
  init_cash?: number;
  fees?: number;
  slippage?: number;
}

export interface PipelineRunRequest {
  request_id?: string | null;
  mode: PipelineRunMode;
  evolution?: PipelineEvolutionParams | null;
  backtest?: { specs: PipelineBacktestSpec[] };
  gates?: { min_sharpe?: number | null; max_drawdown_abs?: number | null } | null;
}

export interface PipelineJobListItem {
  job_id: string;
  owner_sub: string;
  mode: string;
  status: string;
  created_at?: string | null;
  updated_at?: string | null;
  client_request_id?: string | null;
}

export interface PipelineJobsListResponse {
  items: PipelineJobListItem[];
}

export interface PipelineStagedCandidate {
  strategy_id: string;
  name?: string;
  return_pct?: number | null;
  sharpe_ratio?: number | null;
  max_drawdown?: number | null;
  status?: string;
  source?: string;
}

export interface PipelineJobDetail {
  job_id: string;
  owner_sub: string;
  mode: string;
  status: string;
  created_at?: string | null;
  updated_at?: string | null;
  client_request_id?: string | null;
  approved_by?: string | null;
  approved_at?: string | null;
  rejected_by?: string | null;
  reject_reason?: string | null;
  result?: Record<string, unknown> | null;
  staged_candidates?: PipelineStagedCandidate[];
}

export interface PipelineRunResponse {
  job_id: string;
  status: string;
  deduplicated?: boolean;
}

export interface PipelineApproveResponse {
  job_id: string;
  promoted: number;
  status: string;
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
  baseURL: () => {
    const b = getApiBase();
    return b ? `${b}/api` : '/api';
  },
  dashboard: () => apiGet<DashboardResponse>('/dashboard', { timeoutMs: 25_000 }),
  dataStatus: () => apiGet<DataStatusResponse>('/data/status', { timeoutMs: 20_000 }),
  /** a_stock_daily 覆盖：总行数、有 K 线的标的数、按 bar 数 TopN（解释「池大线少」） */
  dataDailyCoverage: (limitCodes?: number) =>
    apiGet<DailyCoverageResponse>(
      `/data/daily-coverage${limitCodes != null ? `?limit_codes=${limitCodes}` : ''}`
    ),
  marketSummary: () => apiGet<MarketSummaryResponse>('/market/summary'),
  marketLimitup: (limit?: number) =>
    apiGet<LimitupDrillItem[]>(`/market/limitup${limit != null ? `?limit=${limit}` : ''}`),
  marketFundflow: (limit?: number) =>
    apiGet<FundflowDrillItem[]>(`/market/fundflow${limit != null ? `?limit=${limit}` : ''}`),
  marketLonghubangRows: (limit?: number) =>
    apiGet<LonghubangDrillItem[]>(`/market/longhubang${limit != null ? `?limit=${limit}` : ''}`),
  stocks: (limit?: number) => apiGet<StockItem[]>(`/stocks${limit != null ? `?limit=${limit}` : ''}`),
  strategies: () => apiGet<StrategiesResponse>('/strategies'),
  strategiesMarket: (limit?: number) =>
    apiGet<StrategiesMarketResponse>(`/strategies/market${limit != null ? `?limit=${limit}` : ''}`),
  portfolio: () => apiGet<PortfolioResponse>('/portfolio/weights'),
  risk: () => apiGet<RiskResponse>('/risk/status'),
  market: async (symbol?: string, interval?: string, limit?: number) => {
    const path = `/market/klines?symbol=${encodeURIComponent(symbol || 'BTCUSDT')}&interval=${interval || '1h'}&limit=${limit ?? 120}`;
    const base = getApiBase();
    const url = path.startsWith('http') ? path : base ? `${base}/api${path}` : `/api${path}`;
    const res = await fetch(url, { cache: 'no-store', headers: { ...getAuthHeaders() } });
    if (res.status === 401) {
      redirectToLogin();
      throw new Error('Unauthorized');
    }
    if (!res.ok) throw new Error(`API ${path}: ${res.status}`);
    const json = (await res.json()) as {
      ok?: boolean;
      data?: MarketResponse;
      error?: string;
      source?: string;
    };
    if (json.ok === false) throw new Error(json.error || 'API error');
    const data = json.data;
    if (!data) throw new Error('API error: missing data');
    return { ...data, source: json.source };
  },
  /** 最近一条数据质量巡检（信封 unwrap） */
  dataQuality: () =>
    apiGet<DataQualityLatest | null>('/data/quality', { unwrapEnvelope: true }),
  ashareStocks: () => apiGet<AshareStocksResponse>('/market/ashare/stocks'),
  news: (symbol?: string, limit?: number) =>
    apiGet<NewsResponse>(`/news?limit=${limit ?? 100}${symbol ? `&symbol=${encodeURIComponent(symbol)}` : ''}`),
  /** 政策采集：GET /api/news/collector → DuckDB news_items（symbol=__POLICY__） */
  newsCollector: (limit?: number, category?: string) => {
    const q = new URLSearchParams({ limit: String(limit ?? 100) });
    if (category?.trim()) q.set('category', category.trim());
    return apiGet<NewsResponse>(`/news/collector?${q}`);
  },
  hotTicker: () => apiGet<HotTickerResponse>('/news/hot-ticker'),
  /** 手动 RSS 宏观入库 + 摘要；可选发飞书等 Webhook（服务端 NEWS_BREAKING_WEBHOOK_URL） */
  newsManualRefresh: (body?: { send_webhook?: boolean }) =>
    postPipelineEnvelope<NewsManualRefreshResponse>('/news/manual-refresh', body ?? {}, undefined, 120_000),
  trades: () => apiGet<TradesResponse>('/trades'),
  evolution: () => apiGet<EvolutionResponse>('/evolution'),
  alphaLab: () => apiGet<AlphaLabResponse>('/alpha-lab'),
  alphaLabDrill: (stage: string, limit?: number) => {
    const q = new URLSearchParams({ stage });
    if (limit != null) q.set('limit', String(limit));
    return apiGet<AlphaLabDrillResponse>(`/alpha-lab/drill?${q}`);
  },
  positions: () => apiGet<PositionsResponse>('/positions'),
  marketEmotion: () => apiGet<MarketEmotionResponse>('/market/emotion', { timeoutMs: 20_000 }),
  /** 后端可能走 AkShare 拉全市场，隧道/境外易慢；超时后走 catch 展示兜底文案 */
  marketSentiment7d: () =>
    /** 东财现货 + 日 K SQL；应大于服务端 AkShare 超时并预留 DuckDB 时间 */
    apiGet<MarketSentiment7dResponse>('/market/sentiment-7d', { timeoutMs: 120_000 }),
  marketHotmoney: (limit?: number) => apiGet<HotmoneySeatItem[]>(`/market/hotmoney${limit != null ? `?limit=${limit}` : ''}`),
  marketMainThemes: (limit?: number) => apiGet<MainThemeItem[]>(`/market/main-themes${limit != null ? `?limit=${limit}` : ''}`),
  strategySignals: (limit?: number) => apiGet<TradeSignalItem[]>(`/strategy/signals${limit != null ? `?limit=${limit}` : ''}`),
  sniperCandidates: (limit?: number) => apiGet<SniperCandidateItem[]>(`/market/sniper-candidates${limit != null ? `?limit=${limit}` : ''}`),
  systemDataOverview: () =>
    apiGet<SystemDataOverviewResponse>('/system/data-overview', { timeoutMs: 45_000 }),
  systemStatus: (limit?: number) =>
    apiGet<SystemStatusResponse>(`/system/status${limit != null ? `?limit=${limit}` : ''}`),
  healthDetail: () =>
    apiGet<HealthDetailPayload>('/system/health-detail', { unwrapEnvelope: true, timeoutMs: 25_000 }),
  backtestErrors: (limit?: number) =>
    apiGet<{ items: BacktestErrorRow[] }>(
      `/system/backtest-errors${limit != null ? `?limit=${limit}` : ''}`,
      { unwrapEnvelope: true, timeoutMs: 15_000 },
    ),
  /** 策略流水线：已登录即可提交；admin 审批后入库 strategy_market */
  pipelineRun: (body: PipelineRunRequest) =>
    postPipelineEnvelope<PipelineRunResponse>('/strategies/pipeline/run', body),
  pipelineJobs: (limit?: number) =>
    apiGet<PipelineJobsListResponse>(
      `/strategies/pipeline/jobs${limit != null ? `?limit=${limit}` : ''}`,
      { unwrapEnvelope: true, timeoutMs: 60_000 },
    ),
  pipelineJob: (jobId: string) =>
    apiGet<PipelineJobDetail>(`/strategies/pipeline/jobs/${encodeURIComponent(jobId)}`, {
      unwrapEnvelope: true,
      timeoutMs: 30_000,
    }),
  pipelineApprove: (jobId: string, body?: { strategy_ids?: string[] }, approveKey?: string) =>
    postPipelineEnvelope<PipelineApproveResponse>(
      `/strategies/pipeline/jobs/${encodeURIComponent(jobId)}/approve`,
      body ?? {},
      approveKey,
    ),
  pipelineReject: async (jobId: string, reason?: string) => {
    const base = getApiBase();
    const q = reason != null && reason !== '' ? `?reason=${encodeURIComponent(reason)}` : '';
    const path = `/strategies/pipeline/jobs/${encodeURIComponent(jobId)}/reject${q}`;
    const url = base ? `${base}/api${path}` : `/api${path}`;
    const res = await fetch(url, { method: 'POST', cache: 'no-store', headers: { ...getAuthHeaders() } });
    if (res.status === 401) {
      redirectToLogin();
      throw new Error('Unauthorized');
    }
    let json: unknown;
    try {
      json = await res.json();
    } catch {
      throw new Error(`API ${path}: ${res.status}`);
    }
    if (res.status >= 400) {
      throw new Error(_apiErrorMessage(path, res.status, json));
    }
    const env = json as { ok?: boolean; data?: { job_id: string; status: string }; error?: string };
    if (env.ok === false) {
      throw new Error(env.error || 'reject failed');
    }
    return env.data as { job_id: string; status: string };
  },
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
  ensureStocks: () => {
    const base = getApiBase();
    const url = base ? `${base}/api/data/ensure-stocks` : '/api/data/ensure-stocks';
    return fetch(url, {
      method: 'POST',
      cache: 'no-store',
      headers: { ...getAuthHeaders() },
    }).then((r) => {
      if (r.status === 401) {
        redirectToLogin();
        throw new Error('Unauthorized');
      }
      return r.json() as Promise<{ ok: boolean; rows: number; error?: string }>;
    });
  },
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
    const base = getApiBase();
    const url = `${base ? `${base}/api` : '/api'}/evolution/trigger?${params}`;
    return fetch(url, {
      method: 'POST',
      cache: 'no-store',
      headers: { ...getAuthHeaders() },
    }).then((r) => {
      if (r.status === 401) {
        redirectToLogin();
        throw new Error('Unauthorized');
      }
      return r.json() as Promise<{ task_id: string; status: string }>;
    });
  },
  getEvolutionStatus: (taskId: string) =>
    apiGet<{ task_id: string; status: string; result: unknown }>(`/evolution/status/${encodeURIComponent(taskId)}`),
  getEvolutionTasks: (limit?: number) =>
    apiGet<{ tasks: EvolutionTaskItem[] }>(`/evolution/tasks${limit != null ? `?limit=${limit}` : ''}`),
  getSkillStats: () =>
    apiGet<{ call_count: number; last_call_time: string | null }>('/skill/stats'),
  // 大佬策略 · 股东策略画像
  collectedStocksRank3: (limit?: number, reportDate?: string) => {
    const q = new URLSearchParams();
    if (limit != null) q.set('limit', String(limit));
    if (reportDate) q.set('report_date', reportDate);
    const query = q.toString();
    return apiGet<CollectedStocksRank3Response>(`/financial/collected-stocks-rank3${query ? `?${query}` : ''}`);
  },
  collectedStocksAllRanks: (limit?: number, reportDate?: string) => {
    const q = new URLSearchParams();
    if (limit != null) q.set('limit', String(limit));
    if (reportDate) q.set('report_date', reportDate);
    const query = q.toString();
    return apiGet<CollectedStocksAllRanksResponse>(`/financial/collected-stocks-all-ranks${query ? `?${query}` : ''}`);
  },
  shareholderByName: (name: string, limit?: number) => {
    const q = new URLSearchParams({ name: name.trim() });
    if (limit != null) q.set('limit', String(limit));
    return apiGet<ShareholderByNameResponse>(`/financial/shareholder-by-name?${q}`);
  },
  shareholderStrategy: (name: string, coLimit?: number) => {
    const q = new URLSearchParams({ name: name.trim() });
    if (coLimit != null) q.set('co_limit', String(coLimit));
    return apiGet<ShareholderStrategyResponse>(`/financial/shareholder-strategy?${q}`);
  },
  antiQuantPool: (limit?: number, minTop10Ratio?: number) => {
    const q = new URLSearchParams();
    if (limit != null) q.set('limit', String(limit));
    if (minTop10Ratio != null) q.set('min_top10_ratio', String(minTop10Ratio));
    const query = q.toString();
    return apiGet<AntiQuantPoolResponse>(`/financial/anti-quant-pool${query ? `?${query}` : ''}`);
  },
  antiQuantStock: (stockCode: string) =>
    apiGet<AntiQuantStockResponse>(`/financial/anti-quant-stock/${stockCode}`),
};

export interface CollectedStocksRank3Item {
  stock_code: string;
  stock_name: string;
  report_date: string;
  rank?: number;
  shareholder_name: string;
  shareholder_type: string;
  share_count: number;
  share_ratio: number;
}

export interface CollectedStocksRank3Response {
  ok: boolean;
  count: number;
  report_date: string | null;
  data: CollectedStocksRank3Item[];
  error?: string;
}

export interface CollectedStocksAllRanksItem extends CollectedStocksRank3Item {
  rank: number;
}

export interface CollectedStocksAllRanksResponse {
  ok: boolean;
  count: number;
  report_date: string | null;
  data: CollectedStocksAllRanksItem[];
  error?: string;
}

export interface ShareholderByNameItem {
  name: string;
  shareholder_type: string;
  stock_count: number;
}

export interface ShareholderByNameResponse {
  ok: boolean;
  count: number;
  data: ShareholderByNameItem[];
  error?: string;
  /** 是否使用了首尾字/difflib 等宽松匹配 */
  relaxed_match?: boolean;
  /** 后端提示用户核对规范名称 */
  hint?: string;
}

/** 与当前股东在同一前十榜（同代码+报告日）共现过的其他股东 */
export interface CoShareholderItem {
  name: string;
  shareholder_type: string;
  /** 共现「榜位」次数（同一股票多期可多次） */
  co_slot_count: number;
  /** 涉及不同股票只数 */
  co_stock_count: number;
}

export interface ShareholderStrategyResponse {
  ok: boolean;
  shareholder_name?: string;
  latest_quarter?: string | null;
  co_shareholders?: CoShareholderItem[];
  info?: {
    name: string;
    identity: string;
    tags: string[];
    stats: { totalMarketCap: number; stockCount: number; avgHoldPeriod: number; winRate: number };
  };
  holdings: Array<{
    stockCode: string;
    stockName: string;
    industry: string;
    marketCap: number;
    pe: number;
    holdShares: number;
    holdValue: number;
    /** 最近交易日收盘价（元），用于气泡图 X 轴 */
    latestClose?: number | null;
    /** 最近一日成交额（亿元），用于气泡图 Y 轴 log */
    turnoverYi?: number | null;
    ratio: number;
    firstEntry: string;
    status: 'current' | 'exited';
    exitQuarter?: string;
  }>;
  changes: Array<{
    quarter: string;
    stockCode: string;
    stockName: string;
    action: '新进' | '增持' | '减持' | '退出';
    changeShares: number;
    changeRatio?: number;
  }>;
  error?: string;
}

export interface AntiQuantPoolItem {
  stock_code: string;
  stock_name: string;
  top10_ratio: number;
  top10_ratio_std: number | null;
  institution_count_current: number;
  long_term_institution_count: number;
  turnover_avg: number | null;
  report_count: number;
  latest_report_date: string | null;
  filter_mode: string;
  /** 前十大 HHI（越高通常头部股东占比越集中） */
  hhi_top10?: number | null;
  /** 最近两期前十大合计占比差，单位：百分点 */
  top10_delta_pp?: number | null;
  /** 筹码综合得分 0–100，仅用于排序 */
  chip_score?: number | null;
}

export interface AntiQuantPoolResponse {
  ok: boolean;
  count: number;
  filter_mode: string;
  summary: {
    total_stocks_analyzed?: number;
    candidate_count?: number;
    avg_top10_ratio?: number;
    avg_institution_count?: number;
    avg_chip_score?: number;
  };
  data: AntiQuantPoolItem[];
  note?: string;
  error?: string;
}

export interface AntiQuantStockResponse {
  ok: boolean;
  stock_code: string;
  in_pool: boolean;
  factors: {
    top10_ratio: number;
    top10_ratio_std: number | null;
    institution_count_current: number;
    long_term_institution_count: number;
    turnover_avg: number | null;
    report_count: number;
    data_sufficient: boolean;
  };
  latest_report_date?: string | null;
  chip?: {
    hhi_top10: number | null;
    top10_delta_pp: number | null;
    chip_score: number | null;
  };
  error?: string;
}

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
  stock_name?: string;
  theme: string;
  sniper_score: number;
  confidence: number;
  last_price?: number | null;
  change_pct?: number | null;
  updated_at?: string;
}

/** 涨停池下钻行 */
export interface LimitupDrillItem {
  code: string;
  stock_name?: string;
  last_price?: number | null;
  change_pct?: number | null;
  limit_up_times?: number | null;
  updated_at?: string;
}

/** 龙虎榜下钻行 */
export interface LonghubangDrillItem {
  code: string;
  stock_name?: string;
  lhb_date?: string | null;
  net_buy?: number | null;
  last_price?: number | null;
  change_pct?: number | null;
  updated_at?: string;
}

/** 资金流下钻行 */
export interface FundflowDrillItem {
  code: string;
  stock_name?: string;
  main_net_inflow?: number | null;
  snapshot_date?: string | null;
  last_price?: number | null;
  change_pct?: number | null;
  updated_at?: string;
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

export interface MarketSentiment7dResponse {
  score?: number;
  level?: string;
  emoji?: string;
  description?: string;
  dimensions?: Record<string, number>;
  weights?: Record<string, number>;
  stats?: Record<string, unknown>;
  data_source?: string;
  /** 日 K 降级时后端写入的最近交易日 YYYY-MM-DD */
  trade_date?: string;
  /** 日 K 的 trade_date 距今天（服务器本地日期）的自然日差 */
  calendar_lag_days?: number | null;
  error?: string;
  detail?: string;
}

export interface HotmoneySeatItem {
  seat_name: string;
  trade_count: number;
  win_rate: number;
  avg_return: number;
  updated_at?: string;
}

export interface MainThemeItem {
  sector: string;
  total_volume: number;
  rank: number;
  updated_at?: string;
}

export interface TradeSignalItem {
  code: string;
  /** 股票简称（来自 a_stock_basic） */
  stock_name?: string;
  signal: string;
  confidence?: number;
  /** 无有效数值时为 null，前端显示 — */
  target_price?: number | null;
  stop_loss?: number | null;
  strategy_id?: string;
  signal_score?: number;
  /** 现价：实时或最近日线 close */
  last_price?: number | null;
  /** 涨跌幅 %（来自实时表，可能为空） */
  change_pct?: number | null;
  /** 展示用短时间 MM-DD HH:mm，无微秒 */
  updated_at?: string;
}

export interface DashboardResponse {
  total_equity: number;
  daily_return_pct: number;
  /** 由权益曲线估算，样本过短时可能为 null */
  sharpe_ratio: number | null;
  max_drawdown_pct: number | null;
  equity_curve: number[];
  top_strategies: { id: string; name: string; return_pct: number | null }[];
  ai_generated_today: number | null;
  strategies_alive: number | null;
  strategies_live: number | null;
  /** 权益曲线所依据的股票代码（示意，非组合净值） */
  equity_proxy_symbol?: string | null;
  /** 后端说明：如单票示意曲线、无库时演示曲线等 */
  dashboard_notes?: string[];
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
  /** 来自信封 json_ok(..., source=)，由 api.market 合并 */
  source?: string;
}

/** GET /data/quality unwrap 后的 data 字段 */
export interface DataQualityLatest {
  id?: number;
  run_at?: string | null;
  report?: {
    timestamp?: string;
    checks?: Array<{ name?: string; result?: Record<string, unknown> }>;
    [key: string]: unknown;
  };
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
  /** 与 /api/system/data-overview 同源：``news_items`` 表行数；列表为抽样+去重 */
  news_items_total?: number | null;
  /** 政策采集：主库 DuckDB `news_items`；detail 如 `policy_news_empty` / `policy_news_read_error`，见 GET /api/news/collector */
  detail?: string;
}

export interface HotTickerLine {
  type: string;
  text: string;
  code?: string | null;
}

export interface HotTickerResponse {
  lines: HotTickerLine[];
  banner: string;
  updated_at: string;
}

/** POST /api/news/manual-refresh 解包后 data */
export interface NewsManualRefreshResponse {
  rss_inserted: number;
  summary: string;
  summary_lines: number;
  webhook_sent: boolean;
  webhook_skipped_reason?: string | null;
  /** 写入阶段失败时的说明；HTTP 仍为 200 时也会出现 */
  error?: string | null;
  rss_fetch_ok?: boolean;
}

/** /data/status 中单套 schema 的统计切片 */
export interface DataStatusBreakdownSlice {
  stocks: number;
  daily_bars: number;
  date_min: string | null;
  date_max: string | null;
}

export interface DataStatusResponse {
  ok: boolean;
  /** duckdb_pipeline | duckdb_astock | 历史值 duckdb */
  source: string | null;
  stocks: number;
  daily_bars: number;
  date_min: string | null;
  date_max: string | null;
  /** 并列展示：stocks/daily_bars 表 vs a_stock_basic/a_stock_daily 表 */
  breakdown?: {
    astock_schema: DataStatusBreakdownSlice | null;
    pipeline_schema: DataStatusBreakdownSlice | null;
  };
}

/** GET /data/daily-coverage */
export interface DailyCoverageResponse {
  ok: boolean;
  error?: string;
  total_rows?: number;
  distinct_codes?: number;
  stock_pool_codes?: number;
  avg_bars_per_code?: number;
  date_min?: string | null;
  date_max?: string | null;
  top_codes?: Array<{
    code: string;
    bar_count: number;
    date_min: string | null;
    date_max: string | null;
  }>;
}

export interface TradesResponse {
  trades: { time: string; strategy: string; symbol: string; side: string; qty: number; price: number }[];
}

export interface EvolutionResponse {
  current_generation: number;
  best_strategy?: { id: string; sharpe: number; return_pct: number } | null;
  generations: { gen: number }[];
  /** duckdb：最近成功进化任务摘要；demo：无记录时的占位 */
  source?: string;
}

export interface AlphaLabResponse {
  generated_today: number;
  passed_backtest: number;
  passed_risk: number;
  deployed: number;
  source?: string;
  binding_note?: string;
}

export interface AlphaLabDrillItem {
  code: string;
  stock_name: string;
  subtitle?: string | null;
  score?: number | null;
  confidence?: number | null;
  strategy_id?: string | null;
  snapshot_time?: string | null;
}

export interface AlphaLabDrillResponse {
  stage: string;
  items: AlphaLabDrillItem[];
  total: number;
  source?: string;
  binding_note?: string;
}

export interface HealthDetailPayload {
  status: string;
  services?: Record<string, unknown>;
  data_availability?: Record<string, unknown>;
  checks?: Record<string, unknown>;
  timestamp?: string;
  celery: {
    status: string;
    workers?: string[];
    reason?: string;
    error?: string;
  };
  pipeline_meta_recent: Array<{ k?: string; v?: string; updated_at?: string }>;
  prometheus_metrics_path: string;
  alert_webhook_configured?: boolean;
}

export interface BacktestErrorRow {
  id: number;
  task_name?: string | null;
  strategy_id?: string | null;
  payload_preview?: string | null;
  error_message?: string | null;
  created_at?: string | null;
}

export interface SystemDataOverviewResponse {
  ok: boolean;
  counts: {
    limitup_pool: number;
    sniper_candidates: number;
    trade_signals: number;
    /** 按 strategy_id 计数（如 ai_fusion、shareholder_chip、market_agg；_unset 表示空 id） */
    trade_signals_by_strategy?: Record<string, number>;
    news_items: number;
    stock_pool: number;
    daily_bars: number;
    longhubang: number;
    fundflow: number;
    emotion_state: string | null;
    hotmoney_seats: number;
  };
  summary: {
    limitup_pool: number;
    sniper_candidates: number;
    trade_signals: number;
    news_items: number;
  };
  error?: string;
}

export interface PositionsResponse {
  positions: unknown[];
}

/** 股票问答 MVP：POST /api/stock-qa/analyze */
export interface StockQAEntity {
  mention: string;
  symbol: string;
  confidence?: number;
  source?: string;
}

export interface StockQAShareholderRow {
  name: string;
  ratio: number | null;
}

export interface StockQASymbolBlock {
  symbol: string;
  name?: string;
  sector?: string;
  errors?: string[];
  quote?: {
    last_price?: number;
    change_pct?: number;
    volume?: number;
    amount?: number;
    snapshot_time?: string | null;
  };
  financial?: {
    report_date?: string | null;
    total_revenue?: number | null;
    net_profit?: number | null;
    gross_margin?: number | null;
    net_margin?: number | null;
    operating_cash_flow?: number | null;
  } | null;
  shareholders?: {
    report_date?: string | null;
    top_holders?: StockQAShareholderRow[];
  };
  sniper?: {
    sniper_score?: number | null;
    confidence?: number | null;
    theme?: string;
  } | null;
  trend?: {
    bias?: string;
    summary?: string;
    model?: string;
    lstm?: Record<string, unknown>;
  };
}

export interface StockQAAnalyzeData {
  entities: StockQAEntity[];
  symbols: StockQASymbolBlock[];
  summary: string;
  llm_ner_error?: string | null;
  ner_mode?: string;
}

export interface StockQAAnalyzeRequest {
  text?: string;
  max_symbols?: number;
  async_mode?: boolean;
  use_llm_ner?: boolean;
  ner_mode?: 'hybrid' | 'rules_only' | 'llm_only';
  symbols_override?: string[];
  include_lstm?: boolean;
}

export interface StockQAJobPayload {
  job_id: string;
  async: boolean;
}

export interface StockQAJobStatus {
  job_id: string;
  status: string;
  progress?: number;
  error?: string | null;
  result?: StockQAAnalyzeData | null;
}

/** 同步返回完整分析；async_mode 时返回 { job_id, async } */
export async function postStockQAAnalyze(
  body: StockQAAnalyzeRequest,
): Promise<StockQAAnalyzeData | StockQAJobPayload> {
  const json = await apiPostJson<{ ok?: boolean; data?: unknown; error?: string }>(
    '/stock-qa/analyze',
    body,
  );
  if (json && typeof json === 'object' && 'ok' in json && json.ok === false) {
    throw new Error((json as { error?: string }).error || 'stock_qa failed');
  }
  const data = (json as { data?: StockQAAnalyzeData & StockQAJobPayload }).data;
  if (!data) throw new Error('stock_qa: empty data');
  if ('job_id' in data && (data as StockQAJobPayload).async === true) {
    return data as StockQAJobPayload;
  }
  return data as StockQAAnalyzeData;
}

export async function getStockQAJob(jobId: string): Promise<StockQAJobStatus> {
  return apiGet<StockQAJobStatus>(`/stock-qa/jobs/${jobId}`, { unwrapEnvelope: true });
}

/** Markdown 正文 */
export async function postStockQAReportMarkdown(data: StockQAAnalyzeData): Promise<string> {
  const base = getApiBase();
  const url = base ? `${base}/api/stock-qa/report` : `/api/stock-qa/report`;
  const res = await fetch(url, {
    method: 'POST',
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ data }),
  });
  if (res.status === 401) {
    redirectToLogin();
    throw new Error('Unauthorized');
  }
  if (!res.ok) throw new Error(`stock_qa report: ${res.status}`);
  return res.text();
}

export async function getStockQAJobReportMarkdown(jobId: string): Promise<string> {
  const base = getApiBase();
  const url = base ? `${base}/api/stock-qa/jobs/${jobId}/report.md` : `/api/stock-qa/jobs/${jobId}/report.md`;
  const res = await fetch(url, { cache: 'no-store', headers: { ...getAuthHeaders() } });
  if (res.status === 401) {
    redirectToLogin();
    throw new Error('Unauthorized');
  }
  if (!res.ok) throw new Error(`stock_qa job report: ${res.status}`);
  return res.text();
}
