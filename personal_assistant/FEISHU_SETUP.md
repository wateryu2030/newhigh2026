# 飞书推送配置

个人助手已支持把每日报告推到飞书群。若「跟飞书配对停止」，多半是未配置 **FEISHU_CHAT_ID** 或 OpenClaw 侧飞书插件被关掉了。

---

## ⚠️ 报错「Bot/User can NOT be out of the chat」时必做

**含义**：机器人还没加入这个群，飞书不允许给「不在群里的机器人」发群消息。

**按下面步骤把机器人加进群（在飞书客户端里操作）：**

1. **打开飞书**，进入你要收报告的那个**群聊**（不是私聊）。
2. 点击**群名称**（顶部）→ 进入 **群设置**。
3. 找到 **「群机器人」** 或 **「添加机器人」** / **「机器人」** 入口。
4. 点 **「添加机器人」** → 在列表里选 **「自定义机器人」** 或 **「自建应用」**。
5. 找到你在飞书开放平台创建的那个应用（App ID 对应 `.env` 里的 `FEISHU_APP_ID`），点击**添加**。
6. 添加成功后，回到终端再执行一次：
   ```bash
   cd /Users/apple/Ahope/newhigh/personal_assistant
   python3 src/pusher.py
   ```
   看到 **「✅ 飞书推送成功」** 且群里有一条测试消息即表示正常。

**若列表里没有你的自建应用：**  
先去 [飞书开放平台](https://open.feishu.cn/app) → 你的应用 → **能力** → **机器人**，确认已启用「机器人」能力并发布；再在 **权限管理** 里开通「获取与发送群消息」。保存后回飞书群再试「添加机器人」。

---

## 一、本仓库（newhigh 个人助手）推送到飞书群

### 1. 已有 .env 配置

- `FEISHU_APP_ID`、`FEISHU_APP_SECRET` 已存在时，只需补 **群组 ID**（`FEISHU_CHAT_ID`）。

### 2. 获取群组 ID（FEISHU_CHAT_ID）

1. 在飞书里打开要接收报告的**群聊**。
2. 点击群名称进入 **群设置**。
3. 在「群组 ID」或「群聊 ID」处复制，形如：`oc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`。
4. 在项目根目录的 `.env` 中增加或修改（**不要在同一行写 # 注释**，否则可能读不到）：
   ```bash
   FEISHU_CHAT_ID=oc_你复制的群组ID
   ```
5. **必须**在该群里**添加你的自建应用机器人**（见上文「Bot/User can NOT be out of the chat」步骤）。

### 3. 应用权限

在 [飞书开放平台](https://open.feishu.cn/app) 你的应用里开启：

- **获取与发送群消息**（或 发送消息 相关权限）。

### 4. 测试

```bash
cd /Users/apple/Ahope/newhigh/personal_assistant
python3 src/pusher.py
```

若配置正确，会看到「✅ 飞书推送成功」（测试内容会发到群里）。

---

## 二、OpenClaw 的飞书插件

若你指的是 **OpenClaw** 里的飞书（例如会话、机器人），那是另一套配置：

- 配置目录：`~/.openclaw/`，其中的 `openclaw.json` 或插件配置里，**feishu** 当前为 **enabled: false**（已关闭）。
- 要恢复「配对」，需要在 OpenClaw 的配置里把飞书插件改为 **enabled: true**，并填好对应 App ID / Secret 等（参见 OpenClaw 文档）。

---

## 三、小结

| 场景           | 处理方式 |
|----------------|----------|
| 个人助手推送到飞书群 | 配置 `.env` 的 `FEISHU_CHAT_ID`，并把机器人加入该群 |
| OpenClaw 飞书机器人 | 在 `~/.openclaw/` 中开启 feishu 插件并配置 |
