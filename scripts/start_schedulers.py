#!/usr/bin/env python3
"""
调度系统启动脚本 - 启动每日调度和实时调度，并提供监控和管理功能

功能：
1. 启动每日调度器（18:00执行）
2. 启动实时调度器（每30秒执行）
3. 提供进程管理和监控
4. 添加错误恢复和自动重启
5. 提供健康检查接口

使用方法：
python start_schedulers.py start     # 启动调度系统
python start_schedulers.py stop      # 停止调度系统
python start_schedulers.py status    # 查看调度系统状态
python start_schedulers.py restart   # 重启调度系统
python start_schedulers.py monitor   # 监控模式（前台运行）
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

# 添加项目路径
project_root = Path("/Users/apple/Ahope/newhigh")
sys.path.insert(0, str(project_root))

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
        self.realtime_interval = 30  # 实时调度间隔（秒）
        
        # 状态文件
        self.status_file = log_dir / "scheduler_status.json"
        
    def start_daily_scheduler(self):
        """启动每日调度器"""
        logger.info("启动每日调度器线程")
        
        def daily_scheduler_loop():
            while self.running:
                try:
                    now = datetime.now().time()
                    
                    # 检查是否到达调度时间
                    if now.hour == self.daily_schedule_time.hour and now.minute == self.daily_schedule_time.minute:
                        logger.info("执行每日调度任务")
                        self.run_daily_tasks()
                        
                        # 等待1分钟避免重复执行
                        time.sleep(60)
                    
                    # 每分钟检查一次
                    time.sleep(60)
                    
                except Exception as e:
                    logger.error(f"每日调度器错误: {e}")
                    time.sleep(60)  # 错误后等待1分钟重试
        
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
    
    def run_daily_tasks(self):
        """执行每日任务"""
        try:
            logger.info("开始执行每日任务")
            
            # 导入每日调度器
            sys.path.insert(0, str(project_root / "data-pipeline" / "src"))
            from data_pipeline.scheduler.daily_scheduler import run_daily
            
            # 执行每日调度
            run_daily(
                update_all_kline=True,
                kline_codes_limit=100,  # 限制更新100只股票
                collect_news=True,
                use_tushare=True,
                tushare_days_back=30
            )
            
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
            key_tables = ["a_stock_basic", "a_stock_daily", "news_items"]
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
    parser.add_argument("action", choices=["start", "stop", "restart", "status", "monitor"], 
                       help="执行的操作")
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