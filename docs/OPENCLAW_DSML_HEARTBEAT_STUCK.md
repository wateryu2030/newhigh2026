# OpenClaw 总出现 DSML read HEARTBEAT.md、迭代无进展 — 原因与对策

## 现象

聊天或心跳里反复出现类似：

`read` → `/Users/apple/.openclaw/workspace/HEARTBEAT.md`

后面没有读主仓、没有改文件、没有命令输出，开发像停住。

## 原因（简要）

1. **系统指令**：OpenClaw 常要求 Agent **先读** `HEARTBEAT.md`（与 `docs/OPENCLAW_SELF_DEV.md` 一致）。  
2. **单步即止**：部分模型在第一次 `read` 成功后就满足「完成心跳」，回复 **`HEARTBEAT_OK`**，不再发起后续工具。  
3. **相对路径踩坑**：`HEARTBEAT` 正文里若写 `docs/OPENCLAW_ORCHESTRATION.md`（无 `newhigh/`），工作区根是 **`~/.openclaw/workspace`**，会去读**不存在的** `workspace/docs/...`，导致读失败或绕圈。  
4. **DSML 外露**：只是工具调用的展示格式，**不是**错误；问题在于**工具链是否在第一步之后就断了**。

## 对策（已写入主仓 HEARTBEAT 模板）

仓库 **`docs/openclaw/HEARTBEAT_AUTONOMOUS.md`** 开篇已增加 **「最高优先级」** 段：读完 `HEARTBEAT.md` 后**必须**再 `read` 主仓的 `tasks/current_task.md`（**绝对路径**或 `newhigh/...`），并禁止「只读 HEARTBEAT 就 OK」。

同步到本机 OpenClaw：

```bash
bash /Users/apple/Ahope/newhigh/scripts/sync_openclaw_heartbeat.sh
```

并 **重启 OpenClaw / Gateway**，新心跳才读新版 `HEARTBEAT.md`。

## 你仍可手动补一刀（会话首条）

粘贴 `docs/OPENCLAW_AUTONOMOUS_DEVELOPMENT_SETUP.md` **§五** 的强制提示词，要求：先 `read` **`/Users/apple/Ahope/newhigh/tasks/current_task.md`**，再给出「改哪些文件 + 命令」。

## 与 Cursor 分工

复杂合码、长跑测试仍在 **Cursor**；OpenClaw 心跳适合 **提醒 + 一条可验证小步**，不要指望单靠心跳轮次自动推满整个平台开发。

---

*与 `docs/openclaw/HEARTBEAT_AUTONOMOUS.md` §G 互补。*
