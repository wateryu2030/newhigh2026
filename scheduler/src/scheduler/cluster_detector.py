"""
OpenClaw 集群检测器 - 可选的集群资源调度

设计原则：
1. 默认单机运行，不依赖任何集群配置
2. 仅在 ~/.openclaw/cluster/nodes.yaml 存在且 enabled: true 时启用集群
3. 节点可随时加入/退出，不影响 newhigh 核心功能
4. 移动设备（如 newhigh 本机）可随时拆解，不影响集群

用法：
    from scheduler.cluster_detector import ClusterDetector

    detector = ClusterDetector()
    if detector.is_cluster_enabled():
        # 使用集群资源
        nodes = detector.get_active_nodes()
        task = detector.schedule_task("backtest", priority="normal")
    else:
        # 本地执行
        run_locally()
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 集群配置路径（与 newhigh 分离）
CLUSTER_DIR = Path.home() / ".openclaw" / "cluster"
CONFIG_FILE = CLUSTER_DIR / "nodes.yaml"
SSH_KEY_PATH = CLUSTER_DIR / "ssh" / "openclaw_cluster_key"


@dataclass
class NodeInfo:
    """节点信息"""
    name: str
    host: str
    user: str
    role: str = "worker"
    cpu_cores: int = 4
    gpu_count: int = 0
    memory_gb: int = 8
    storage_gb: int = 512
    status: str = "unknown"
    ssh_key: Optional[str] = None


@dataclass
class ClusterConfig:
    """集群配置"""
    enabled: bool = False
    name: str = "openclaw-cluster"
    master_node: str = "studio"
    nodes: List[NodeInfo] = field(default_factory=list)
    shared_storage_path: Optional[str] = None


class ClusterDetector:
    """集群检测器 - 检测并管理集群资源"""

    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or CONFIG_FILE
        self._config: Optional[ClusterConfig] = None

    def is_cluster_enabled(self) -> bool:
        """
        检查集群模式是否启用

        返回 False 的情况：
        - 配置文件不存在
        - enabled: false
        - 配置文件解析失败

        这确保 newhigh 默认以单机模式运行
        """
        if not self.config_file.exists():
            logger.debug(f"集群配置文件不存在：{self.config_file}，使用单机模式")
            return False

        try:
            config = self._load_config()
            return config.enabled
        except Exception as e:
            logger.warning(f"加载集群配置失败：{e}，使用单机模式")
            return False

    def _load_config(self) -> ClusterConfig:
        """加载集群配置（懒加载）"""
        if self._config is not None:
            return self._config

        # 尝试使用 pyyaml，如果可用
        try:
            import yaml
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            config = ClusterConfig(
                enabled=data.get('cluster', {}).get('enabled', False),
                name=data.get('cluster', {}).get('name', 'openclaw-cluster'),
                master_node=data.get('cluster', {}).get('master_node', 'studio'),
            )

            # 解析节点
            for node_data in data.get('nodes', []):
                if isinstance(node_data, dict):
                    config.nodes.append(self._parse_node(node_data))

            self._config = config
            return config
        except ImportError:
            logger.debug("pyyaml 未安装，使用简化解析")
        except Exception as e:
            logger.warning(f"yaml 解析失败：{e}，使用简化解析")

        # 简化 YAML 解析（不依赖 pyyaml）
        config = ClusterConfig()
        nodes = []
        current_node: Dict[str, Any] = {}
        in_nodes_section = False
        in_resources = False

        with open(self.config_file, 'r', encoding='utf-8') as f:
            for line in f:
                line_stripped = line.rstrip()
                indent = len(line) - len(line.lstrip())

                # 检查 enabled 状态
                if 'enabled:' in line_stripped and indent == 2:
                    value = line_stripped.split(':')[1].strip()
                    config.enabled = value.lower() == 'true'

                # 检查共享存储路径
                if 'data_path:' in line_stripped:
                    value = line_stripped.split(':')[1].strip().strip('"\'')
                    # 后续可使用

                # 检查节点部分
                if line_stripped.strip() == 'nodes:':
                    in_nodes_section = True
                    continue

                if in_nodes_section:
                    # 新节点开始（顶级列表项）
                    if line_stripped.strip().startswith('- name:'):
                        if current_node:
                            nodes.append(self._parse_node(current_node))
                        current_node = {}
                        in_resources = False
                        value = line_stripped.split(':', 1)[1].strip().strip('"\'')
                        current_node['name'] = value
                        continue

                    # 解析节点属性
                    if ':' in line_stripped and not line_stripped.strip().startswith('#'):
                        key_part = line_stripped.split(':')[0].strip().strip('- ')
                        value_part = line_stripped.split(':', 1)[1].strip() if ':' in line_stripped else ''

                        if key_part == 'resources':
                            in_resources = True
                            continue
                        elif key_part == 'storage':
                            in_resources = False
                            continue

                        if in_resources:
                            current_node.setdefault('resources', {})[key_part] = value_part.strip('"\'')
                        else:
                            current_node[key_part] = value_part.strip('"\'')

        # 添加最后一个节点
        if current_node and 'name' in current_node:
            nodes.append(self._parse_node(current_node))

        config.nodes = nodes
        self._config = config
        return config

    def _parse_node(self, data: Dict[str, Any]) -> NodeInfo:
        """解析节点数据"""
        resources = data.get('resources', {})
        return NodeInfo(
            name=data.get('name', 'unknown'),
            host=data.get('host', 'localhost'),
            user=data.get('user', os.getenv('USER', 'user')),
            role=data.get('role', 'worker'),
            cpu_cores=int(resources.get('cpu_cores', 4)),
            gpu_count=int(resources.get('gpu_count', 0)),
            memory_gb=int(resources.get('memory_gb', 8)),
            storage_gb=int(resources.get('storage_gb', 512)),
            status=data.get('status', 'unknown'),
            ssh_key=data.get('ssh_key')
        )

    def get_active_nodes(self, role: Optional[str] = None) -> List[NodeInfo]:
        """
        获取活跃节点列表

        Args:
            role: 过滤节点角色（master | worker）

        Returns:
            活跃节点列表（status 为 online 或 unknown）
        """
        if not self.is_cluster_enabled():
            return []

        config = self._load_config()
        nodes = config.nodes

        if role:
            nodes = [n for n in nodes if n.role == role]

        # 只返回可能可用的节点（online 或 unknown）
        return [n for n in nodes if n.status in ('online', 'unknown')]

    def get_master_node(self) -> Optional[NodeInfo]:
        """获取主节点信息"""
        if not self.is_cluster_enabled():
            return None

        config = self._load_config()
        for node in config.nodes:
            if node.role == 'master':
                return node
        return None

    def get_shared_storage_path(self) -> Optional[str]:
        """获取共享存储路径"""
        if not self.is_cluster_enabled():
            return None

        # 简单解析 YAML 获取 shared_storage.data_path
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # 查找 data_path
                import re
                match = re.search(r'data_path:\s*["\']?([^"\'\n]+)', content)
                if match:
                    return match.group(1).strip()
        except Exception as e:
            logger.warning(f"读取共享存储配置失败：{e}")

        return None

    def test_node_connection(self, node: NodeInfo, timeout: int = 5) -> bool:
        """
        测试节点 SSH 连接

        Args:
            node: 节点信息
            timeout: 连接超时时间（秒）

        Returns:
            True 如果连接成功
        """
        ssh_key = node.ssh_key or str(SSH_KEY_PATH)

        if not Path(ssh_key).expanduser().exists():
            logger.warning(f"SSH 密钥不存在：{ssh_key}")
            return False

        try:
            cmd = [
                'ssh',
                '-o', 'ConnectTimeout={}'.format(timeout),
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'BatchMode=yes',
                '-i', str(Path(ssh_key).expanduser()),
                f"{node.user}@{node.host}",
                "echo 'OK'"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 2)
            return result.returncode == 0 and 'OK' in result.stdout
        except subprocess.TimeoutExpired:
            logger.warning(f"节点 {node.host} 连接超时")
            return False
        except Exception as e:
            logger.warning(f"节点 {node.host} 连接失败：{e}")
            return False

    def check_all_nodes(self) -> Dict[str, bool]:
        """
        检查所有节点连接状态

        Returns:
            {节点名：是否可达}
        """
        if not self.is_cluster_enabled():
            return {}

        results = {}
        for node in self.get_active_nodes():
            results[node.name] = self.test_node_connection(node)
            logger.info(f"节点 {node.name} ({node.host}): {'✅' if results[node.name] else '❌'}")

        return results

    def schedule_task(
        self,
        task_type: str,
        priority: str = "normal",
        required_resources: Optional[Dict[str, Any]] = None
    ) -> Optional[NodeInfo]:
        """
        根据任务类型和资源需求调度节点

        Args:
            task_type: 任务类型（backtest | training | data_processing）
            priority: 优先级（critical | high | normal | low）
            required_resources: 所需资源（如 {'gpu_count': 1, 'memory_gb': 16}）

        Returns:
            选中的节点，如果没有可用节点则返回 None
        """
        if not self.is_cluster_enabled():
            return None

        nodes = self.get_active_nodes()
        if not nodes:
            logger.warning("没有可用的集群节点")
            return None

        # 简单调度策略：选择资源最匹配的节点
        # TODO: 实现更复杂的调度算法

        for node in nodes:
            if self._meets_requirements(node, required_resources):
                logger.info(f"任务 {task_type} 调度到节点 {node.name}")
                return node

        # 如果没有匹配的节点，返回第一个可用节点
        logger.warning(f"没有完全匹配资源的节点，使用默认节点 {nodes[0].name}")
        return nodes[0]

    def _meets_requirements(
        self,
        node: NodeInfo,
        requirements: Optional[Dict[str, Any]]
    ) -> bool:
        """检查节点是否满足资源需求"""
        if not requirements:
            return True

        if requirements.get('gpu_count', 0) > node.gpu_count:
            return False
        if requirements.get('memory_gb', 0) > node.memory_gb:
            return False
        if requirements.get('cpu_cores', 0) > node.cpu_cores:
            return False

        return True

    def run_on_node(
        self,
        node: NodeInfo,
        command: str,
        timeout: int = 300
    ) -> subprocess.CompletedProcess:
        """
        在远程节点执行命令

        Args:
            node: 目标节点
            command: 要执行的命令
            timeout: 超时时间（秒）

        Returns:
            subprocess.CompletedProcess 结果
        """
        ssh_key = node.ssh_key or str(SSH_KEY_PATH)

        cmd = [
            'ssh',
            '-o', 'ConnectTimeout=10',
            '-o', 'StrictHostKeyChecking=no',
            '-i', str(Path(ssh_key).expanduser()),
            f"{node.user}@{node.host}",
            command
        ]

        logger.info(f"在节点 {node.name} 执行：{command}")
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


# 便捷函数
def get_cluster_detector() -> ClusterDetector:
    """获取集群检测器实例"""
    return ClusterDetector()


def is_cluster_available() -> bool:
    """快速检查集群是否可用"""
    detector = get_cluster_detector()
    return detector.is_cluster_enabled()
