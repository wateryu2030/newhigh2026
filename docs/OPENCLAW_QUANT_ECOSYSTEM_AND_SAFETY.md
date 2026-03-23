# OpenClaw 量化投研：生态技能与安全实践

OpenClaw 在量化投研场景下可显著降低搭建 AI 投研系统的门槛、提高自动化程度，使「一人量化团队」成为可能。个人投资者、金融工程师、券商研究员与小型量化工作室均可借此快速迭代策略与研报流程。**工具越强，越需要清晰的风险认知与严格的安全规范。**

---

## 一、量化投研常用 Skill 一键安装（金融向示例）

以下命令在 **OpenClaw 容器内**执行（示例）：

```bash
docker exec -it openclaw bash
npm install -g clawhub
```

以下为**营销/教程里常见的示意命令**；**截至核查时（ClawHub 站点 SSR）**，下列 slug 在 `https://clawhub.ai/skills/<name>` 上均为 **`owner:"skills"` 且 `displayName`/`initialData` 为空**，更像是**占位页**，**不能视为已验证可安装的官方包**。安装前请在 ClawHub 内 **搜索、看作者、读安全扫描、试 `clawhub search <关键词>`**，以 CLI/网页实际结果为准。

```bash
# ⚠️ 以下为示意名称，安装前请自行在 ClawHub 核实是否存在、作者是谁、是否 Suspicious
# clawhub install market-data-fetcher
# clawhub install strategy-generator
# clawhub install backtest-runner
# clawhub install research-parser
# clawhub install announcement-crawler
# clawhub install report-exporter
# clawhub install scheduled-task
```

**在 ClawHub 上能查到元数据的「市场数据」类示例（仍须自行审代码与安全标签）**：

- `open-market-data`（作者 `anotb`）— 站点上有完整 `displayName` / `initialData`。
- `crypto-market-data`（作者 `Liam8`）— 同上；偏加密与部分权益市场，**不等同 A 股专用**。

```bash
# 启用所有技能（按环境与需求评估后再执行；强烈不建议生产 blindly --all）
openclaw skills enable --all
openclaw skills list
```

> **说明**：生产环境建议**按需启用**，避免 `enable --all` 扩大攻击面与资源占用；参阅本仓库 [`CLAWHUB_A_STOCK_MONITOR_INTEGRATION.md`](./CLAWHUB_A_STOCK_MONITOR_INTEGRATION.md) 对部分 ClawHub 技能 **Suspicious** 的说明。

---

## 二、量化场景指令示例

1. **选股策略**  
   例如：筛选近 5 年 ROE &gt; 15%、营收增速 &gt; 10%、PE &lt; 30 的股票，并输出 Excel。

2. **研报复现**  
   解析研报 → 提取核心因子 → 生成回测代码 → 输出净值曲线（需人工校验逻辑与数据对齐）。

3. **每日公告汇总**  
   定时（如每日 17:00）抓取 A 股公告，提炼重大利好、业绩预告、资产重组等，生成简报推送。

4. **数据监控**  
   例如监控沪深300成分股，成交量放大超过阈值（如 5 倍）时提醒。

---

## 三、安全铁律（建议全员遵守）

1. **勿在主力机/主力账户环境直接部署**  
   使用独立服务器或隔离设备，与重要数据、密钥解耦。

2. **强制沙箱与最小权限**  
   限制文件访问范围，禁止随意访问系统敏感目录。

3. **禁止明文存储交易与券商密钥**  
   交易密码、券商 API Key 等不得写入 OpenClaw 工作目录或版本库；使用密钥管理服务或环境注入。

4. **收敛高危命令**  
   禁用或严格审计 `rm`、`sudo`、磁盘格式化、系统级修改等高风险操作。

5. **定期备份**  
   策略、配置、报告等应纳入自动化备份与恢复演练。

6. **不信任模型直接给出的投资结论**  
   模型存在幻觉与过拟合叙述；**所有实盘或资金相关决策须经人工复核**。

---

## 四、常见问题（FAQ）

| 现象 | 可能原因与处理 |
|------|----------------|
| 无法访问 Web 控制台 | 安全组未放行 **18789**；容器未启动 `docker start openclaw`；端口冲突时更换映射端口。 |
| 数据获取失败、行情拉取异常 | 网络出站策略；数据源接口变更；Skill 配置缺失或 Token 失效。 |
| 策略代码报错、回测失败 | 生成代码逻辑错误；数据路径或频率不一致；依赖未安装或版本冲突。 |
| CPU/内存占用过高 | 大规模回测或并发任务；关闭无用 Skill；扩容或任务排队限流。 |
| 担心数据泄露与权限风险 | 开启沙箱与路径白名单；禁用高危命令；**不存放真实交易密钥**；隔离部署。 |

---

## 五、与本仓库的关系

- **本项目内 A 股数据 Skill**（Tushare、Gateway 路由等）见 [`OPENCLAW_SKILLS.md`](./OPENCLAW_SKILLS.md)。  
- **本地自检与任务编排**可参考 [`OPENCLAW_LOCAL_CHECK.md`](./OPENCLAW_LOCAL_CHECK.md)、[`CURSOR_OPENCLAW_TASKS.md`](./CURSOR_OPENCLAW_TASKS.md)。

---

## 六、总结

OpenClaw 类工具往往具备较高系统权限，必须在**沙箱、隔离、权限收敛**前提下使用：不在主力设备裸奔部署，不明文存放交易密钥与敏感数据。**工具可以替代重复劳动，无法替代人的判断与风控。** 在人与 AI 协作中，守住边界、掌握主动权，才是量化场景下的长期优势。
