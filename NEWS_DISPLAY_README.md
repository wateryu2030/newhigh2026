# 📰 新闻展示系统

**部署时间**: 2026-03-17  
**版本**: 1.0.0

---

## 快速启动

### 方式 1: 使用启动脚本 (推荐)
```bash
cd /Users/apple/Ahope/newhigh
./start_news_server.sh
```

### 方式 2: 直接运行
```bash
cd /Users/apple/Ahope/newhigh
.venv/bin/python news_api_server.py --port 8080
```

---

## 访问地址

| 功能 | 地址 | 说明 |
|------|------|------|
| **新闻网页** | http://localhost:8080/news | 📺 可视化新闻列表 |
| 今日新闻 | http://localhost:8080/api/news/today | 📊 JSON 格式今日新闻 |
| 新闻列表 | http://localhost:8080/api/news/list | 📋 分页新闻列表 |
| 个股新闻 | http://localhost:8080/api/news/stock?code=002701 | 📈 个股相关新闻 |
| 统计摘要 | http://localhost:8080/api/news/summary | 📉 统计数据 |
| API 文档 | http://localhost:8080/docs | 📖 Swagger 文档 |

---

## API 接口说明

### 1. 今日新闻
```bash
curl http://localhost:8080/api/news/today
```

**返回示例**:
```json
{
  "date": "2026-03-17",
  "total": 46,
  "by_source": {
    "证券时报": 40,
    "商务部": 6
  },
  "news": [...]
}
```

### 2. 新闻列表 (分页)
```bash
curl "http://localhost:8080/api/news/list?limit=20&offset=0&days=7"
```

**参数**:
- `limit`: 每页数量 (1-200, 默认 50)
- `offset`: 偏移量 (默认 0)
- `days`: 最近 N 天 (1-30, 默认 7)
- `source`: 按来源筛选 (可选)

### 3. 个股新闻
```bash
curl "http://localhost:8080/api/news/stock?code=002701"
```

**支持代码**: 002701, 300212, 600881, 600889 等

### 4. 统计摘要
```bash
curl http://localhost:8080/api/news/summary
```

**返回**:
- 今日统计 (总数、按来源)
- 小时趋势
- 7 天趋势

---

## 网页展示功能

访问 http://localhost:8080/news 查看:

- ✅ 今日新闻总数统计
- ✅ 数据源数量
- ✅ 新闻列表卡片展示
- ✅ 关键词标签
- ✅ 时间戳显示
- ✅ 一键刷新

---

## 集成到现有项目

### Frontend 调用示例

```javascript
// 获取今日新闻
fetch('http://localhost:8080/api/news/today')
  .then(res => res.json())
  .then(data => {
    console.log('今日新闻:', data.total, '条');
    data.news.forEach(news => {
      console.log(news.title);
    });
  });

// 获取个股新闻
fetch('http://localhost:8080/api/news/stock?code=002701')
  .then(res => res.json())
  .then(data => {
    console.log('奥瑞金相关新闻:', data.total, '条');
  });
```

### Python 调用示例

```python
import requests

# 今日新闻
res = requests.get('http://localhost:8080/api/news/today')
data = res.json()
print(f"今日新闻：{data['total']} 条")

# 个股新闻
res = requests.get('http://localhost:8080/api/news/stock?code=002701')
data = res.json()
print(f"奥瑞金新闻：{data['total']} 条")
```

---

## 停止服务器

```bash
# 方式 1: 使用命令
lsof -ti :8080 | xargs kill -9

# 方式 2: 如果在终端运行，按 Ctrl+C
```

---

## 配置说明

### 端口配置
```bash
# 修改端口 (默认 8080)
.venv/bin/python news_api_server.py --port 9000
```

### 地址配置
```bash
# 只监听本地 (更安全)
.venv/bin/python news_api_server.py --host 127.0.0.1

# 监听所有地址 (可远程访问)
.venv/bin/python news_api_server.py --host 0.0.0.0
```

---

## 数据源

新闻数据来自:
- 证券时报 (稳定)
- 东方财富 (待修复)
- 新浪财经 (待修复)
- 政府网站 (待修复)

**数据库**: `data/quant_system.duckdb`  
**表名**: `official_news`

---

## 下一步优化

1. ⏳ 接入 Tushare 新闻 API
2. ⏳ 添加个股新闻自动关联
3. ⏳ 添加新闻情感分析
4. ⏳ 添加实时推送 (WebSocket)
5. ⏳ 添加搜索功能

---

## 故障排查

### 端口被占用
```bash
# 查看占用端口的进程
lsof -i :8080

# 杀死进程
lsof -ti :8080 | xargs kill -9
```

### 数据库不存在
```bash
# 检查数据库文件
ls -la /Users/apple/Ahope/newhigh/data/quant_system.duckdb

# 运行一次新闻采集
.venv/bin/python practical_news_collector.py
```

### 依赖缺失
```bash
# 安装依赖
.venv/bin/pip install fastapi uvicorn duckdb
```

---

**维护者**: OpenClaw 量化系统  
**更新时间**: 2026-03-17
