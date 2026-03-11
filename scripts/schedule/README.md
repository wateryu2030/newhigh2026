# 定时任务（锁屏/后台自动执行）

使用 macOS **launchd**，在**每周一至五 18:30** 自动执行。只要当前用户已登录（含锁屏状态），到点就会跑，无需保持前台或解锁。

## 方式一：仅全周期（扫描→AI→信号）

**安装**：

在 **newhigh 仓库根目录**执行：

```bash
bash scripts/schedule/install_scheduled_run.sh
```

会完成：

- 创建 `logs/` 目录
- 将 LaunchAgent 安装到 `~/Library/LaunchAgents/com.redmountain.newhigh.fullcycle.plist`
- 加载任务（立即生效，下次 18:30 会跑）

- **执行内容**：`run_full_cycle.py --skip-data`（只跑扫描 + 情绪/狙击/主线 + 融合信号，不拉数据）
- **日志**：`logs/full_cycle.log`

## 方式二：自动化执行（Tushare 拉取 + 全周期）

先拉 Tushare 日 K（需 `.env` 中 `TUSHARE_TOKEN`），再跑全周期（扫描→AI→信号）。适合希望用 Tushare 作为日 K 数据源时使用。

**安装**：

```bash
bash scripts/schedule/install_scheduled_automated.sh
```

- **执行内容**：`run_automated.py`（默认：Tushare 增量 → 全周期 --skip-data）
- **日志**：`logs/automated.log`

**手动执行一次**（不装定时任务也可用）：

```bash
bash scripts/run_automated.sh
# 或
python scripts/run_automated.py
```

可选参数：`--no-tushare`（不拉 Tushare）、`--no-full-cycle`（只拉 Tushare）、`--full-cycle-with-data`（全周期含 akshare 数据填充）。

## 想每天顺带拉数据（方式一）

编辑 plist，去掉 `--skip-data` 参数：

```bash
plutil -replace ProgramArguments -json '["/绝对路径/scripts/schedule/run_scheduled_full_cycle.sh"]' ~/Library/LaunchAgents/com.redmountain.newhigh.fullcycle.plist
# 或直接编辑 plist，把 ProgramArguments 里第二个元素 "--skip-data" 删掉
```

然后重新加载：

```bash
launchctl unload ~/Library/LaunchAgents/com.redmountain.newhigh.fullcycle.plist
launchctl load ~/Library/LaunchAgents/com.redmountain.newhigh.fullcycle.plist
```

## 修改时间

编辑 `~/Library/LaunchAgents/com.redmountain.newhigh.fullcycle.plist` 中 `StartCalendarInterval` 的 `Hour` / `Minute` / `Weekday`（1=周一…7=周日），保存后：

```bash
launchctl unload ~/Library/LaunchAgents/com.redmountain.newhigh.fullcycle.plist
launchctl load ~/Library/LaunchAgents/com.redmountain.newhigh.fullcycle.plist
```

## 卸载

```bash
bash scripts/schedule/uninstall_scheduled_run.sh
```

或手动：

```bash
launchctl unload ~/Library/LaunchAgents/com.redmountain.newhigh.fullcycle.plist
rm ~/Library/LaunchAgents/com.redmountain.newhigh.fullcycle.plist
```

## 说明

- **锁屏会跑**：LaunchAgent 属于当前登录用户，只要账户已登录（包括锁屏、息屏），到点就会执行。
- **休眠**：若机器进入休眠，可能错过当次触发；下次唤醒后不会补跑。需要休眠也跑的可考虑保持「防止休眠」或使用服务器/常开机器。
- **依赖**：需已存在 `.venv` 且安装好依赖；首次建议先手动跑通 `python scripts/run_full_cycle.py`。
