# 微信推送配置指南

## 1. 获取 Server 酱 SendKey（2 分钟）

### 步骤：
1. 打开微信，扫码登录：https://sct.ftqq.com/
2. 登录后，点击 **"SendKey"** 标签
3. 复制你的 SendKey（格式类似：`SCTxxxxxxxxxxxxxxxx`）

### 截图指引：
```
https://sct.ftqq.com/
    ↓
微信扫码登录
    ↓
点击 "SendKey"
    ↓
复制 SendKey
```

## 2. 配置到项目（1 分钟）

### 方式一：告诉我 SendKey（推荐）
直接把你的 SendKey 发给我，我帮你配置好。

### 方式二：自己配置
在终端执行：
```bash
echo "SERVERCHAN_SENDKEY=你的 SendKey" >> /Users/apple/Ahope/newhigh/.env
```

## 3. 测试推送（1 分钟）

配置完成后，运行测试：
```bash
cd /Users/apple/Ahope/newhigh/personal_assistant
python3 src/pusher.py
```

如果看到 "✅ 微信推送成功"，就配置完成了！

## 4. 绑定微信接收

在 Server 酱后台：
1. 点击 "微信" 标签
2. 关注 "方糖" 公众号
3. 绑定你的微信

这样就能收到推送了！

---

**现在请操作第 1 步**：
1. 访问 https://sct.ftqq.com/
2. 微信扫码登录
3. 复制 SendKey
4. 把 SendKey 发给我

我帮你完成后续配置！👍
