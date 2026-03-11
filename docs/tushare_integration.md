# Tushare 集成文档

## 概述

Tushare 是一个提供中国金融市场数据的 Python 接口，包含股票、基金、期货、期权等数据。本文档介绍如何将 Tushare 集成到量化交易平台中。

## 安装与配置

### 1. 安装依赖

```bash
pip install tushare pandas
```

### 2. 获取 Token

1. 访问 [Tushare Pro](https://tushare.pro) 注册账号
2. 完成实名认证（获取更多数据权限）
3. 在个人中心获取 Token

### 3. 配置环境变量

```bash
export TUSHARE_TOKEN="你的token"
```

或在 `.env` 文件中添加：
```
TUSHARE_TOKEN=你的token
```

## 数据连接器

### 文件位置
```
data-engine/src/data_engine/connector_tushare.py
```

### 主要功能

#### 1. 获取K线数据
```python
from data_engine.src.data_engine import connector_tushare as tushare

# 获取日线数据
ohlcv_list = tushare.fetch_ohlcv(
    code='000001',           # 股票代码
    start_date='20240101',   # 开始日期
    end_date='20240131',     # 结束日期
    period='daily',          # 周期：daily, weekly, monthly
    adjust=''                # 复权类型：qfq(前复权), hfq(后复权), ''(不复权)
)

# 返回 OHLCV 对象列表
for ohlcv in ohlcv_list:
    print(f"{ohlcv.timestamp}: 收盘价 {ohlcv.close}, 成交量 {ohlcv.volume}")
```

#### 2. 获取股票基本信息
```python
import tushare as ts
ts.set_token(os.getenv('TUSHARE_TOKEN'))
pro = ts.pro_api()

# 获取所有上市股票
df = pro.stock_basic(
    exchange='', 
    list_status='L',
    fields='ts_code,symbol,name,area,industry,list_date,market,is_hs'
)
```

#### 3. 获取财务数据
```python
# 获取利润表
income_df = tushare.fetch_financial_data('000001', 'income', '20230101', '20231231')

# 获取资产负债表
balance_df = tushare.fetch_financial_data('000001', 'balancesheet', '20230101', '20231231')

# 获取现金流量表
cashflow_df = tushare.fetch_financial_data('000001', 'cashflow', '20230101', '20231231')
```

#### 4. 获取实时行情
```python
# 获取实时行情（需要相应权限）
realtime_df = tushare.fetch_realtime_quotes(['000001', '000002', '600000'])
```

## 与现有系统集成

### 1. 数据管道集成

修改 `data_pipeline.py`，添加 Tushare 数据源：

```python
# 在现有数据源基础上添加
from data_engine.src.data_engine.connector_tushare import fetch_ohlcv

class TushareDataSource:
    def __init__(self):
        self.name = "tushare"
        
    def fetch_data(self, symbol, start_date, end_date, frequency='daily'):
        """获取数据"""
        return fetch_ohlcv(symbol, start_date, end_date, frequency)
```

### 2. 定时任务配置

创建定时获取任务，每天收盘后自动更新数据：

```python
# scripts/scheduled_tasks/tushare_daily_update.py
from datetime import datetime, timedelta
from data_engine.src.data_engine import connector_tushare as tushare

def daily_update():
    """每日数据更新"""
    # 获取当前日期
    today = datetime.now().strftime('%Y%m%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    
    # 获取股票列表
    import tushare as ts
    ts.set_token(os.getenv('TUSHARE_TOKEN'))
    pro = ts.pro_api()
    
    stocks = pro.stock_basic(list_status='L')['ts_code'].tolist()
    
    # 批量获取数据
    for stock in stocks[:10]:  # 示例：前10只股票
        try:
            data = tushare.fetch_ohlcv(stock, yesterday, today, 'daily')
            # 存储到数据库
            save_to_database(data)
            print(f"更新 {stock} 数据成功")
        except Exception as e:
            print(f"更新 {stock} 数据失败: {e}")
```

### 3. 数据存储

#### 存储到 ClickHouse
```python
from data_engine.src.data_engine.clickhouse_storage import ClickHouseStorage

def save_tushare_data(ohlcv_list):
    """保存Tushare数据到ClickHouse"""
    storage = ClickHouseStorage()
    
    for ohlcv in ohlcv_list:
        storage.insert_ohlcv(
            symbol=ohlcv.code,
            timestamp=ohlcv.timestamp,
            open=ohlcv.open,
            high=ohlcv.high,
            low=ohlcv.low,
            close=ohlcv.close,
            volume=ohlcv.volume,
            amount=ohlcv.amount
        )
```

#### 存储到 DuckDB
```python
from data_engine.src.data_engine.connector_astock_duckdb import save_ohlcv_to_duckdb

def save_to_duckdb(ohlcv_list):
    """保存到DuckDB"""
    for ohlcv in ohlcv_list:
        save_ohlcv_to_duckdb(
            symbol=ohlcv.code,
            date=ohlcv.timestamp.date(),
            open=ohlcv.open,
            high=ohlcv.high,
            low=ohlcv.low,
            close=ohlcv.close,
            volume=ohlcv.volume
        )
```

## 使用示例

### 示例1：策略数据获取
```python
# strategy_engine/strategies/tushare_based_strategy.py
from data_engine.src.data_engine import connector_tushare as tushare

class TushareBasedStrategy:
    def __init__(self):
        self.data_source = "tushare"
    
    def prepare_data(self, symbol, lookback_days=60):
        """准备策略数据"""
        from datetime import datetime, timedelta
        
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y%m%d')
        
        # 获取历史数据
        historical_data = tushare.fetch_ohlcv(
            symbol, start_date, end_date, 'daily'
        )
        
        # 转换为DataFrame
        import pandas as pd
        df = pd.DataFrame([{
            'date': ohlcv.timestamp,
            'open': ohlcv.open,
            'high': ohlcv.high,
            'low': ohlcv.low,
            'close': ohlcv.close,
            'volume': ohlcv.volume
        } for ohlcv in historical_data])
        
        return df
```

### 示例2：基本面分析
```python
# feature_engine/features/fundamental_features.py
from data_engine.src.data_engine import connector_tushare as tushare

def calculate_fundamental_features(symbol):
    """计算基本面特征"""
    # 获取财务数据
    income_df = tushare.fetch_financial_data(symbol, 'income', '20230101', '20231231')
    balance_df = tushare.fetch_financial_data(symbol, 'balancesheet', '20230101', '20231231')
    
    if income_df.empty or balance_df.empty:
        return {}
    
    # 计算财务比率
    latest_income = income_df.iloc[0]
    latest_balance = balance_df.iloc[0]
    
    features = {
        'pe_ratio': calculate_pe_ratio(latest_income, latest_balance),
        'pb_ratio': calculate_pb_ratio(latest_balance),
        'roe': calculate_roe(latest_income, latest_balance),
        'debt_ratio': calculate_debt_ratio(latest_balance)
    }
    
    return features
```

## 性能优化

### 1. 批量获取
```python
def batch_fetch_data(symbols, start_date, end_date):
    """批量获取数据，减少API调用"""
    results = {}
    for symbol in symbols:
        try:
            data = tushare.fetch_ohlcv(symbol, start_date, end_date, 'daily')
            results[symbol] = data
        except Exception as e:
            print(f"获取{symbol}数据失败: {e}")
            results[symbol] = None
    
    return results
```

### 2. 数据缓存
```python
import hashlib
import pickle
import os

def get_cached_data(func, *args, **kwargs):
    """带缓存的数据获取"""
    # 生成缓存键
    cache_key = hashlib.md5(str(args + tuple(kwargs.items())).encode()).hexdigest()
    cache_file = f"/tmp/tushare_cache_{cache_key}.pkl"
    
    # 检查缓存
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            return pickle.load(f)
    
    # 获取新数据
    data = func(*args, **kwargs)
    
    # 保存缓存
    with open(cache_file, 'wb') as f:
        pickle.dump(data, f)
    
    return data
```

### 3. 错误处理与重试
```python
import time
from functools import wraps

def retry_on_failure(max_retries=3, delay=1):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    print(f"尝试 {attempt + 1} 失败: {e}, {delay}秒后重试...")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

@retry_on_failure(max_retries=3, delay=2)
def safe_fetch_ohlcv(*args, **kwargs):
    """安全获取数据，自动重试"""
    return tushare.fetch_ohlcv(*args, **kwargs)
```

## 监控与维护

### 1. API使用监控
```python
def monitor_api_usage():
    """监控API使用情况"""
    import tushare as ts
    ts.set_token(os.getenv('TUSHARE_TOKEN'))
    
    # 获取API使用情况（需要相应权限）
    # 注意：具体实现取决于Tushare API支持
    print("监控API使用情况...")
```

### 2. 数据质量检查
```python
def check_data_quality(data):
    """检查数据质量"""
    if not data:
        return False, "数据为空"
    
    # 检查数据完整性
    required_fields = ['open', 'high', 'low', 'close', 'volume']
    for item in data:
        for field in required_fields:
            if getattr(item, field) <= 0:
                return False, f"数据异常: {field} <= 0"
    
    return True, "数据质量正常"
```

## 故障排除

### 常见问题

1. **Token无效**
   - 检查token是否正确
   - 确认token是否过期
   - 重新生成token

2. **网络连接问题**
   - 检查网络连接
   - 确认Tushare服务状态
   - 添加重试机制

3. **频率限制**
   - 降低请求频率
   - 使用批量获取
   - 升级会员等级

4. **数据权限**
   - 确认账号权限
   - 完成实名认证
   - 申请相应数据权限

### 调试工具
```bash
# 运行测试脚本
python scripts/tushare_demo.py

# 测试连接器
python -c "from data_engine.src.data_engine.connector_tushare import test_tushare_connector; test_tushare_connector()"
```

## 最佳实践

1. **环境隔离**: 为不同环境（开发、测试、生产）配置不同的token
2. **版本控制**: 将token存储在环境变量中，不要提交到代码仓库
3. **错误处理**: 添加完善的错误处理和日志记录
4. **数据验证**: 获取数据后验证数据质量和完整性
5. **性能监控**: 监控API使用情况和数据获取性能
6. **备份策略**: 定期备份重要数据

## 扩展功能

### 1. 多数据源融合
```python
def get_multi_source_data(symbol, start_date, end_date):
    """从多个数据源获取数据"""
    sources = ['tushare', 'akshare', 'yahoo']
    data = {}
    
    for source in sources:
        try:
            if source == 'tushare':
                data[source] = tushare.fetch_ohlcv(symbol, start_date, end_date, 'daily')
            # 添加其他数据源...
        except Exception as e:
            print(f"{source}获取失败: {e}")
    
    return data
```

### 2. 实时数据流
```python
def realtime_data_stream(symbols):
    """实时数据流"""
    # 使用Tushare实时接口
    # 注意：需要相应权限
    pass
```

### 3. 数据质量报告
```python
def generate_data_quality_report():
    """生成数据质量报告"""
    # 分析数据完整性、准确性、及时性
    pass
```

---

**注意**: Tushare API有使用限制，请遵守相关条款，合理使用API资源。对于生产环境，建议使用Tushare Pro版本获取更稳定和全面的数据服务。