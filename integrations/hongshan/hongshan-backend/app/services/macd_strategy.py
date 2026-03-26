"""
MACD 策略回测引擎
"""
import pandas as pd
import numpy as np
from datetime import date
from typing import List, Dict, Any
from app.services.backtest_engine import get_stock_data, run_backtest


def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """计算 MACD 指标"""
    df = df.copy()
    
    # 计算 EMA
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
    
    # MACD 线 (DIF)
    df['macd'] = ema_fast - ema_slow
    
    # 信号线 (DEA)
    df['signal'] = df['macd'].ewm(span=signal, adjust=False).mean()
    
    # MACD 柱状图 (MACD Histogram)
    df['histogram'] = df['macd'] - df['signal']
    
    return df


def generate_macd_signals(df: pd.DataFrame) -> pd.DataFrame:
    """生成 MACD 交易信号"""
    df = df.copy()
    
    # 金叉：MACD 线上穿信号线
    df['signal'] = 0
    df.loc[df['macd'] > df['signal'], 'signal'] = 1
    
    # 交易信号
    df['positions'] = df['signal'].diff()
    
    return df


def run_macd_backtest(
    symbols: List[str],
    start_date: date,
    end_date: date,
    initial_capital: float = 500000,
    params: Dict[str, Any] = None
) -> Dict[str, Any]:
    """运行 MACD 策略回测"""
    if params is None:
        params = {'fast': 12, 'slow': 26, 'signal': 9}
    
    fast = params.get('fast', 12)
    slow = params.get('slow', 26)
    signal_period = params.get('signal', 9)
    
    results = []
    
    for symbol in symbols:
        try:
            # 获取数据
            df = get_stock_data(symbol, start_date, end_date)
            if df.empty:
                continue
            
            # 计算 MACD
            df = calculate_macd(df, fast, slow, signal_period)
            
            # 生成信号
            df = generate_macd_signals(df)
            
            # 执行回测
            result = run_backtest(df, initial_capital / len(symbols))
            result['symbol'] = symbol
            results.append(result)
            
        except Exception as e:
            print(f"MACD 回测 {symbol} 失败：{e}")
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
    result = run_macd_backtest(
        symbols=['600519'],
        start_date=date(2025, 1, 1),
        end_date=date(2026, 3, 26),
        initial_capital=500000
    )
    
    print("=" * 50)
    print("MACD 策略回测结果")
    print("=" * 50)
    print(f"总收益率：{result['total_return']}%")
    print(f"年化收益：{result['annual_return']}%")
    print(f"夏普比率：{result['sharpe_ratio']}")
    print(f"最大回撤：{result['max_drawdown']}%")
    print(f"交易次数：{result['total_trades']}")
    print(f"胜率：{result['win_rate']}%")
