# 📊 个人量化投资助手

**你的私人 AI 股票分析师** - 每天早上 8 点自动推送股票分析报告

---

## 🎯 产品定位

- **做什么**：每天自动分析 20 只股票，给出投资建议
- **面向谁**：你自己用（可扩展分享给朋友）
- **解决什么**：帮你快速筛选值得关注的股票，避免错过机会，减少情绪化决策

---

## ✨ 核心功能

### 1. 智能选股
- **10 只固定股票**：行业龙头，长期关注
- **10 只动态股票**：每日筛选，捕捉热点
- **混合模式**：既保证稳定性，又不错过机会

### 2. AI 分析
- **DeepSeek AI**：专业股票分析引擎
- **五维分析**：技术面 + 资金面 + 情绪面 + 基本面 + 消息面
- **明确建议**：买入/持有/卖出，带星级评级

### 3. 每日推送
- **微信推送**：Server 酱，即时接收
- **邮件推送**：HTML 格式，美观专业
- **本地保存**：历史记录，便于回顾

### 4. 自动运行
- **每天早上 8 点**：准时推送
- **无需干预**：全自动运行
- **日志记录**：随时查看运行状态

---

## 🚀 快速开始

### 1. 配置微信推送（5 分钟）

运行配置工具：
```bash
cd /Users/apple/Ahope/newhigh/personal_assistant
python3 configure.py
```

按提示操作：
1. 访问 https://sct.ftqq.com/
2. 微信扫码登录
3. 获取 SendKey
4. 输入到配置工具

### 2. 测试运行
```bash
python3 run_daily.py
```

看到"✅ 执行完成"就成功了！

### 3. 查看报告
```bash
# 微信版本
cat reports/report_$(date +%Y-%m-%d).txt

# HTML 版本（在浏览器打开）
open reports/report_$(date +%Y-%m-%d).html
```

### 4. 查看定时任务
```bash
# 查看任务
crontab -l

# 查看日志
tail -f logs/daily_run.log
```

---

## 📁 目录结构

```
personal_assistant/
├── run_daily.py          # 主程序（每天自动运行）
├── configure.py          # 配置工具
├── config.json           # 配置文件
├── .env                  # 环境变量（API Key 等）
├── .env.example          # 环境变量示例
├── README.md             # 本文件
├── src/                  # 源代码
│   ├── stock_screener.py    # 股票筛选器
│   ├── ai_analyzer.py       # AI 分析引擎
│   ├── report_generator.py  # 报告生成器
│   └── pusher.py            # 消息推送器
├── reports/              # 报告输出
│   ├── report_YYYY-MM-DD.txt   # 微信版本
│   ├── report_YYYY-MM-DD.html  # HTML 版本
│   └── analysis_YYYY-MM-DD.json # 数据版本
└── logs/                 # 日志目录
    └── daily_run.log     # 运行日志
```

---

## ⚙️ 配置说明

### 环境变量（.env 文件）

```bash
# 微信推送（Server 酱）
SERVERCHAN_SENDKEY=SCTxxxxxxxxxxxxxxxx

# 邮件推送（可选）
SMTP_SERVER=smtp.qq.com
SMTP_PORT=587
SMTP_USERNAME=your@qq.com
SMTP_PASSWORD=your_auth_code
SMTP_FROM=your@qq.com
SMTP_TO=your@qq.com

# AI 服务
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx

# 数据库
QUANT_SYSTEM_DUCKDB_PATH=/Users/apple/Ahope/newhigh/data/quant_system.duckdb
```

### 配置文件（config.json）

```json
{
  "fixed_stocks": ["600519.XSHG", "000858.XSHE", ...],
  "fixed_count": 10,
  "dynamic_count": 10,
  "db_path": "/path/to/quant_system.duckdb"
}
```

---

## 📊 股票池

### 固定股票池（15 只行业龙头）

**大消费（5 只）**：
- 600519.XSHG - 贵州茅台
- 000858.XSHE - 五粮液
- 000333.XSHE - 美的集团
- 600887.XSHG - 伊利股份
- 000568.XSHE - 泸州老窖

**新能源（3 只）**：
- 300750.XSHE - 宁德时代
- 002594.XSHE - 比亚迪
- 601012.XSHG - 隆基绿能

