# Cursor 接续开发体系

> 让 Cursor 持续接力开发，而不是每次靠人工写长需求。核心是 **架构层 → 任务层 → 提示词层**。

---

## 一、项目结构（Cursor 优先读这些）

```
newhigh/
├── docs/
│   ├── vision.md           # 目标与最终形态 → 先读
│   ├── roadmap.md          # 阶段与优先级
│   ├── architecture.md     # 系统架构（详见 docs/ARCHITECTURE.md）
│   └── CURSOR_RELAY.md     # 本文件：如何接力
│
├── ai/
│   └── prompts/            # AI 角色提示词
│       ├── planner.md      # 拆解任务、排优先级
│       ├── coder.md        # 写代码：Python/TypeScript、模块化
│       ├── reviewer.md     # 代码审查
│       └── quant.md        # 策略/回测/因子设计
│
├── tasks/
│   ├── backlog.md          # 待办列表
│   ├── current_task.md     # 当前要做的任务（Cursor 直接继续）
│   └── task_template.md    # 新任务复制模板
│
├── system_core/            # 统一运行入口
├── data-pipeline/ ...      # 其余见 PROJECT_STATUS.md
```

---

## 二、Cursor 使用方式

**每次打开项目或开始新会话时，可以输入：**

```
读取 docs/vision.md、docs/roadmap.md、tasks/current_task.md，
按 tasks 里的当前任务继续开发。
```

或更短：

```
读 docs 和 tasks，继续开发 current_task。
```

Cursor 将：

1. 从 **vision** 知道系统目标  
2. 从 **roadmap** 知道当前阶段  
3. 从 **current_task** 知道具体要做的事  
4. 需要时可参考 **ai/prompts/** 中的角色（planner/coder/reviewer/quant）  
5. 在对应目录写代码（目录在 current_task 或 backlog 中指明）

---

## 三、六个核心文件

| 文件 | 作用 |
|------|------|
| `docs/vision.md` | AI 必须知道的系统目标 |
| `docs/roadmap.md` | 阶段 1～4，与目录对应 |
| `docs/architecture.md` | 数据/策略/AI/执行/展示层（详见 ARCHITECTURE.md） |
| `tasks/backlog.md` | 待办任务列表，Cursor 从这里挑或补充 |
| `tasks/current_task.md` | **当前任务**，Cursor 直接执行 |
| `tasks/task_template.md` | 新任务时复制填写 |

---

## 四、AI 角色（ai/prompts/）

- **planner**：根据 roadmap + backlog 拆解下一步任务、优先级、实施步骤  
- **coder**：写干净、模块化、可扩展的 Python/TypeScript  
- **reviewer**：检查 bug、性能、风险、代码结构  
- **quant**：设计策略、优化回测、设计因子  

需要时在对话中 @ 或引用对应 prompt 文件。

---

## 五、与现有仓库的对应

- **架构细节**：见 `docs/ARCHITECTURE.md`、`PROJECT_STATUS.md`  
- **数据与进化**：见 `docs/DATA_AND_EVOLUTION.md`  
- **统一运行**：`python -m system_core.system_runner`，见 `system_core/README.md`  
- **数据库**：统一为 `data/quant_system.duckdb`，见 PROJECT_STATUS 第三节  

保持 **vision / roadmap / current_task** 与上述文档一致，AI 就不会迷路。
