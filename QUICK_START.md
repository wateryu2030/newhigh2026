# 📰 新闻采集器 - 快速配置指南

**状态**: ✅ 采集器已安装并测试通过  
**待完成**: 配置定时任务 + API Key

---

## ✅ 已完成

1. **采集器已安装**: `/Users/apple/Ahope/newhigh/api_news_collector.py`
2. **测试通过**: 成功采集 62 条真实新闻（新浪财经 50 条 + RSS 12 条）
3. **数据库已更新**: 去重逻辑正常工作
4. **依赖已安装**: requests, feedparser

---

## ⏰ 待完成 1: 配置定时任务

由于系统限制，crontab 需要手动配置。请执行以下命令：

```bash
# 1. 编辑 crontab
crontab -e

# 2. 添加以下 3 行（在文件末尾）
# 新闻采集 - 早间 (6:00)
0 6 * * * cd /Users/apple/Ahope/newhigh && source .venv/bin/activate && python3 api_news_collector.py >> logs/news_api/cron_morning.log 2>&1

# 新闻采集 - 午间 (12:00)
0 12 * * * cd /Users/apple/Ahope/newhigh && source .venv/bin/activate && python3 api_news_collector.py >> logs/news_api/cron_noon.log 2>&1

# 新闻采集 - 晚间 (18:00)
0 18 * * * cd /Users/apple/Ahope/newhigh && source .venv/bin/activate && python3 api_news_collector.py >> logs/news_api/cron_evening.log 2>&1

# 3. 保存并退出（vi: :wq 或 nano: Ctrl+X, Y, Enter）

# 4. 验证
crontab -l | grep news
```

---

## 🔑 待完成 2: 配置聚合数据 API Key（推荐）

**好处**: 更稳定的中文财经新闻源，每日 100 次免费额度

### 步骤：

**1. 注册账号**
- 访问：https://www.juhe.cn/
- 点击右上角"注册"
- 完成手机验证

**2. 申请 API**
- 登录后访问：https://www.juhe.cn/docs/api/id/235
- 点击"立即订阅"
- 选择免费版（100 次/天）
- 提交申请

**3. 获取 API Key**
- 访问：https://www.juhe.cn/console
- 找到"今日头条"API
- 复制 API Key（类似：abc123def456...）

**4. 添加到 .env 文件**
```bash
# 方法 1: 命令行
echo "JUHE_API_KEY=你的 API_Key_在这里" >> /Users/apple/Ahope/newhigh/.env

# 方法 2: 手动编辑
vi /Users/apple/Ahope/newhigh/.env
# 添加一行：JUHE_API_KEY=你的 API_Key_在这里
```

**5. 验证配置**
```bash
cd /Users/apple/Ahope/newhigh
source .venv/bin/activate
python3 api_news_collector.py
# 应该看到"✅ 获取 XX 条财经新闻"（聚合数据）
```

---

## 🧪 手动测试采集器

```bash
cd /Users/apple/Ahope/newhigh
source .venv/bin/activate
python3 api_news_collector.py
```

**预期输出**:
```
✅ 采集任务完成!
📊 采集统计:
  新浪财经：50 条
  RSS 源：12 条
  总计：62 条
  入库：X 条（去重后）
```

---

## 📊 查看采集结果

```bash
# 查看最新 10 条新闻
cd /Users/apple/Ahope/newhigh
source .venv/bin/activate
python3 -c "
import duckdb
conn = duckdb.connect('data/quant_system.duckdb')
result = conn.execute('''
    SELECT title, source, publish_time 
    FROM news_items 
    WHERE id IS NOT NULL
    ORDER BY ts DESC 
    LIMIT 10
''').fetchall()
for row in result:
    print(f'{row[0][:50]} | {row[1]} | {row[2]}')
conn.close()
"
```

---

## 📁 相关文件

| 文件 | 说明 |
|------|------|
| `api_news_collector.py` | 主程序 |
| `NEWS_API_SETUP.md` | 详细配置文档 |
| `install_news_cron.sh` | 自动安装脚本（可选） |
| `logs/news_api/` | 执行日志 |

---

## ❓ 常见问题

**Q: 为什么没有配置聚合数据 API？**  
A: 需要您亲自注册获取 API Key（免费），这是为了保护您的账号安全。

**Q: 定时任务不执行怎么办？**  
A: 检查 cron 日志：`tail -f /var/log/system.log | grep cron`

**Q: 如何查看历史采集记录？**  
A: 查看日志文件：`ls -lt logs/news_api/run_*.json`

---

**创建时间**: 2026-03-21 06:35 AM  
**下次采集**: 配置后将于 6:00/12:00/18:00 自动执行
