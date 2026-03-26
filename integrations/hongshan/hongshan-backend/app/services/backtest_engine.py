"""
双均线策略回测引擎
"""
import pandas as pd
import numpy as np
from datetime import date, timedelta
from typing import List, Dict, Any
import akshare as ak


def get_stock_data(symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
    """获取股票历史数据"""
    df = ak.stock_zh_a_hist(
        symbol=symbol,
        period="daily",
        start_date=start_date.strftime("%Y%m%d"),
        end_date=end_date.strftime("%Y%m%d"),
        adjust="qfq"
    )
    
    if df.empty:
        return pd.DataFrame()
    
    # 重命名列
    df = df.rename(columns={
        '日期': 'date',
        '开盘': 'open',
        '最高': 'high',
        '最低': 'low',
        '收盘': 'close',
        '成交量': 'volume',
        '成交额': 'amount'
    })
    
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    
    return df


def calculate_ma(df: pd.DataFrame, short_window: int = 5, long_window: int = 20) -> pd.DataFrame:
    """计算移动平均线"""
    df = df.copy()
    df['ma_short'] = df['close'].rolling(window=short_window).mean()
    df['ma_long'] = df['close'].rolling(window=long_window).mean()
    return df


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """生成交易信号"""
    df = df.copy()
    
    # 金叉：短周期上穿长周期
    df['signal'] = 0
    df['signal'] = np.where(df['ma_short'] > df['ma_long'], 1, 0)
    
    # 交易信号：1-买入，-1-卖出
    df['positions'] = df['signal'].diff()
    
    return df


def run_backtest(
    df: pd.DataFrame,
    initial_capital: float = 500000,
    commission_rate: float = 0.0003,
    stamp_tax_rate: float = 0.001
) -> Dict[str, Any]:
    """执行回测"""
    capital = initial_capital
    position = 0
    trades = []
    portfolio_values = []
    
    for i, row in df.iterrows():
        if pd.isna(row['positions']):
            continue
            
        # 买入信号
        if row['positions'] == 1 and capital > 0:
            # 计算可买数量（100 股的整数倍）
            shares = int(capital / row['close'] / 100) * 100
            if shares >= 100:
                cost = shares * row['close']
                commission = cost * commission_rate
                total_cost = cost + commission
                
                if total_cost <= capital:
                    capital -= total_cost
                    position = shares
                    trades.append({
                        'date': i,
                        'type': 'buy',
                        'price': row['close'],
                        'shares': shares,
                        'cost': total_cost
                    })
        
        # 卖出信号
        elif row['positions'] == -1 and position > 0:
            revenue = position * row['close']
            commission = revenue * commission_rate
            stamp_tax = revenue * stamp_tax_rate
            net_revenue = revenue - commission - stamp_tax
            
            capital += net_revenue
            trades.append({
                'date': i,
                'type': 'sell',
                'price': row['close'],
                'shares': position,
                'revenue': net_revenue
            })
            position = 0
        
        # 计算组合价值
        portfolio_value = capital + (position * row['close'] if position > 0 else 0)
        portfolio_values.append({
            'date': i,
            'value': portfolio_value
        })
    
    # 计算收益指标
    portfolio_df = pd.DataFrame(portfolio_values)
    portfolio_df.set_index('date', inplace=True)
    
    total_return = (portfolio_df['value'].iloc[-1] - initial_capital) / initial_capital * 100
    
    # 年化收益
    days = (portfolio_df.index[-1] - portfolio_df.index[0]).days
    annual_return = ((1 + total_return/100) ** (365/days) - 1) * 100 if days > 0 else 0
    
    # 夏普比率
    daily_returns = portfolio_df['value'].pct_change().dropna()
    sharpe_ratio = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if daily_returns.std() > 0 else 0
    
    # 最大回撤
    rolling_max = portfolio_df['value'].cummax()
    drawdown = (portfolio_df['value'] - rolling_max) / rolling_max
    max_drawdown = drawdown.min() * 100
    
    # 交易统计
    total_trades = len(trades)
    buy_trades = [t for t in trades if t['type'] == 'buy']
    sell_trades = [t for t in trades if t['type'] == 'sell']
    
    # 计算胜率
    winning_trades = 0
    if len(sell_trades) > 0 and len(buy_trades) > 0:
        for i, sell in enumerate(sell_trades):
            if i < len(buy_trades):
                if sell['revenue'] > buy_trades[i]['cost']:
                    winning_trades += 1
    
    win_rate = (winning_trades / len(sell_trades) * 100) if sell_trades else 0
    
    return {
        'total_return': round(total_return, 4),
        'annual_return': round(annual_return, 4),
        'sharpe_ratio': round(sharpe_ratio, 4),
        'max_drawdown': round(max_drawdown, 4),
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'win_rate': round(win_rate, 4),
        'final_capital': round(portfolio_df['value'].iloc[-1], 2),
        'portfolio_values': portfolio_df.to_dict('records')
    }


def run_ma_cross_backtest(
    symbols: List[str],
    start_date: date,
    end_date: date,
    initial_capital: float = 500000,
    params: Dict[str, Any] = None
) -> Dict[str, Any]:
    """运行双均线策略回测"""
    if params is None:
        params = {'short_window': 5, 'long_window': 20}
    
    short_window = params.get('short_window', 5)
    long_window = params.get('long_window', 20)
    
    results = []
    
    for symbol in symbols:
        try:
            # 获取数据
            df = get_stock_data(symbol, start_date, end_date)
            if df.empty:
                continue
            
            # 计算均线
            df = calculate_ma(df, short_window, long_window)
            
            # 生成信号
            df = generate_signals(df)
            
            # 执行回测
            result = run_backtest(df, initial_capital / len(symbols))
            
            result['symbol'] = symbol
            results.append(result)
            
        except Exception as e:
            print(f"回测 {symbol} 失败：{e}")
            continue
    
    # 汇总结果
    if not results:
        return {
            'total_return': 0,
            'annual_return': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'total_trades': 0,
            'win_rate': 0
        }
    
    # 简单平均
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
    result = run_ma_cross_backtest(
        symbols=['600519'],
        start_date=date(2025, 1, 1),
        end_date=date(2026, 3, 26),
        initial_capital=500000,
        params={'short_window': 5, 'long_window': 20}
    )
    
    print("=" * 50)
    print("双均线策略回测结果")
    print("=" * 50)
    print(f"总收益率：{result['total_return']}%")
    print(f"年化收益：{result['annual_return']}%")
    print(f"夏普比率：{result['sharpe_ratio']}")
    print(f"最大回撤：{result['max_drawdown']}%")
    print(f"交易次数：{result['total_trades']}")
    print(f"胜率：{result['win_rate']}%")
    print("=" * 50)
