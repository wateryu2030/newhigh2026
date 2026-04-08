# Auto-fixed by Cursor on 2026-04-02: 默认万二手续费+千一滑点、可选止损止盈、logging。
"""基于 DuckDB 数据与信号运行回测，返回资金曲线与风险指标。"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from .cost_models import CommissionModel, SlippageModel, effective_fee_per_order
from .data_loader import load_ohlcv_from_db, load_signals_from_db
from .metrics import compute_metrics
from .position_manager import apply_stop_take_series
from .runner import run_backtest, run_backtest_from_ohlcv

_log = logging.getLogger(__name__)


def _align_signals_to_dates(
    date_index: pd.DatetimeIndex,
    entries_by_date: dict,
    exits_by_date: dict,
) -> tuple:
    """将 entries_by_date / exits_by_date 对齐到 date_index，返回 (entries, exits) Series。"""
    entries = pd.Series(False, index=date_index)
    exits = pd.Series(False, index=date_index)
    for i, d in enumerate(date_index):
        key = d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)[:10]
        if entries_by_date.get(key):
            entries.iloc[i] = True
        if exits_by_date.get(key):
            exits.iloc[i] = True
    return entries, exits


def _extract_equity_curve(pf, result: Dict[str, Any]) -> None:
    """从投资组合中提取资金曲线。"""
    try:
        val = pf.value()
        if val is not None and len(val) > 0:
            for t, v in val.items():
                dt = t.strftime("%Y-%m-%d") if hasattr(t, "strftime") else str(t)[:10]
                result["equity_curve"].append({"date": dt, "value": float(v)})
    except Exception:
        pass


def _extract_trade_count(pf, result: Dict[str, Any]) -> None:
    """从投资组合中提取交易次数。"""
    try:
        result["trade_count"] = (
            len(pf.trades.records_readable)
            if hasattr(pf, "trades") and pf.trades is not None
            else None
        )
    except Exception:
        pass


def run_backtest_from_db(
    symbol: str,
    start_date: str,
    end_date: str,
    signal_source: str = "trade_signals",
    strategy_id: Optional[str] = None,
    init_cash: float = 10000.0,
    fees: float = 0.0002,
    slippage: float = 0.001,
    conn: Any = None,
    stop_loss_pct: Optional[float] = None,
    take_profit_pct: Optional[float] = None,
    use_legacy_fee_combine: bool = False,
) -> Dict[str, Any]:
    """
    从 quant_system.duckdb 读取日 K 与信号，跑回测，返回资金曲线与风险指标。
    输入：
      symbol: 标的代码（6 位或 600519.SH）
      start_date, end_date: YYYY-MM-DD
      signal_source: 'trade_signals' | 'market_signals'
      fees: 单边手续费占成交额（默认 0.0002 = 万二）
      slippage: 单边滑点占价（默认 0.001 = 千一）；与 fees 合并为 vectorbt 单参数时默认 per_order=fees+slippage
      stop_loss_pct / take_profit_pct: 可选，如 0.08 表示 8% 止损（简化日频模型）
      use_legacy_fee_combine: True 时使用旧式 fees + 2*slippage
    输出：
      equity_curve: [{"date": "YYYY-MM-DD", "value": float}, ...]
      sharpe_ratio, max_drawdown, total_return, win_rate_pct, ...
      error: 若有异常则带错误信息，其余字段可为 None
    """
    result = {
        "equity_curve": [],
        "sharpe_ratio": None,
        "max_drawdown": None,
        "total_return": None,
        "win_rate_pct": None,
        "profit_factor": None,
        "total_profit": None,
        "trade_count": None,
        "error": None,
    }

    try:
        ohlcv_df, _ = load_ohlcv_from_db(symbol, start_date, end_date, conn=conn)
        if ohlcv_df is None or ohlcv_df.empty:
            result["error"] = "no_ohlcv"
            return result

        entries_by_date, exits_by_date = load_signals_from_db(
            symbol, start_date, end_date,
            signal_source=signal_source,
            strategy_id=strategy_id,
            conn=conn,
        )

        date_index = pd.DatetimeIndex(ohlcv_df["date"])
        entries, exits = _align_signals_to_dates(date_index, entries_by_date, exits_by_date)

        close = ohlcv_df.set_index("date")["close"]
        close = close.reindex(date_index).ffill().fillna(0)

        if close.max() <= 0:
            result["error"] = "invalid_prices"
            return result

        ent = entries.reindex(close.index).fillna(False)
        ex = exits.reindex(close.index).fillna(False)
        if stop_loss_pct is not None or take_profit_pct is not None:
            ent, ex = apply_stop_take_series(
                close, ent, ex,
                stop_loss_pct=stop_loss_pct,
                take_profit_pct=take_profit_pct,
            )

        if use_legacy_fee_combine:
            effective_fees = float(fees) + 2.0 * float(slippage)
        else:
            effective_fees = effective_fee_per_order(
                CommissionModel(rate_per_leg=float(fees)),
                SlippageModel(rate_per_leg=float(slippage)),
            )
        pf = run_backtest(
            close,
            ent,
            ex,
            init_cash=init_cash,
            fees=effective_fees,
            freq="1D",
        )

        metrics = compute_metrics(pf, freq="1D")
        result.update({
            "sharpe_ratio": metrics.get("sharpe_ratio"),
            "max_drawdown": metrics.get("max_drawdown"),
            "total_return": metrics.get("total_return"),
            "win_rate_pct": metrics.get("win_rate_pct"),
            "profit_factor": metrics.get("profit_factor"),
            "total_profit": metrics.get("total_profit"),
        })

        _extract_equity_curve(pf, result)
        _extract_trade_count(pf, result)

    except Exception as e:
        _log.exception("run_backtest_from_db failed: %s", symbol)
        result["error"] = str(e)

    return result


def _metrics_from_equity_curve(equity_curve: List[Dict[str, Any]]) -> Dict[str, Any]:
    """从合并后的资金曲线 [{date, value}, ...] 计算 total_return、max_drawdown、sharpe（年化）。"""
    out = {"total_return": None, "max_drawdown": None, "sharpe_ratio": None}
    if not equity_curve or len(equity_curve) < 2:
        return out
    try:
        df = pd.DataFrame(equity_curve)
        df = df.sort_values("date")
        vals = df["value"].astype(float)
        start_val = float(vals.iloc[0])
        end_val = float(vals.iloc[-1])
        if start_val > 0:
            out["total_return"] = (end_val - start_val) / start_val
        cummax = vals.cummax()
        dd = (vals - cummax) / cummax.replace(0, float("nan"))
        out["max_drawdown"] = float(dd.min()) if len(dd.dropna()) else None
        rets = vals.pct_change().dropna()
        if len(rets) > 0 and rets.std() != 0:
            out["sharpe_ratio"] = float(rets.mean() / rets.std() * (252**0.5))
    except Exception:
        pass
    return out


def run_backtest_multi_from_db(
    symbols: List[str],
    start_date: str,
    end_date: str,
    signal_source: str = "trade_signals",
    strategy_id: Optional[str] = None,
    init_cash: float = 10000.0,
    fees: float = 0.0002,
    slippage: float = 0.001,
    conn: Any = None,
    stop_loss_pct: Optional[float] = None,
    take_profit_pct: Optional[float] = None,
    use_legacy_fee_combine: bool = False,
) -> Dict[str, Any]:
    """
    多标的组合回测：等权分配初始资金，分别回测后合并资金曲线与指标。
    返回格式与 run_backtest_from_db 一致；equity_curve 为合并后的总权益。
    """
    result = {
        "equity_curve": [],
        "sharpe_ratio": None,
        "max_drawdown": None,
        "total_return": None,
        "win_rate_pct": None,
        "profit_factor": None,
        "total_profit": None,
        "trade_count": None,
        "error": None,
    }
    if not symbols:
        result["error"] = "no_symbols"
        return result
    n = len(symbols)
    cash_per = init_cash / n
    per_results: List[Dict[str, Any]] = []
    for sym in symbols:
        r = run_backtest_from_db(
            symbol=sym,
            start_date=start_date,
            end_date=end_date,
            signal_source=signal_source,
            strategy_id=strategy_id,
            init_cash=cash_per,
            fees=fees,
            slippage=slippage,
            conn=conn,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
            use_legacy_fee_combine=use_legacy_fee_combine,
        )
        if r.get("error"):
            continue
        per_results.append(r)
    if not per_results:
        result["error"] = "no_ohlcv_or_signals"
        return result
    # 按日期合并 equity_curve：同一天多标的加总
    by_date: Dict[str, float] = {}
    for r in per_results:
        for point in r.get("equity_curve") or []:
            d = point.get("date") or ""
            v = float(point.get("value") or 0)
            by_date[d] = by_date.get(d, 0) + v
    result["equity_curve"] = [{"date": d, "value": v} for d, v in sorted(by_date.items())]
    result["total_profit"] = sum((r.get("total_profit") or 0) for r in per_results)
    result["trade_count"] = sum((r.get("trade_count") or 0) for r in per_results)
    agg = _metrics_from_equity_curve(result["equity_curve"])
    result["total_return"] = agg.get("total_return")
    result["max_drawdown"] = agg.get("max_drawdown")
    result["sharpe_ratio"] = agg.get("sharpe_ratio")
    # 加权平均 win_rate / profit_factor 或从合并曲线不重算则保留简单平均
    wrs = [r.get("win_rate_pct") for r in per_results if r.get("win_rate_pct") is not None]
    pfs = [r.get("profit_factor") for r in per_results if r.get("profit_factor") is not None]
    result["win_rate_pct"] = sum(wrs) / len(wrs) if wrs else None
    result["profit_factor"] = sum(pfs) / len(pfs) if pfs else None
    return result
