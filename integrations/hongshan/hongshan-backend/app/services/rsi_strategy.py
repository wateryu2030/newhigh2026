"""
RSI 策略回测引擎
"""
import pandas as pd
import numpy as np
from datetime import date
from typing import List, Dict, Any
from app.services.backtest_engine import get_stock_data, run_backtest


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """计算 RSI 指标"""
    df = df.copy()
    
    # 计算价格变化
    delta = df['close'].diff()
    
    # 分离上涨和下跌
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # 计算平均涨幅和跌幅
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    # 计算 RS 和 RSI
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    return df


def generate_rsi_signals(df: pd.DataFrame, oversold: int = 30, overbought: int = 70) -> pd.DataFrame:
    """生成 RSI 交易信号"""
    df = df.copy()
    
    # 信号：超卖买入，超买卖出
    df['signal'] = 0
    df.loc[df['rsi'] < oversold, 'signal'] = 1  # 超卖买入
    df.loc[df['rsi'] > overbought, 'signal'] = -1  # 超买卖出
    
    # 交易信号 (信号变化时)
    df['positions'] = 0
    df.loc[(df['signal'] == 1) & (df['signal'].shift(1) != 1), 'positions'] = 1
    df.loc[(df['signal'] == -1) & (df['signal'].shift(1) != -1), 'positions'] = -1
    
    return df


def run_rsi_backtest(
    symbols: List[str],
    start_date: date,
    end_date: date,
    initial_capital: float = 500000,
    params: Dict[str, Any] = None
) -> Dict[str, Any]:
    """运行 RSI 策略回测"""
    if params is None:
        params = {'period': 14, 'oversold': 30, 'overbought': 70}
    
    period = params.get('period', 14)
    oversold = params.get('oversold', 30)
    overbought = params.get('overbought', 70)
    
    results = []
    
    for symbol in symbols:
        try:
            # 获取数据
            df = get_stock_data(symbol, start_date, end_date)
            if df.empty:
                continue
            
            # 计算 RSI
            df = calculate_rsi(df, period)
            
            # 生成信号
            df = generate_rsi_signals(df, oversold, overbought)
            
            # 执行回测
            result = run_backtest(df, initial_capital / len(symbols))
            result['symbol'] = symbol
            results.append(result)
            
        except Exception as e:
            print(f"RSI 回测 {symbol} 失败：{e}")
            continue
    
    if not results:
        return {
            'total_return': 0,
            'annual_return': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'total_trades': 0,
            'win_rate': 0
        }
    
    # 汇总结果
    avg_return = np.mean([r['total_return'] for r in results])
    avg_sharpe = np.mean([r['sharpe_ratio'] for r in results])
    avg_drawdown = np.mean([r['max_drawdown'] for r in results])
    total_trades = sum([r['total_trades'] for r in results])
    avg_win_rate = np.mean([r['win_rate'] for r in results])
    
    return {
        'total_return': round(avg_return, 4),
        'annual_return': round(avg_return * 365 / ((end_date - start_date).days or 1), 4),
        'sharpe_ratio': round(avg_sharpe, 4),
        'max_drawdown': round(avg_drawdown, 4),
        'total_trades': total_trades,
        'win_rate': round(avg_win_rate, 4),
        'symbols': symbols,
        'details': results
    }


# 测试
if __name__ == "__main__":
    result = run_rsi_backtest(
        symbols=['600519'],
        start_date=date(2025, 1, 1),
        end_date=date(2026, 3, 26),
        initial_capital=500000
    )
    
    print("=" * 50)
    print("RSI 策略回测结果")
    print("=" * 50)
    print(f"总收益率：{result['total_return']}%")
    print(f"年化收益：{result['annual_return']}%")
    print(f"夏普比率：{result['sharpe_ratio']}")
    print(f"最大回撤：{result['max_drawdown']}%")
    print(f"交易次数：{result['total_trades']}")
    print(f"胜率：{result['win_rate']}%")
