#!/usr/bin/env python3
"""
调度系统启动脚本 - 启动每日调度和实时调度，并提供监控和管理功能

功能：
1. 启动每日调度器（18:00 执行）
2. 日内数据刷新（默认 08:30、12:00、22:00）：优先活跃标的东财新闻 + 日 K + 可选 Tushare 增量；见 INTRADAY_* 环境变量
3. 十大股东采集（02:00 执行，多期历史）
4. 晚间 22:15 股东覆盖巡检（JSON + reports/missing_stocks.txt，可选补采见 NIGHTLY_SHAREHOLDER_BACKFILL）
5. 启动实时调度器（每30秒执行）
5. 提供进程管理和监控
6. 添加错误恢复和自动重启
7. 提供健康检查接口
8. 每日任务结束后可选执行 `push_shareholder_chip_signals.py`（写入 trade_signals / shareholder_chip）

使用方法：
python start_schedulers.py start     # 启动调度系统
python start_schedulers.py stop      # 停止调度系统
python start_schedulers.py status    # 查看调度系统状态
python start_schedulers.py restart   # 重启调度系统
python start_schedulers.py monitor   # 监控模式（前台运行）
python start_schedulers.py backfill-shareholder  # 十大股东全量回补（一次性）
python start_schedulers.py intraday-now  # 立即跑一轮日内刷新（调试用）
"""

import os
import sys
import time
import signal
import logging
import threading
import subprocess
import argparse
from datetime import datetime, time as dt_time
from pathlib import Path

# 添加项目路径（勿写死本机绝对路径）
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "lib"))
try:
    from newhigh_env import hydrate_tushare_token_from_dotenv, load_dotenv_if_present

    load_dotenv_if_present(project_root)
    hydrate_tushare_token_from_dotenv(project_root)
except ImportError:
    pass

