"""
自动化代码审查

提供代码质量检查和审查功能。
"""

from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class IssueSeverity(Enum):
    """问题严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class CodeIssue:
    """代码问题"""
    file: str
    line: int
    column: int
    message: str
    severity: IssueSeverity
    rule: str


class CodeReviewer:
    """代码审查器"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.rules = self._load_rules()

    def _load_rules(self) -> List[Dict[str, Any]]:
        """加载审查规则"""
        return [
            {
                "id": "R001",
                "name": "函数过长",
                "description": "函数超过 50 行",
                "severity": IssueSeverity.WARNING,
            },
            {
                "id": "R002",
                "name": "缺少文档字符串",
                "description": "公共函数缺少 docstring",
                "severity": IssueSeverity.INFO,
            },
            {
                "id": "R003",
                "name": "复杂度过高",
                "description": "函数圈复杂度超过 10",
                "severity": IssueSeverity.WARNING,
            },
            {
                "id": "R004",
                "name": "重复代码",
                "description": "检测到重复代码块",
                "severity": IssueSeverity.ERROR,
            },
            {
                "id": "R005",
                "name": "未使用的导入",
                "description": "导入了未使用的模块",
                "severity": IssueSeverity.INFO,
            },
        ]

    def review_file(self, file_path: str) -> List[CodeIssue]:
        """
        审查单个文件

        Args:
            file_path: 文件路径

        Returns:
            问题列表
        """
        issues = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()

            tree = ast.parse(source)

            # 检查函数长度
            issues.extend(self._check_function_length(tree, file_path, source))

            # 检查文档字符串
            issues.extend(self._check_docstrings(tree, file_path))

            # 检查导入
            issues.extend(self._check_imports(tree, file_path, source))

        except Exception as e:
            issues.append(CodeIssue(
                file=file_path,
                line=0,
                column=0,
                message=f"审查失败：{e}",
                severity=IssueSeverity.ERROR,
                rule="PARSE_ERROR",
            ))

        return issues

    def review_directory(self, directory: str, pattern: str = "*.py") -> Dict[str, List[CodeIssue]]:
        """
        审查目录

        Args:
            directory: 目录路径
            pattern: 文件匹配模式

        Returns:
            文件 -> 问题列表 的字典
        """
        results = {}
        path = Path(directory)

        for file_path in path.rglob(pattern):
            if "__pycache__" in str(file_path):
                continue

            issues = self.review_file(str(file_path))
            if issues:
                results[str(file_path)] = issues

        return results

    def _check_function_length(self, tree: ast.AST, file_path: str, source: str) -> List[CodeIssue]:
        """检查函数长度"""
        issues = []
        lines = source.split('\n')

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # 计算函数行数
                start_line = node.lineno
                end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line
                func_length = end_line - start_line + 1

                if func_length > 50:
                    issues.append(CodeIssue(
                        file=file_path,
                        line=start_line,
                        column=node.col_offset,
                        message=f"函数 '{node.name}' 过长 ({func_length} 行)",
                        severity=IssueSeverity.WARNING,
                        rule="R001",
                    ))

        return issues

    def _check_docstrings(self, tree: ast.AST, file_path: str) -> List[CodeIssue]:
        """检查文档字符串"""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # 检查公共函数
                if not node.name.startswith('_'):
                    if not ast.get_docstring(node):
                        issues.append(CodeIssue(
                            file=file_path,
                            line=node.lineno,
                            column=node.col_offset,
                            message=f"公共函数 '{node.name}' 缺少文档字符串",
                            severity=IssueSeverity.INFO,
                            rule="R002",
                        ))

        return issues

    def _check_imports(self, tree: ast.AST, file_path: str, source: str) -> List[CodeIssue]:
        """检查导入"""
        issues = []

        # 简单检查：查找未使用的导入
        # (这里可以实现更复杂的逻辑)

        return issues

    def generate_report(self, results: Dict[str, List[CodeIssue]]) -> str:
        """
        生成审查报告

        Args:
            results: 审查结果

        Returns:
            报告文本
        """
        report = []
        report.append("=" * 60)
        report.append("代码审查报告")
        report.append("=" * 60)

        total_issues = sum(len(issues) for issues in results.values())
        report.append(f"\n总问题数：{total_issues}")
        report.append(f"审查文件数：{len(results)}")

        # 按严重程度统计
        severity_count = {s.value: 0 for s in IssueSeverity}
        for issues in results.values():
            for issue in issues:
                severity_count[issue.severity.value] += 1

        report.append("\n问题分布:")
        for severity, count in severity_count.items():
            if count > 0:
                report.append(f"  {severity.upper()}: {count}")

        # 详细问题列表
        report.append("\n详细问题:")
        for file_path, issues in results.items():
            report.append(f"\n{file_path}:")
            for issue in issues:
                report.append(
                    f"  L{issue.line}:{issue.column} [{issue.severity.value.upper()}] "
                    f"{issue.message} ({issue.rule})"
                )

        return '\n'.join(report)

    def review_project(self) -> Dict[str, Any]:
        """
        审查整个项目

        Returns:
            审查结果
        """
        directories = [
            self.project_root / "lib",
            self.project_root / "core" / "src" / "core",
            self.project_root / "data" / "src" / "data",
            self.project_root / "ai" / "src" / "ai",
            self.project_root / "scanner" / "src" / "market_scanner",
            self.project_root / "strategy" / "src" / "strategy_engine",
        ]

        all_results = {}
        for directory in directories:
            if directory.exists():
                results = self.review_directory(str(directory))
                all_results.update(results)

        return {
            "total_files": len(all_results),
            "total_issues": sum(len(issues) for issues in all_results.values()),
            "issues_by_file": all_results,
            "report": self.generate_report(all_results),
        }


# 全局实例
code_reviewer = CodeReviewer()


def review_code(file_path: str) -> List[CodeIssue]:
    """审查代码文件"""
    return code_reviewer.review_file(file_path)


def review_project() -> Dict[str, Any]:
    """审查整个项目"""
    return code_reviewer.review_project()
