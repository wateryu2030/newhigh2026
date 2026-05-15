# 任务：桌面 Web → 微信小程序能力对齐（OpenClaw 调度优先）

## 背景

桌面端（Next `frontend/`）功能面大于小程序原生实现；当前策略是 **导航单源**（`config/navigation_manifest.json`）+ **原生页 + 内嵌 Web**（`pages/web-page`）。仍可能存在：**未入菜单的 Web 页不可达**、**业务域名未配导致白屏**、**原生页与 `/market` 等 Web 体验不一致**。

## 目标

在**不改坏主仓 Web** 的前提下，让小程序用户能触达**与桌面同域**的核心能力，并分阶段缩小体验差距。

---

## 阶段 P0（运维 / 配置，非代码）

| 项 | 动作 |
|----|------|
| 微信「业务域名」 | 公众平台 → 开发 → 开发管理 → 业务域名：添加 **`htma.newhigh.com.cn`**（与 `utils/htma.js` 的 `BASE` 一致），否则 `web-view` 白屏。 |
| request 合法域名 | 同控制台，确保 Gateway 域名已加，接口可通。 |
| 同步 HEARTBEAT | 若用 OpenClaw 提醒：`bash scripts/sync_openclaw_heartbeat.sh` |

---

## 阶段 P1（已完成 / 本仓已落地）

| 项 | 说明 |
|----|------|
| 菜单单源 | `config/navigation_manifest.json` → `make sync-nav` → `menu.generated.js` |
| 全部功能 | `pages/feature-hub` + `navigateMenuItem` / `openWebPath` |
| 扩展桌面页入口 | `integrations/hongshan/wechat-miniprogram/config/extra_web_paths.js` 在「全部功能」中追加投研/研报/交易/风控/进化等 **Web 内嵌** |

---

## 阶段 P2（可选产品决策）

| 方向 | 说明 |
|------|------|
| **行情 / 策略** 与 Web 完全一致 | 将 manifest 中「行情」「策略」由 `native` 改为 `webview`（`/market`、`/strategies`），再 `make sync-nav`。**代价**：失去纯原生 Tab/列表性能，换同 URL 一致。 |
| 原生页增强 | 在 `pages/quotes`、`pages/strategy` 内逐步对齐 Web 的图表/字段（工作量大，按迭代拆）。 |

---

## 阶段 P3（给 OpenClaw / Cursor 的执行顺序）

1. 读 `integrations/hongshan/wechat-miniprogram/README.md`、`config/extra_web_paths.js`。  
2. 确认 P0 业务域名已配置；用开发者工具真机预览 `web-page` 任一路径。  
3. 若需新增扩展入口：只改 **`extra_web_paths.js`**（勿重复主菜单已在 `navigation_manifest` 中的路径）。  
4. 大改仍走 **`tasks/current_task.md`** 与 `evolution/improvement_log_*.md`。  

---

## 给 OpenClaw 的一行调度提示

```
本轮优先：小程序与桌面能力对齐。仓库 /Users/apple/Ahope/newhigh，必读 tasks/MINIPROGRAM_DESKTOP_PARITY.md；改小程序只动 integrations/hongshan/wechat-miniprogram/ 与 config/navigation_manifest.json（改菜单后 make sync-nav）。桌面合码在 Cursor 完成。
```

---

*与 `docs/OPENCLAW_PLUS_CURSOR_LOOP.md`、`docs/OPENCLAW_ORCHESTRATION.md` §4.5 一致。*