# 配置日志
log_dir = project_root / "logs" / "scheduler"
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "scheduler_system.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class SchedulerManager:
    """调度系统管理器"""

    def __init__(self):
        self.daily_scheduler_thread = None
        self.realtime_scheduler_thread = None
        self.monitor_thread = None
        self.running = False
        self.processes = {}

        # 调度配置
        self.daily_schedule_time = dt_time(18, 0)  # 每日18:00
        self.shareholder_schedule_time = (2, 0)  # 每日02:00 十大股东采集
        self.data_quality_schedule_time = (2, 5)  # 每日02:05 数据质量巡检（错开股东任务）
        # 每日 22:15：十大股东覆盖巡检（晚间 10 点之后）
        self.shareholder_nightly_coverage_time = (22, 15)
        self.realtime_interval = 30  # 实时调度间隔（秒）
        self._last_shareholder_run = None  # 避免重复执行
        self._last_data_quality_run = None
        self._last_shareholder_nightly_run = None
        self._last_intraday_fire = {}  # (hour, minute) -> date 已触发日内刷新

        # 日内刷新时刻：默认 8:30、12:00、22:00；可用 SCHEDULER_INTRADAY_TIMES=08:30,12:00,22:00 覆盖
        self.intraday_times = self._parse_intraday_times()

        # 状态文件
        self.status_file = log_dir / "scheduler_status.json"

    @staticmethod
    def _parse_intraday_times():
        raw = (os.environ.get("SCHEDULER_INTRADAY_TIMES") or "08:30,12:00,22:00").strip()
        out = []
        for part in raw.split(","):
            part = part.strip()
            if not part or ":" not in part:
                continue
            try:
                a, b = part.split(":", 1)
                out.append((int(a), int(b)))
            except ValueError:
                continue
        return out if out else [(8, 30), (12, 0), (22, 0)]

    def start_daily_scheduler(self):
        """启动每日调度器"""
        logger.info("启动每日调度器线程")

        def daily_scheduler_loop():
            while self.running:
                try:
                    now = datetime.now()
                    now_time = now.time()
                    today = now.date()

                    # 每日 18:00：K线、新闻等
                    if now_time.hour == self.daily_schedule_time.hour and now_time.minute == self.daily_schedule_time.minute:
                        logger.info("执行每日调度任务")
                        self.run_daily_tasks()
                        time.sleep(60)

                    # 每日 02:00：十大股东多期采集
                    sh_hour, sh_minute = self.shareholder_schedule_time
                    if now_time.hour == sh_hour and now_time.minute == sh_minute:
                        if getattr(self, "_last_shareholder_run", None) != today:
                            logger.info("执行十大股东每日采集")
                            self.run_shareholder_collect()
                            self._last_shareholder_run = today
                        time.sleep(60)

                    dq_h, dq_m = self.data_quality_schedule_time
                    if now_time.hour == dq_h and now_time.minute == dq_m:
                        if getattr(self, "_last_data_quality_run", None) != today:
                            logger.info("执行数据质量巡检 run_data_quality_checks")
                            self.run_data_quality_checks()
                            self._last_data_quality_run = today
                        time.sleep(60)

                    n_h, n_m = self.shareholder_nightly_coverage_time
                    if now_time.hour == n_h and now_time.minute == n_m:
                        if getattr(self, "_last_shareholder_nightly_run", None) != today:
                            logger.info("执行晚间股东覆盖巡检 run_nightly_shareholder_coverage")
                            self.run_nightly_shareholder_coverage()
                            self._last_shareholder_nightly_run = today
                        time.sleep(60)

                    # 日内 8:30 / 12:00 / 22:00：新闻 + 优先标的日 K（减轻 Alpha 工坊穿透无 K 线/无新闻）
                    intraday_on = (os.environ.get("INTRADAY_REFRESH_ENABLE", "1") or "1").strip().lower() not in (
                        "0",
                        "false",
                        "no",
                    )
                    if intraday_on:
                        for ih, im in self.intraday_times:
                            if now_time.hour == ih and now_time.minute == im:
                                key = (ih, im)
                                if self._last_intraday_fire.get(key) != today:
                                    logger.info(
                                        "触发日内数据刷新 %02d:%02d（K 线/东财新闻/Tushare 可选）",
                                        ih,
                                        im,
                                    )
                                    self.run_intraday_refresh_task(slot=f"{ih:02d}{im:02d}")
                                    self._last_intraday_fire[key] = today
                                time.sleep(60)
                                break

                    time.sleep(60)

                except Exception as e:
                    logger.error(f"每日调度器错误: {e}")
                    time.sleep(60)

        self.daily_scheduler_thread = threading.Thread(target=daily_scheduler_loop, daemon=True)
        self.daily_scheduler_thread.start()
        logger.info("每日调度器已启动")

    def start_realtime_scheduler(self):
        """启动实时调度器"""
        logger.info("启动实时调度器线程")

        def realtime_scheduler_loop():
            while self.running:
                try:
                    logger.info("执行实时调度任务")
                    self.run_realtime_tasks()

                    # 等待指定间隔
                    time.sleep(self.realtime_interval)

                except Exception as e:
                    logger.error(f"实时调度器错误: {e}")
                    time.sleep(self.realtime_interval)  # 错误后等待间隔重试

        self.realtime_scheduler_thread = threading.Thread(target=realtime_scheduler_loop, daemon=True)
        self.realtime_scheduler_thread.start()
        logger.info("实时调度器已启动")

    def start_monitor(self):
        """启动监控线程"""
        logger.info("启动监控线程")

        def monitor_loop():
            while self.running:
                try:
                    self.check_system_health()
                    self.save_status()

                    # 每5分钟检查一次
                    time.sleep(300)

                except Exception as e:
                    logger.error(f"监控线程错误: {e}")
                    time.sleep(300)

        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("监控线程已启动")

    def _python_executable(self) -> str:
        venv_py = project_root / ".venv" / "bin" / "python"
        return str(venv_py) if venv_py.is_file() else sys.executable

    def run_shareholder_collect(self):
        """执行十大股东多期采集（后台子进程，约 35 分钟）"""
        def _run():
            try:
                logger.info("开始十大股东采集")
                log_path = project_root / "logs" / "shareholder_collect.log"
                log_path.parent.mkdir(parents=True, exist_ok=True)
                with open(log_path, "a", encoding="utf-8") as f:
                    proc = subprocess.Popen(
                        [
                            self._python_executable(),
                            str(project_root / "scripts" / "run_shareholder_collect.py"),
                            "--shareholders-only",
                            "--delay", "0.6",
                        ],
                        cwd=str(project_root),
                        env={**os.environ, "PYTHONPATH": str(project_root)},
                        stdout=f,
                        stderr=subprocess.STDOUT,
                    )
                    proc.wait()
                logger.info(f"十大股东采集完成 code={proc.returncode}")
            except Exception as e:
                logger.error(f"十大股东采集失败: {e}")

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def run_data_quality_checks(self):
        """数据质量巡检：写入 data_quality_reports / reports/latest_quality.json"""
        def _run():
            try:
                log_path = project_root / "logs" / "data_quality_scheduler.log"
                log_path.parent.mkdir(parents=True, exist_ok=True)
                with open(log_path, "a", encoding="utf-8") as f:
                    proc = subprocess.Popen(
                        [
                            self._python_executable(),
                            str(project_root / "scripts" / "run_data_quality_checks.py"),
                        ],
                        cwd=str(project_root),
                        env={**os.environ, "PYTHONPATH": str(project_root)},
                        stdout=f,
                        stderr=subprocess.STDOUT,
                    )
                    proc.wait()
                logger.info("数据质量巡检完成 code=%s", proc.returncode)
            except Exception as e:
                logger.error("数据质量巡检失败: %s", e)

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def run_nightly_shareholder_coverage(self):
        """晚间 22:15 股东覆盖巡检（后台子进程）"""
        def _run():
            try:
                log_path = project_root / "logs" / "nightly_shareholder_coverage.log"
                log_path.parent.mkdir(parents=True, exist_ok=True)
                with open(log_path, "a", encoding="utf-8") as f:
                    proc = subprocess.Popen(
                        [
                            self._python_executable(),
                            str(project_root / "scripts" / "run_nightly_shareholder_coverage.py"),
                        ],
                        cwd=str(project_root),
                        env={**os.environ, "PYTHONPATH": str(project_root)},
                        stdout=f,
                        stderr=subprocess.STDOUT,
                    )
                    proc.wait()
                logger.info("晚间股东覆盖巡检完成 code=%s", proc.returncode)
            except Exception as e:
                logger.error("晚间股东覆盖巡检失败: %s", e)

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def run_intraday_refresh_task(self, slot: str = "manual"):
        """后台执行一轮日内刷新（不阻塞调度主循环）。"""
        def _run():
            try:
                log_path = project_root / "logs" / "intraday_refresh.log"
                log_path.parent.mkdir(parents=True, exist_ok=True)
                with open(log_path, "a", encoding="utf-8") as f:
                    proc = subprocess.Popen(
                        [
                            self._python_executable(),
                            "-c",
                            (
                                "from data_pipeline.scheduler.daily_scheduler import run_intraday_refresh;"
                                f"run_intraday_refresh({slot!r})"
                            ),
                        ],
                        cwd=str(project_root),
                        env={**os.environ, "PYTHONPATH": str(project_root / "data-pipeline" / "src")},
                        stdout=f,
                        stderr=subprocess.STDOUT,
                    )
                    proc.wait()
                logger.info("日内刷新完成 slot=%s code=%s", slot, proc.returncode)
            except Exception as e:
                logger.exception("日内刷新子进程失败: %s", e)

        threading.Thread(target=_run, daemon=True).start()

    def run_daily_tasks(self):
        """执行每日任务"""
        try:
            logger.info("开始执行每日任务")

            token = (os.environ.get("TUSHARE_TOKEN") or "").strip()
            use_tushare = bool(token)
            ts_days = int(os.environ.get("TUSHARE_DAILY_DAYS_BACK", "7"))
            # 有 Token 时默认不再跑 akshare 批量日 K（代理环境易卡死）；需要东财补边时设 DAILY_AKSHARE_KLINE_LIMIT>0
            default_ak = 0 if use_tushare else 100
            ak_limit = int(os.environ.get("DAILY_AKSHARE_KLINE_LIMIT", str(default_ak)))

            logger.info(
                "每日调度策略: tushare_incremental=%s (TUSHARE_DAILY_DAYS_BACK 仅兼容) akshare_kline_limit=%s",
                use_tushare,
                ak_limit,
            )
            if use_tushare and ts_days > 21:
                logger.warning(
                    "TUSHARE_DAILY_DAYS_BACK=%s 偏大；长历史/全市场缺口请按需跑 scripts/backfill_a_stock_daily.py，勿依赖每日大窗口",
                    ts_days,
                )

            # 导入每日调度器
            sys.path.insert(0, str(project_root / "data-pipeline" / "src"))
            from data_pipeline.scheduler.daily_scheduler import run_daily

            run_daily(
                update_all_kline=(ak_limit > 0),
                kline_codes_limit=max(0, ak_limit),
                collect_news=True,
                use_tushare=use_tushare,
                tushare_days_back=ts_days,
            )

            # 反量化筹码池 → trade_signals（仅 strategy_id=shareholder_chip，与 ai_fusion 并存）
            push_chip = (os.environ.get("NEWHIGH_PUSH_SHAREHOLDER_CHIP_SIGNALS", "1") or "1").strip().lower()
            if push_chip not in ("0", "false", "no"):
                try:
                    chip_script = project_root / "scripts" / "push_shareholder_chip_signals.py"
                    proc = subprocess.run(
                        [sys.executable, str(chip_script)],
                        cwd=str(project_root),
                        capture_output=True,
                        text=True,
                        timeout=900,
                    )
                    if proc.returncode != 0:
                        logger.warning(
                            "push_shareholder_chip_signals 退出=%s stderr=%s",
                            proc.returncode,
                            (proc.stderr or "")[-1500:],
                        )
                    else:
                        out = (proc.stdout or "").strip()
                        if out:
                            logger.info(out)
                except Exception as e:
                    logger.error("push_shareholder_chip_signals 失败: %s", e)
            else:
                logger.info("已跳过 shareholder_chip 信号（NEWHIGH_PUSH_SHAREHOLDER_CHIP_SIGNALS=0）")

            logger.info("每日任务执行完成")

        except Exception as e:
            logger.error(f"每日任务执行失败: {e}")
            raise

    def run_realtime_tasks(self):
        """执行实时任务"""
        try:
            logger.info("开始执行实时任务")

            # 导入实时调度器
            sys.path.insert(0, str(project_root / "data-pipeline" / "src"))
            from data_pipeline.scheduler.realtime_scheduler import run_realtime_loop

            # 执行一轮实时任务（不进入无限循环）
            # 注意：这里需要修改realtime_scheduler以支持单次执行
            # 暂时使用系统运行器替代

            # 使用系统运行器执行一轮
            sys.path.insert(0, str(project_root))
            from system_core.system_runner import run_once

            result = run_once(
                run_data=False,  # 实时任务不更新数据
                run_scan=True,
                run_ai=True,
                run_strategy=True,
                data_include_daily_kline=False
            )

            logger.info(f"实时任务执行完成: {result}")

        except Exception as e:
            logger.error(f"实时任务执行失败: {e}")
            raise

    def check_system_health(self):
        """检查系统健康状态"""
        try:
            health_status = {
                "timestamp": datetime.now().isoformat(),
                "daily_scheduler": self.daily_scheduler_thread.is_alive() if self.daily_scheduler_thread else False,
                "realtime_scheduler": self.realtime_scheduler_thread.is_alive() if self.realtime_scheduler_thread else False,
                "monitor": self.monitor_thread.is_alive() if self.monitor_thread else False,
                "running": self.running,
                "database_health": self.check_database_health(),
                "api_health": self.check_api_health()
            }

            logger.info(f"系统健康状态: {health_status}")
            return health_status

        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return {"error": str(e)}

    def check_database_health(self):
        """检查数据库健康状态"""
        try:
            import duckdb

            db_path = project_root / "data" / "quant_system.duckdb"
            if not db_path.exists():
                return {"status": "error", "message": "数据库文件不存在"}

            conn = duckdb.connect(str(db_path))

            # 检查表数量
            tables = conn.execute("SHOW TABLES").fetchall()
            table_count = len(tables)

            # 检查关键表
            key_tables = ["a_stock_basic", "a_stock_daily", "news_items", "top_10_shareholders"]
            missing_tables = []

            for table in key_tables:
                try:
                    conn.execute(f"SELECT 1 FROM {table} LIMIT 1")
                except:
                    missing_tables.append(table)

            conn.close()

            return {
                "status": "healthy" if len(missing_tables) == 0 else "warning",
                "table_count": table_count,
                "missing_tables": missing_tables,
                "db_size_mb": db_path.stat().st_size / (1024 * 1024)
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def check_api_health(self):
        """检查API健康状态"""
        try:
            import requests

            # 尝试连接本地API
            response = requests.get("http://localhost:8000/api/health", timeout=5)

            return {
                "status": "healthy" if response.status_code == 200 else "warning",
                "status_code": response.status_code,
                "response": response.text[:100] if response.text else ""
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def save_status(self):
        """保存状态到文件"""
        try:
            import json

            status = {
                "timestamp": datetime.now().isoformat(),
                "running": self.running,
                "daily_scheduler_alive": self.daily_scheduler_thread.is_alive() if self.daily_scheduler_thread else False,
                "realtime_scheduler_alive": self.realtime_scheduler_thread.is_alive() if self.realtime_scheduler_thread else False,
                "monitor_alive": self.monitor_thread.is_alive() if self.monitor_thread else False,
                "health": self.check_system_health()
            }

            with open(self.status_file, 'w') as f:
                json.dump(status, f, indent=2, default=str)

        except Exception as e:
            logger.error(f"保存状态失败: {e}")

    def start(self):
        """启动调度系统"""
        if self.running:
            logger.warning("调度系统已在运行中")
            return

        logger.info("启动调度系统")
        self.running = True

        # 启动各个组件
        self.start_daily_scheduler()
        self.start_realtime_scheduler()
        self.start_monitor()

        logger.info("调度系统启动完成")
        self.save_status()

    def stop(self):
        """停止调度系统"""
        if not self.running:
            logger.warning("调度系统未在运行")
            return

        logger.info("停止调度系统")
        self.running = False

        # 等待线程结束
        if self.daily_scheduler_thread:
            self.daily_scheduler_thread.join(timeout=5)
        if self.realtime_scheduler_thread:
            self.realtime_scheduler_thread.join(timeout=5)
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

        logger.info("调度系统已停止")
        self.save_status()

    def restart(self):
        """重启调度系统"""
        logger.info("重启调度系统")
        self.stop()
        time.sleep(2)
        self.start()

    def status(self):
        """查看调度系统状态"""
        status_info = {
            "running": self.running,
            "daily_scheduler": "运行中" if self.daily_scheduler_thread and self.daily_scheduler_thread.is_alive() else "停止",
            "realtime_scheduler": "运行中" if self.realtime_scheduler_thread and self.realtime_scheduler_thread.is_alive() else "停止",
            "monitor": "运行中" if self.monitor_thread and self.monitor_thread.is_alive() else "停止",
            "health": self.check_system_health()
        }

        return status_info

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="调度系统管理工具")
    parser.add_argument(
        "action",
        choices=[
            "start",
            "stop",
            "restart",
            "status",
            "monitor",
            "backfill-shareholder",
            "intraday-now",
        ],
        help="执行的操作",
    )
    parser.add_argument("--config", help="配置文件路径")

    args = parser.parse_args()

    manager = SchedulerManager()

    if args.action == "start":
        manager.start()
        print("调度系统已启动")

        # 如果是监控模式，保持运行
        if args.action == "monitor":
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n收到中断信号，停止调度系统...")
                manager.stop()

    elif args.action == "stop":
        manager.stop()
        print("调度系统已停止")

    elif args.action == "restart":
        manager.restart()
        print("调度系统已重启")

    elif args.action == "status":
        status = manager.status()
        import json
        print(json.dumps(status, indent=2, default=str))

    elif args.action == "intraday-now":
        sys.path.insert(0, str(project_root / "data-pipeline" / "src"))
        from data_pipeline.scheduler.daily_scheduler import run_intraday_refresh

        run_intraday_refresh(slot_label="manual")
        print("intraday-now 完成")
        return 0

    elif args.action == "backfill-shareholder":
        print("执行十大股东全量回补（约 35 分钟）...")
        proc = subprocess.run(
            [
                str(project_root / ".venv" / "bin" / "python"),
                str(project_root / "scripts" / "run_shareholder_collect.py"),
                "--shareholders-only",
                "--delay", "0.6",
            ],
            cwd=str(project_root),
            env={**os.environ, "PYTHONPATH": str(project_root)},
        )
        print(f"回补完成 exit_code={proc.returncode}")
        return proc.returncode

    elif args.action == "monitor":
        manager.start()
        print("调度系统已启动（监控模式）")
        print("按 Ctrl+C 停止")

        try:
            while True:
                # 每10秒显示一次状态
                status = manager.status()
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 调度系统状态:")
                print(f"  运行状态: {'运行中' if status['running'] else '停止'}")
                print(f"  每日调度: {status['daily_scheduler']}")
                print(f"  实时调度: {status['realtime_scheduler']}")
                print(f"  监控线程: {status['monitor']}")

                # 显示健康状态摘要
                health = status.get('health', {})
                if isinstance(health, dict):
                    db_health = health.get('database_health', {})
                    if isinstance(db_health, dict):
                        print(f"  数据库状态: {db_health.get('status', '未知')} ({db_health.get('table_count', 0)} 表)")

                time.sleep(10)

        except KeyboardInterrupt:
            print("\n收到中断信号，停止调度系统...")
            manager.stop()

if __name__ == "__main__":
    main()