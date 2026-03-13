"""Tushare 日 K 线数据收集器"""
from __future__ import annotations
import os
from datetime import datetime, timedelta
from typing import Optional

from ..storage.duckdb_manager import get_conn, ensure_tables


def update_tushare_daily(
    code: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    adjust: str = "qfq"
) -> int:
    """
    使用 Tushare 更新日 K 线数据
    
    Args:
        code: 股票代码，如 "000001" 或 "600519"，None 表示更新所有股票
        start_date: 开始日期，格式 "YYYYMMDD"，None 表示最近30天
        end_date: 结束日期，格式 "YYYYMMDD"，None 表示今天
        adjust: 复权类型，"qfq"（前复权）、"hfq"（后复权）、""（不复权）
    
    Returns:
        更新的数据条数
    """
    # 检查 Tushare Token
    token = os.environ.get("TUSHARE_TOKEN", "").strip()
    if not token:
        print("⚠ 未设置 TUSHARE_TOKEN 环境变量，跳过 Tushare 数据更新")
        print("  请在 .env 文件中设置 TUSHARE_TOKEN=你的token")
        return 0
    
    try:
        import tushare as ts
        import pandas as pd
    except ImportError:
        print("⚠ Tushare 或 pandas 未安装，跳过 Tushare 数据更新")
        print("  请运行: pip install tushare pandas")
        return 0
    
    # 初始化 Tushare
    try:
        ts.set_token(token)
        pro = ts.pro_api()
    except Exception as e:
        print(f"✗ Tushare 初始化失败: {e}")
        return 0
    
    # 设置日期范围
    if not end_date:
        end_date = datetime.now().strftime("%Y%m%d")
    
    if not start_date:
        # 默认获取最近30天数据
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
    
    # 获取数据库连接
    conn = get_conn()
    ensure_tables(conn)
    
    # 确定要更新的股票代码
    codes_to_update = []
    if code:
        codes_to_update.append(code)
    else:
        # 从数据库获取所有股票代码
        try:
            df = conn.execute("SELECT DISTINCT code FROM a_stock_basic").fetchdf()
            if df is not None and not df.empty:
                codes_to_update = df["code"].tolist()
                print(f"📊 将更新 {len(codes_to_update)} 只股票的 Tushare 数据")
            else:
                print("⚠ 数据库中没有股票代码，请先运行股票池更新")
                return 0
        except Exception as e:
            print(f"⚠ 获取股票代码失败: {e}")
            return 0
    
    total_rows = 0
    
    # 分批处理，避免内存过大
    batch_size = 50
    for i in range(0, len(codes_to_update), batch_size):
        batch_codes = codes_to_update[i:i + batch_size]
        batch_ts_codes = []
        
        # 转换为 Tushare 格式的代码
        for c in batch_codes:
            c = str(c).strip()
            if not c:
                continue
            # 标准化代码格式
            if c.startswith("6"):
                ts_code = f"{c}.SH"
            elif c.startswith(("0", "3")):
                ts_code = f"{c}.SZ"
            elif c.startswith(("4", "8", "9")) or len(c) == 8:
                ts_code = f"{c}.BSE"
            else:
                continue
            batch_ts_codes.append(ts_code)
        
        if not batch_ts_codes:
            continue
        
        try:
            # 批量获取数据
            print(f"🔄 获取批次 {i//batch_size + 1}/{(len(codes_to_update)-1)//batch_size + 1}: {len(batch_ts_codes)} 只股票")
            
            # 使用 Tushare 的批量接口
            df = pro.daily(
                ts_code=",".join(batch_ts_codes),
                start_date=start_date,
                end_date=end_date
            )
            
            if df is None or df.empty:
                print(f"⚠ 批次 {i//batch_size + 1} 未获取到数据")
                continue
            
            # 处理数据
            df = df.copy()
            df["code"] = df["ts_code"].str.split(".").str[0]  # 提取纯数字代码
            df["date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d").dt.date
            
            # 重命名列以匹配数据库
            df = df.rename(columns={
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "vol": "volume",
                "amount": "amount"
            })
            
            # 选择需要的列
            cols = ["code", "date", "open", "high", "low", "close", "volume", "amount"]
            for col in cols:
                if col not in df.columns:
                    df[col] = None
            
            df = df[cols]
            
            # 写入数据库
            conn.register("tmp_tushare_daily", df)
            result = conn.execute("""
                INSERT INTO a_stock_daily (code, date, open, high, low, close, volume, amount)
                SELECT code, date, open, high, low, close, volume, amount FROM tmp_tushare_daily
                ON CONFLICT (code, date) DO UPDATE SET
                open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low, 
                close=EXCLUDED.close, volume=EXCLUDED.volume, amount=EXCLUDED.amount
            """)
            
            rows_updated = result.rowcount
            total_rows += rows_updated
            
            print(f"✓ 批次 {i//batch_size + 1} 更新 {rows_updated} 条数据")
            
            # 避免频率限制
            import time
            time.sleep(1)  # Tushare 有频率限制
            
        except Exception as e:
            print(f"✗ 批次 {i//batch_size + 1} 处理失败: {e}")
            continue
    
    conn.close()
    
    if total_rows > 0:
        print(f"✅ Tushare 日 K 线数据更新完成: 共更新 {total_rows} 条数据")
    else:
        print("ℹ️ Tushare 日 K 线数据更新完成: 无新数据")
    
    return total_rows


def update_all_tushare_daily(
    days_back: int = 30,
    adjust: str = "qfq"
) -> int:
    """
    更新所有股票的 Tushare 日 K 线数据
    
    Args:
        days_back: 获取多少天内的数据
        adjust: 复权类型
    
    Returns:
        更新的数据条数
    """
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d")
    
    print(f"🔄 开始更新 Tushare 日 K 线数据")
    print(f"   时间范围: {start_date} 到 {end_date}")
    print(f"   复权类型: {adjust}")
    
    return update_tushare_daily(
        code=None,
        start_date=start_date,
        end_date=end_date,
        adjust=adjust
    )


if __name__ == "__main__":
    # 命令行测试
    import sys
    
    if len(sys.argv) > 1:
        # 更新指定股票
        code = sys.argv[1]
        start_date = sys.argv[2] if len(sys.argv) > 2 else None
        end_date = sys.argv[3] if len(sys.argv) > 3 else None
        
        rows = update_tushare_daily(code, start_date, end_date)
        print(f"更新 {code} 完成: {rows} 条数据")
    else:
        # 更新所有股票（最近30天）
        rows = update_all_tushare_daily(days_back=30)
        print(f"更新所有股票完成: {rows} 条数据")