**科技（3 只）**：
- 002415.XSHE - 海康威视
- 000063.XSHE - 中兴通讯
- 600036.XSHG - 招商银行

**医药（2 只）**：
- 600276.XSHG - 恒瑞医药
- 300122.XSHE - 智飞生物

**其他（2 只）**：
- 601318.XSHG - 中国平安

### 动态股票池
- 每日从全市场筛选
- 基于成交量和涨幅
- 自动剔除 ST 和问题股

---

## 🔧 常用命令

### 运行
```bash
# 手动运行一次
python3 run_daily.py

# 查看今日报告
cat reports/report_$(date +%Y-%m-%d).txt

# 查看历史报告
ls -la reports/
```

### 配置
```bash
# 运行配置工具
python3 configure.py

# 编辑配置
vi config.json
vi .env
```

### 日志
```bash
# 查看运行日志
tail -f logs/daily_run.log

# 查看最近 100 行
tail -100 logs/daily_run.log
```

### 定时任务
```bash
# 查看任务
crontab -l

# 编辑任务
crontab -e

# 删除任务
crontab -r
```

---

## 📈 报告示例

```
📊 每日股票分析 - 2026-03-14

━━━━━━━━━━━━━━━━━━
🔥 重点关注（买入评级）
━━━━━━━━━━━━━━━━━━

1. 贵州茅台 (600519)
   评级：买入 ⭐⭐⭐⭐⭐
   策略：趋势良好，可考虑介入
   理由：技术面突破，资金流入明显
   ⚠️ 风险：大盘波动

2. 宁德时代 (300750)
   评级：买入 ⭐⭐⭐⭐
   策略：新能源板块轮动，逢低布局
   理由：行业前景好，估值合理
   ⚠️ 风险：行业竞争加剧

━━━━━━━━━━━━━━━━━━
👁️ 保持关注（持有评级）
━━━━━━━━━━━━━━━━━━
1. 五粮液 (000858) - 走势平稳，继续持有
2. 比亚迪 (002594) - 等待突破信号

━━━━━━━━━━━━━━━━━━
💡 今日策略建议
━━━━━━━━━━━━━━━━━━
• 重点关注：2 只
• 保持关注：5 只
• 注意风险：0 只

📌 提醒：投资有风险，决策需谨慎
```

---

## ❓ 常见问题

### Q: 微信推送没收到？
A: 
1. 检查 SendKey 是否正确
2. 确认已关注"方糖"公众号
3. 运行 `python3 src/pusher.py` 测试

### Q: 如何修改股票池？
A: 
1. 运行 `python3 configure.py`
2. 选择"配置股票池"
3. 或编辑 `config.json`

### Q: 如何更改推送时间？
A: 
1. 运行 `crontab -e`
2. 修改第一行（0 8 * * * 改为 0 9 * * * 等）

### Q: AI 分析不准怎么办？
A: 
1. 检查 DeepSeek API Key 是否有效
2. 查看日志了解分析详情
3. 可调整提示词或更换 AI 服务

### Q: 数据不准确？
A: 
1. 检查数据库是否最新
2. 运行数据更新脚本
3. 查看数据源是否正常

---

## 📝 更新日志

### v0.1.0 (2026-03-14)
- ✅ 核心功能完成
- ✅ 股票筛选器（混合模式）
- ✅ AI 分析引擎（DeepSeek）
- ✅ 报告生成器（微信 + 邮件）
- ✅ 消息推送（Server 酱 + SMTP）
- ✅ 定时任务（每天早上 8 点）

---

## 🎯 下一步计划

### v0.2.0 (明天)
- [ ] 优化 AI 解析（JSON 格式）
- [ ] 添加业绩跟踪
- [ ] 优化报告格式
- [ ] 完善错误处理

### v0.3.0 (后天)
- [ ] 添加配置界面（Web）
- [ ] 支持多用户
- [ ] 添加回测功能
- [ ] 完善文档

---

## 📞 技术支持

遇到问题？
1. 查看日志：`tail -f logs/daily_run.log`
2. 检查配置：`python3 configure.py`
3. 测试运行：`python3 run_daily.py`

---

**投资有风险，决策需谨慎**

本工具仅供参考，不构成投资建议。
