"""
智能重构建议

基于代码分析提供智能重构建议。
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class RefactoringType(Enum):
    """重构类型"""
    EXTRACT_FUNCTION = "extract_function"
    RENAME_VARIABLE = "rename_variable"
    MOVE_CLASS = "move_class"
    REMOVE_DUPLICATE = "remove_duplicate"
    SIMPLIFY_CONDITION = "simplify_condition"
    ADD_TYPE_HINT = "add_type_hint"


@dataclass
class RefactoringSuggestion:
    """重构建议"""
    id: str
    type: RefactoringType
    file: str
    line: int
    description: str
    benefit: str
    effort: str  # low/medium/high
    code_snippet: Optional[str] = None


class RefactoringSuggester:
    """重构建议生成器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
    
    def analyze_file(self, file_path: str) -> List[RefactoringSuggestion]:
        """
        分析文件并生成重构建议
        
        Args:
            file_path: 文件路径
        
        Returns:
            重构建议列表
        """
        suggestions = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source)
            
            # 分析并生成建议
            suggestions.extend(self._suggest_extract_function(tree, file_path, source))
            suggestions.extend(self._suggest_add_type_hints(tree, file_path))
            suggestions.extend(self._suggest_simplify_condition(tree, file_path, source))
            
        except Exception as e:
            pass
        
        return suggestions
    
    def _suggest_extract_function(
        self, tree: ast.AST, file_path: str, source: str
    ) -> List[RefactoringSuggestion]:
        """建议提取函数"""
        suggestions = []
        lines = source.split('\n')
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # 检查函数是否过长
                if hasattr(node, 'end_lineno') and node.end_lineno:
                    func_length = node.end_lineno - node.lineno
                    
                    if func_length > 30:
                        suggestions.append(RefactoringSuggestion(
                            id=f"EXT_{node.lineno}",
                            type=RefactoringType.EXTRACT_FUNCTION,
                            file=file_path,
                            line=node.lineno,
                            description=f"函数 '{node.name}' 过长 ({func_length} 行)，建议拆分",
                            benefit="提高代码可读性和可维护性",
                            effort="medium",
                            code_snippet='\n'.join(lines[node.lineno-1:node.lineno+5]),
                        ))
        
        return suggestions
    
    def _suggest_add_type_hints(
        self, tree: ast.AST, file_path: str
    ) -> List[RefactoringSuggestion]:
        """建议添加类型提示"""
        suggestions = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # 检查公共函数是否缺少类型提示
                if not node.name.startswith('_'):
                    # 检查返回值类型
                    if node.returns is None:
                        suggestions.append(RefactoringSuggestion(
                            id=f"TYPE_{node.lineno}",
                            type=RefactoringType.ADD_TYPE_HINT,
                            file=file_path,
                            line=node.lineno,
                            description=f"函数 '{node.name}' 缺少返回值类型提示",
                            benefit="提高代码可读性和 IDE 支持",
                            effort="low",
                        ))
                    
                    # 检查参数类型
                    for arg in node.args.args:
                        if arg.annotation is None and arg.arg != 'self':
                            suggestions.append(RefactoringSuggestion(
                                id=f"TYPE_{node.lineno}_{arg.arg}",
                                type=RefactoringType.ADD_TYPE_HINT,
                                file=file_path,
                                line=node.lineno,
                                description=f"参数 '{arg.arg}' 缺少类型提示",
                                benefit="提高代码可读性和 IDE 支持",
                                effort="low",
                            ))
        
        return suggestions
    
    def _suggest_simplify_condition(
        self, tree: ast.AST, file_path: str, source: str
    ) -> List[RefactoringSuggestion]:
        """建议简化条件"""
        suggestions = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # 检查嵌套 if 语句
                nested_count = self._count_nested_if(node)
                if nested_count > 3:
                    suggestions.append(RefactoringSuggestion(
                        id=f"COND_{node.lineno}",
                        type=RefactoringType.SIMPLIFY_CONDITION,
                        file=file_path,
                        line=node.lineno,
                        description=f"条件嵌套过深 ({nested_count} 层)",
                        benefit="降低代码复杂度，提高可读性",
                        effort="medium",
                    ))
        
        return suggestions
    
    def _count_nested_if(self, node: ast.AST, depth: int = 0) -> int:
        """计算嵌套 if 深度"""
        max_depth = depth
        
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.If):
                child_depth = self._count_nested_if(child, depth + 1)
                max_depth = max(max_depth, child_depth)
        
        return max_depth
    
    def suggest_project(self) -> Dict[str, Any]:
        """
        分析整个项目并生成重构建议
        
        Returns:
            建议汇总
        """
        directories = [
            self.project_root / "lib",
            self.project_root / "core" / "src" / "core",
            self.project_root / "data" / "src" / "data",
            self.project_root / "ai" / "src" / "ai",
            self.project_root / "scanner" / "src" / "market_scanner",
            self.project_root / "strategy" / "src" / "strategy_engine",
        ]
        
        all_suggestions = []
        for directory in directories:
            if directory.exists():
                for file_path in directory.rglob("*.py"):
                    if "__pycache__" not in str(file_path):
                        suggestions = self.analyze_file(str(file_path))
                        all_suggestions.extend(suggestions)
        
        # 按类型统计
        by_type = {}
        for suggestion in all_suggestions:
            type_name = suggestion.type.value
            if type_name not in by_type:
                by_type[type_name] = []
            by_type[type_name].append(suggestion)
        
        # 按工作量统计
        by_effort = {"low": 0, "medium": 0, "high": 0}
        for suggestion in all_suggestions:
            by_effort[suggestion.effort] += 1
        
        return {
            "total_suggestions": len(all_suggestions),
            "by_type": {k: len(v) for k, v in by_type.items()},
            "by_effort": by_effort,
            "suggestions": all_suggestions,
        }
    
    def generate_report(self, suggestions: List[RefactoringSuggestion]) -> str:
        """
        生成重构建议报告
        
        Args:
            suggestions: 建议列表
        
        Returns:
            报告文本
        """
        report = []
        report.append("=" * 60)
        report.append("重构建议报告")
        report.append("=" * 60)
        
        report.append(f"\n总建议数：{len(suggestions)}")
        
        # 按工作量分组
        low_effort = [s for s in suggestions if s.effort == "low"]
        medium_effort = [s for s in suggestions if s.effort == "medium"]
        high_effort = [s for s in suggestions if s.effort == "high"]
        
        report.append(f"\n快速改进 (low): {len(low_effort)}")
        report.append(f"中等改进 (medium): {len(medium_effort)}")
        report.append(f"重大改进 (high): {len(high_effort)}")
        
        # 详细建议
        report.append("\n详细建议:")
        for i, suggestion in enumerate(suggestions[:20], 1):  # 只显示前 20 个
            report.append(f"\n{i}. [{suggestion.type.value}] {suggestion.file}")
            report.append(f"   L{suggestion.line}: {suggestion.description}")
            report.append(f"   收益：{suggestion.benefit}")
            report.append(f"   工作量：{suggestion.effort}")
        
        if len(suggestions) > 20:
            report.append(f"\n... 还有 {len(suggestions) - 20} 个建议")
        
        return '\n'.join(report)


# 全局实例
refactoring_suggester = RefactoringSuggester()


def suggest_refactoring(file_path: str) -> List[RefactoringSuggestion]:
    """生成重构建议"""
    return refactoring_suggester.analyze_file(file_path)


def suggest_project() -> Dict[str, Any]:
    """生成项目重构建议"""
    return refactoring_suggester.suggest_project()
