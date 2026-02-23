export interface KlineBar {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

export interface Signal {
  date: string;
  type: 'BUY' | 'SELL';
  price: number;
  stop_loss?: number;
  target?: number;
  reason?: string;
}

export interface AiScore {
  symbol: string;
  score: number;
  suggestion: 'BUY' | 'SELL' | 'HOLD';
  position_pct?: number;
  risk_level?: string;
  latest_signal?: string;
}

export interface BacktestResult {
  equity_curve: { date: string; value: number }[];
  total_return: number;
  max_drawdown: number;
  sharpe_ratio: number;
  trades: { date: string; type: string; price: number; pnl?: number }[];
  monthly_heatmap?: { month: string; return: number }[];
}

export interface ScanItem {
  symbol: string;
  name?: string;
  signal?: string;
  price?: number;
  buy_prob?: number;
  reason?: string;
}
