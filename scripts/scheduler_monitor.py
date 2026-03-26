#!/usr/bin/env python3
"""
调度系统监控脚本
实时监控调度系统状态，提供告警和管理功能

功能：
1. 监控调度系统运行状态
2. 监控任务执行情况
3. 监控系统资源使用
4. 提供告警通知
5. 生成监控报告
"""

import os
import sys
import time
import json
import logging
import subprocess
import psutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scheduler_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SchedulerMonitor:
    """调度系统监控器"""

    def __init__(self, config_path: Optional[str] = None):
        self.config = self.load_config(config_path)
        self.alert_thresholds = {
            'cpu_percent': 80.0,      # CPU使用率阈值
            'memory_percent': 80.0,   # 内存使用率阈值
            'disk_percent': 90.0,     # 磁盘使用率阈值
            'process_count': 50,      # 进程数阈值
            'response_time': 5.0,     # 响应时间阈值（秒）
            'error_count': 10,        # 错误计数阈值
            'queue_size': 100,        # 队列大小阈值
        }
        self.alerts = []
        self.metrics_history = []
        self.max_history_size = 1000

    def load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """加载配置"""
        default_config = {
            'monitor_interval': 60,           # 监控间隔（秒）
            'alert_check_interval': 300,      # 告警检查间隔（秒）
            'report_interval': 3600,          # 报告生成间隔（秒）
            'log_retention_days': 7,          # 日志保留天数
            'alert_channels': ['log', 'file'], # 告警通道
            'monitor_services': ['scheduler', 'database', 'api'],
            'metrics_to_collect': ['cpu', 'memory', 'disk', 'process', 'network'],
        }

        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
                logger.info(f"从 {config_path} 加载配置")
            except Exception as e:
                logger.error(f"加载配置失败: {e}")

        return default_config

    def check_scheduler_status(self) -> Dict[str, Any]:
        """检查调度系统状态"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'running': False,
            'processes': [],
            'health': {}
        }

        try:
            # 检查调度进程
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    if 'start_schedulers.py' in cmdline or 'scheduler' in proc.info['name'].lower():
                        status['processes'].append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cmdline': cmdline[:100]  # 截断长命令
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # 检查调度器是否运行
            status['running'] = len(status['processes']) > 0

            # 检查调度器健康状态
            if status['running']:
                try:
                    # 调用调度器状态检查
                    result = subprocess.run(
                        ['python', 'scripts/start_schedulers.py', 'status'],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )

                    if result.returncode == 0:
                        health_data = json.loads(result.stdout)
                        status['health'] = health_data
                    else:
                        status['health'] = {'error': result.stderr}

                except Exception as e:
                    status['health'] = {'error': str(e)}

            logger.info(f"调度系统状态: 运行={status['running']}, 进程数={len(status['processes'])}")

        except Exception as e:
            logger.error(f"检查调度状态失败: {e}")
            status['error'] = str(e)

        return status

    def check_system_metrics(self) -> Dict[str, Any]:
        """检查系统指标"""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'cpu': {},
            'memory': {},
            'disk': {},
            'process': {},
            'network': {}
        }

        try:
            # CPU指标
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_times = psutil.cpu_times_percent()

            metrics['cpu'] = {
                'percent': cpu_percent,
                'count': cpu_count,
                'user': cpu_times.user,
                'system': cpu_times.system,
                'idle': cpu_times.idle
            }

            # 内存指标
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()

            metrics['memory'] = {
                'total_gb': round(memory.total / (1024**3), 2),
                'available_gb': round(memory.available / (1024**3), 2),
                'used_percent': memory.percent,
                'swap_total_gb': round(swap.total / (1024**3), 2),
                'swap_used_percent': swap.percent
            }

            # 磁盘指标
            disk = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()

            metrics['disk'] = {
                'total_gb': round(disk.total / (1024**3), 2),
                'used_gb': round(disk.used / (1024**3), 2),
                'free_gb': round(disk.free / (1024**3), 2),
                'percent': disk.percent,
                'read_mb': round(disk_io.read_bytes / (1024**2), 2) if disk_io else 0,
                'write_mb': round(disk_io.write_bytes / (1024**2), 2) if disk_io else 0
            }

            # 进程指标
            process_count = len(list(psutil.process_iter()))

            metrics['process'] = {
                'count': process_count,
                'python_count': len([p for p in psutil.process_iter()
                                   if p.name() and 'python' in p.name().lower()])
            }

            # 网络指标
            net_io = psutil.net_io_counters()

            metrics['network'] = {
                'bytes_sent_mb': round(net_io.bytes_sent / (1024**2), 2),
                'bytes_recv_mb': round(net_io.bytes_recv / (1024**2), 2),
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv
            }

            logger.debug(f"系统指标收集完成: CPU={cpu_percent}%, 内存={memory.percent}%")

        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")
            metrics['error'] = str(e)

        return metrics

    def check_database_health(self) -> Dict[str, Any]:
        """检查数据库健康状态"""
        health = {
            'timestamp': datetime.now().isoformat(),
            'status': 'unknown',
            'tables': 0,
            'size_mb': 0,
            'connection': False
        }

        try:
            import duckdb

            db_path = 'data/quant_system.duckdb'
            if os.path.exists(db_path):
                # 检查数据库连接
                conn = duckdb.connect(db_path)

                # 获取表数量
                tables_result = conn.execute('SHOW TABLES').fetchall()
                table_count = len(tables_result)

                # 获取数据库大小
                db_size = os.path.getsize(db_path) / (1024 * 1024)  # MB

                # 检查关键表
                critical_tables = ['daily_bars', 'stocks', 'news_items', 'features_daily']
                missing_tables = []

                for table in critical_tables:
                    try:
                        conn.execute(f'SELECT 1 FROM {table} LIMIT 1')
                    except:
                        missing_tables.append(table)

                conn.close()

                health.update({
                    'status': 'healthy' if len(missing_tables) == 0 else 'degraded',
                    'tables': table_count,
                    'size_mb': round(db_size, 2),
                    'missing_tables': missing_tables,
                    'connection': True
                })

                logger.info(f"数据库健康: 状态={health['status']}, 表数={table_count}, 大小={db_size:.2f}MB")
            else:
                health['status'] = 'error'
                health['error'] = '数据库文件不存在'
                logger.error("数据库文件不存在")

        except ImportError:
            health['status'] = 'error'
            health['error'] = 'duckdb模块未安装'
            logger.error("duckdb模块未安装")
        except Exception as e:
            health['status'] = 'error'
            health['error'] = str(e)
            logger.error(f"检查数据库健康失败: {e}")

        return health

    def check_alerts(self, scheduler_status: Dict, system_metrics: Dict, db_health: Dict) -> List[Dict[str, Any]]:
        """检查告警条件"""
        alerts = []

        # 检查调度系统状态
        if not scheduler_status.get('running', False):
            alerts.append({
                'level': 'critical',
                'type': 'scheduler_down',
                'message': '调度系统未运行',
                'timestamp': datetime.now().isoformat(),
                'details': scheduler_status
            })

        # 检查CPU使用率
        cpu_percent = system_metrics.get('cpu', {}).get('percent', 0)
        if cpu_percent > self.alert_thresholds['cpu_percent']:
            alerts.append({
                'level': 'warning',
                'type': 'high_cpu',
                'message': f'CPU使用率过高: {cpu_percent}%',
                'timestamp': datetime.now().isoformat(),
                'details': system_metrics['cpu']
            })

        # 检查内存使用率
        memory_percent = system_metrics.get('memory', {}).get('used_percent', 0)
        if memory_percent > self.alert_thresholds['memory_percent']:
            alerts.append({
                'level': 'warning',
                'type': 'high_memory',
                'message': f'内存使用率过高: {memory_percent}%',
                'timestamp': datetime.now().isoformat(),
                'details': system_metrics['memory']
            })

        # 检查数据库健康
        db_status = db_health.get('status', 'unknown')
        if db_status == 'error':
            alerts.append({
                'level': 'critical',
                'type': 'database_error',
                'message': '数据库错误',
                'timestamp': datetime.now().isoformat(),
                'details': db_health
            })
        elif db_status == 'degraded':
            missing_tables = db_health.get('missing_tables', [])
            if missing_tables:
                alerts.append({
                    'level': 'warning',
                    'type': 'database_degraded',
                    'message': f'数据库表缺失: {missing_tables}',
                    'timestamp': datetime.now().isoformat(),
                    'details': db_health
                })

        return alerts

    def send_alerts(self, alerts: List[Dict[str, Any]]):
        """发送告警"""
        for alert in alerts:
            # 记录到日志
            logger.warning(f"告警 [{alert['level']}]: {alert['type']} - {alert['message']}")

            # 保存到文件
            alert_file = f"logs/alerts_{datetime.now().strftime('%Y%m%d')}.json"
            try:
                existing_alerts = []
                if os.path.exists(alert_file):
                    with open(alert_file, 'r') as f:
                        existing_alerts = json.load(f)

                existing_alerts.append(alert)

                with open(alert_file, 'w') as f:
                    json.dump(existing_alerts, f, indent=2, ensure_ascii=False)

            except Exception as e:
                logger.error(f"保存告警到文件失败: {e}")

            # 这里可以添加其他告警通道，如邮件、Slack、微信等
            # if 'email' in self.config['alert_channels']:
            #     self.send_email_alert(alert)
            # if 'slack' in self.config['alert_channels']:
            #     self.send_slack_alert(alert)

    def generate_report(self) -> Dict[str, Any]:
        """生成监控报告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'period': 'hourly',
            'summary': {},
            'metrics': {},
            'alerts': self.alerts[-24:] if self.alerts else [],  # 最近24条告警
            'recommendations': []
        }

        if self.metrics_history:
            # 计算指标统计
            recent_metrics = self.metrics_history[-60:]  # 最近60个数据点

            cpu_values = [m.get('cpu', {}).get('percent', 0) for m in recent_metrics]
            memory_values = [m.get('memory', {}).get('used_percent', 0) for m in recent_metrics]

            report['metrics'] = {
                'cpu': {
                    'avg': round(sum(cpu_values) / len(cpu_values), 2) if cpu_values else 0,
                    'max': max(cpu_values) if cpu_values else 0,
                    'min': min(cpu_values) if cpu_values else 0
                },
                'memory': {
                    'avg': round(sum(memory_values) / len(memory_values), 2) if memory_values else 0,
                    'max': max(memory_values) if memory_values else 0,
                    'min': min(memory_values) if memory_values else 0
                }
            }

            # 生成建议
            if report['metrics']['cpu']['avg'] > 70:
                report['recommendations'].append('CPU使用率偏高，建议优化代码或增加资源')

            if report['metrics']['memory']['avg'] > 75:
                report['recommendations'].append('内存使用率偏高，建议检查内存泄漏或增加内存')

        # 保存报告
        report_file = f"logs/report_{datetime.now().strftime('%Y%m%d_%H')}.json"
        try:
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            logger.info(f"监控报告已保存: {report_file}")
        except Exception as e:
            logger.error(f"保存监控报告失败: {e}")

        return report

    def run_monitoring_cycle(self):
        """运行监控周期"""
        logger.info("开始监控周期")

        try:
            # 收集监控数据
            scheduler_status = self.check_scheduler_status()
            system_metrics = self.check_system_metrics()
            db_health = self.check_database_health()

            # 保存指标历史
            combined_metrics = {
                'timestamp': datetime.now().isoformat(),
                'scheduler': scheduler_status,
                'system': system_metrics,
                'database': db_health
            }

            self.metrics_history.append(combined_metrics)
            if len(self.metrics_history) > self.max_history_size:
                self.metrics_history = self.metrics_history[-self.max_history_size:]

            # 检查告警
            new_alerts = self.check_alerts(scheduler_status, system_metrics, db_health)
            if new_alerts:
                self.alerts.extend(new_alerts)
                self.send_alerts(new_alerts)

            # 生成摘要日志
            logger.info(f"监控摘要: 调度器={scheduler_status['running']}, "
                       f"CPU={system_metrics.get('cpu', {}).get('percent', 0)}%, "
                       f"内存={system_metrics.get('memory', {}).get('used_percent', 0)}%, "
                       f"数据库={db_health.get('status', 'unknown')}")

        except Exception as e:
            logger.error(f"监控周期执行失败: {e}")

    def start_monitoring(self):
        """启动监控"""
        logger.info("启动调度系统监控")
        logger.info(f"监控配置: 间隔={self.config['monitor_interval']}秒")

        last_alert_check = time.time()
        last_report_time = time.time()

        try:
            while True:
                start_time = time.time()

                # 运行监控周期
                self.run_monitoring_cycle()

                # 定期检查告警（频率较低）
                current_time = time.time()
                if current_time - last_alert_check >= self.config['alert_check_interval']:
                    # 这里可以添加更复杂的告警分析
                    last_alert_check = current_time

                # 定期生成报告
                if current_time - last_report_time >= self.config['report_interval']:
                    self.generate_report()
                    last_report_time = current_time

                # 计算睡眠时间，确保精确的监控间隔
                elapsed = time.time() - start_time
                sleep_time = max(1, self.config['monitor_interval'] - elapsed)

                logger.debug(f"监控周期完成，耗时{elapsed:.2f}秒，睡眠{sleep_time:.2f}秒")
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            logger.info("监控被用户中断")
        except Exception as e:
            logger.error(f"监控主循环失败: {e}")
            raise

    def stop_monitoring(self):
        """停止监控"""
        logger.info("停止调度系统监控")
        # 这里可以添加清理逻辑


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="调度系统监控工具")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--interval", type=int, default=60, help="监控间隔（秒）")
    parser.add_argument("--once", action="store_true", help="只运行一次监控")
    parser.add_argument("--report", action="store_true", help="生成报告并退出")

    args = parser.parse_args()

    # 创建监控器
    monitor = SchedulerMonitor(args.config)

    if args.config:
        monitor.config['monitor_interval'] = args.interval

    try:
        if args.report:
            # 生成报告
            report = monitor.generate_report()
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 0
        elif args.once:
            # 运行一次监控
            monitor.run_monitoring_cycle()
            return 0
        else:
            # 持续监控
            monitor.start_monitoring()
            return 0

    except KeyboardInterrupt:
        print("\n监控已停止")
        return 0
    except Exception as e:
        logger.error(f"监控执行失败: {e}")
        return 1


if __name__ == "__main__":
    exit(main())