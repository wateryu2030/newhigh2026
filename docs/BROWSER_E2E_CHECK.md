# 前端 E2E / 浏览器检测说明

## 0. Node 22 与 OpenClaw（本机已配置）

- **Node 22**：已用 Homebrew 安装 `node@22`，并在 `~/.zshrc` 中加入  
  `export PATH="/opt/homebrew/opt/node@22/bin:$PATH"`，新开终端即可用。
- **OpenClaw**：在 Node 22 下执行 `npm install -g openclaw@latest` 已安装；  
  使用前请先 `export PATH="/opt/homebrew/opt/node@22/bin:$PATH"` 或开新终端。
- **机构组合 / AI 推荐**：两区块已放在页面最上方（header 下），便于自动化快照与点击。

## 1. 不依赖浏览器的快速检测（推荐）

项目内脚本会请求首页并检查「机构组合结果」「AI 推荐列表」等是否出现在 HTML 中，并可选探测 API：

```bash
# 确保平台已启动（如 python3 web_platform.py）
python3 scripts/check_frontend_blocks.py
python3 scripts/check_frontend_blocks.py --base-url http://127.0.0.1:5050
```

通过即表示页面结构和接口可访问正常。

## 2. 使用 Cursor 内置浏览器 MCP（cursor-ide-browser）

若要在 Cursor 内用浏览器自动点击、截图、检测：

1. **确认 MCP 已启用**  
   打开 Cursor 设置 → Features / MCP，确认 **cursor-ide-browser**（或 **user-cursor-ide-browser**）已启用并连接。

2. **使用方式**  
   在对话中让 AI「用浏览器打开 http://127.0.0.1:5050，截一张图 / 点一下加载机构组合」等，AI 会调用：
   - `browser_navigate`：打开 URL
   - `browser_snapshot`：获取可访问性快照（用于定位元素）
   - `browser_click`：按 ref 点击
   - `browser_screenshot`：截图

3. **若工具不可用**  
   - 检查 Cursor 的 MCP 配置中是否包含 cursor-ide-browser，且状态为已连接。
   - 部分环境下 MCP 工具名可能带前缀（如 `mcp_cursor_ide_browser_browser_navigate`），以实际提供的工具名为准。

## 3. 使用 OpenClaw 浏览器（本机已装 Node 22 + OpenClaw）

```bash
# 确保 PATH 含 Node 22（已写入 ~/.zshrc）
export PATH="/opt/homebrew/opt/node@22/bin:$PATH"

# 打开页面并截取快照（机构组合 / AI 推荐在首屏）
openclaw browser --browser-profile openclaw open http://127.0.0.1:5050
openclaw browser --browser-profile openclaw snapshot

# 按快照中的 ref 点击按钮（示例）
openclaw browser --browser-profile openclaw click e9   # 加载机构组合
openclaw browser --browser-profile openclaw click e14  # 加载 AI 推荐
```

## 4. 手动检查清单

- 打开 http://127.0.0.1:5050，强刷（Cmd+Shift+R）。
- 在「运行回测」下方应看到 **机构组合结果**、**AI 推荐列表** 两个卡片。
- 点击「加载机构组合」应出现表格或「暂无订单」等提示。
- 点击「加载 AI 推荐」应出现表格或「未找到已训练模型」等提示。
