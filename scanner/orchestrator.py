# -*- coding: utf-8 -*-
"""
多智能体流水线编排器 (Orchestrator)
负责按顺序调度各个 Skill，管理上下文 (SkillContext) 和数据流
"""
from __future__ import annotations
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from datetime import datetime

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)


@dataclass
class SkillContext:
    """技能上下文：在流水线中传递的数据容器"""
    # 输入数据
    news_raw: List[Dict[str, Any]] = field(default_factory=list)
    
    # 主题相关
    themes_raw: List[str] = field(default_factory=list)
    themes_canonical: List[str] = field(default_factory=list)
    themes_validated: List[Dict[str, Any]] = field(default_factory=list)
    themes_with_regime: List[Dict[str, Any]] = field(default_factory=list)
    
    # 主题-股票映射
    theme_stock_map: Dict[str, List[str]] = field(default_factory=dict)
    
    # 选股相关
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    strategy_plan: Dict[str, Any] = field(default_factory=dict)
    enriched_data: Dict[str, Any] = field(default_factory=dict)
    feedback_data: Dict[str, Any] = field(default_factory=dict)
    picks: List[Dict[str, Any]] = field(default_factory=list)
    risk_filtered_picks: List[Dict[str, Any]] = field(default_factory=list)
    
    # 输出
    report: str = ""
    outcome: Dict[str, Any] = field(default_factory=dict)
    
    # 元数据
    start_time: datetime = field(default_factory=datetime.now)
    execution_log: List[Dict[str, Any]] = field(default_factory=list)
    
    def log(self, step: str, status: str, message: str = ""):
        """记录执行日志"""
        self.execution_log.append({
            "step": step,
            "status": status,
            "message": message,
            "timestamp": datetime.now()
        })


class Orchestrator:
    """
    多智能体流水线编排器
    按顺序执行: News Fetch → Theme Heat → Canonicalize → Theme Validate → Theme Regime
    → Theme Stock Bridge → Strategy Select → Backfill Enriched → Feedback Curator
    → Stock Pick → Chief Risk → Report → Outcome Enrich
    """
    
    def __init__(
        self,
        llm_client: Optional[Any] = None,
        progress_callback: Optional[Callable[[str, int, int, str], None]] = None,
    ):
        self.llm_client = llm_client
        self.progress_callback = progress_callback
        self.skills = {}
        self._load_skills()
    
    def _load_skills(self):
        """加载所有技能模块"""
        try:
            from scanner.skills import (
                news_fetch, theme_heat, canonicalize, theme_validate,
                theme_regime, theme_stock_bridge, strategy_select,
                backfill_enriched, feedback_curator, stock_pick,
                chief_risk, report_generator, outcome_enrich
            )
            self.skills = {
                "news_fetch": news_fetch,
                "theme_heat": theme_heat,
                "canonicalize": canonicalize,
                "theme_validate": theme_validate,
                "theme_regime": theme_regime,
                "theme_stock_bridge": theme_stock_bridge,
                "strategy_select": strategy_select,
                "backfill_enriched": backfill_enriched,
                "feedback_curator": feedback_curator,
                "stock_pick": stock_pick,
                "chief_risk": chief_risk,
                "report_generator": report_generator,
                "outcome_enrich": outcome_enrich,
            }
        except ImportError as e:
            print(f"[Orchestrator] 技能模块加载失败: {e}")
    
    def _progress(self, phase: str, current: int, total: int, message: str = ""):
        """进度回调"""
        if self.progress_callback:
            self.progress_callback(phase, current, total, message)
    
    def run_pipeline(
        self,
        days_lookback: int = 3,
        top_n_themes: int = 10,
        top_n_stocks: int = 20,
        use_llm: bool = True,
        relaxed_filter: bool = False,
    ) -> SkillContext:
        """
        执行完整的多智能体流水线
        
        :param days_lookback: 新闻回溯天数
        :param top_n_themes: 提取的热门主题数量
        :param top_n_stocks: 最终选股数量
        :param use_llm: 是否使用LLM进行深度分析
        :return: SkillContext 包含所有中间结果和最终输出
        """
        ctx = SkillContext()
        total_steps = 13
        
        try:
            # Step 1: News Fetch
            self._progress("news_fetch", 1, total_steps, "抓取财经新闻...")
            ctx = self.skills["news_fetch"].execute(ctx, days_lookback=days_lookback)
            ctx.log("news_fetch", "success", f"获取 {len(ctx.news_raw)} 条新闻")
            
            # Step 2: Theme Heat
            self._progress("theme_heat", 2, total_steps, "提取热门主题...")
            ctx = self.skills["theme_heat"].execute(ctx, llm_client=self.llm_client if use_llm else None)
            ctx.log("theme_heat", "success", f"提取 {len(ctx.themes_raw)} 个主题")
            
            # Step 3: Canonicalize
            self._progress("canonicalize", 3, total_steps, "标准化主题名称...")
            ctx = self.skills["canonicalize"].execute(ctx, llm_client=self.llm_client if use_llm else None)
            ctx.log("canonicalize", "success", f"标准化后 {len(ctx.themes_canonical)} 个主题")
            
            # Step 4: Theme Validate
            self._progress("theme_validate", 4, total_steps, "验证主题有效性...")
            ctx = self.skills["theme_validate"].execute(ctx)
            ctx.log("theme_validate", "success", f"有效主题 {len(ctx.themes_validated)} 个")
            
            # Step 5: Theme Regime
            self._progress("theme_regime", 5, total_steps, "判定主题生命周期...")
            ctx = self.skills["theme_regime"].execute(ctx, top_n=top_n_themes)
            ctx.log("theme_regime", "success", f"确定生命周期 {len(ctx.themes_with_regime)} 个")
            
            # Step 6: Theme Stock Bridge
            self._progress("theme_stock_bridge", 6, total_steps, "建立主题-股票映射...")
            ctx = self.skills["theme_stock_bridge"].execute(ctx)
            ctx.log("theme_stock_bridge", "success", f"映射股票池 {sum(len(v) for v in ctx.theme_stock_map.values())} 只")
            
            # Step 7: Strategy Select
            self._progress("strategy_select", 7, total_steps, "选择最优策略...")
            ctx = self.skills["strategy_select"].execute(ctx)
            ctx.log("strategy_select", "success", f"策略计划 {len(ctx.strategy_plan)} 个")
            
            # Step 8: Backfill Enriched
            self._progress("backfill_enriched", 8, total_steps, "补充量化因子...")
            ctx = self.skills["backfill_enriched"].execute(ctx)
            ctx.log("backfill_enriched", "success", "数据补充完成")
            
            # Step 9: Feedback Curator
            self._progress("feedback_curator", 9, total_steps, "加载历史反馈...")
            ctx = self.skills["feedback_curator"].execute(ctx)
            ctx.log("feedback_curator", "success", "反馈数据已加载")
            
            # Step 10: Stock Pick
            self._progress("stock_pick", 10, total_steps, "核心选股环节...")
            ctx = self.skills["stock_pick"].execute(
                ctx, 
                llm_client=self.llm_client if use_llm else None,
                top_n=top_n_stocks,
                relaxed_filter=relaxed_filter,
            )
            filter_msg = f"(候选{getattr(ctx, 'candidates_count', 0)}只,过滤{getattr(ctx, 'filtered_count', 0)}只)" if hasattr(ctx, 'candidates_count') else ""
            ctx.log("stock_pick", "success", f"选出 {len(ctx.picks)} 只股票{filter_msg}")
            
            # Step 11: Chief Risk
            self._progress("chief_risk", 11, total_steps, "风控审查...")
            ctx = self.skills["chief_risk"].execute(ctx)
            ctx.log("chief_risk", "success", f"风控后剩余 {len(ctx.risk_filtered_picks)} 只")
            
            # Step 12: Report Generator
            self._progress("report_generator", 12, total_steps, "生成投资研报...")
            ctx = self.skills["report_generator"].execute(ctx)
            ctx.log("report_generator", "success", "研报已生成")
            
            # Step 13: Outcome Enrich
            self._progress("outcome_enrich", 13, total_steps, "保存运行结果...")
            ctx = self.skills["outcome_enrich"].execute(ctx)
            ctx.log("outcome_enrich", "success", "结果已保存")
            
        except Exception as e:
            ctx.log("error", "failed", str(e))
            print(f"[Orchestrator] 流水线执行失败: {e}")
            import traceback
            traceback.print_exc()
        
        return ctx


def run_multi_agent_scan(
    days_lookback: int = 3,
    top_n_themes: int = 10,
    top_n_stocks: int = 20,
    use_llm: bool = True,
    relaxed_filter: bool = False,
    progress_callback: Optional[Callable[[str, int, int, str], None]] = None,
) -> Tuple[List[Dict[str, Any]], str, SkillContext]:
    """
    多智能体扫描入口函数
    
    :return: (股票列表, 研报Markdown, 完整上下文)
    """
    # 尝试初始化LLM客户端
    llm_client = None
    if use_llm:
        try:
            from scanner.llm.client import DeepSeekClient
            llm_client = DeepSeekClient()
        except Exception as e:
            print(f"[Warning] LLM客户端初始化失败: {e}，将使用备用逻辑")
    
    # 创建编排器并执行
    orchestrator = Orchestrator(
        llm_client=llm_client,
        progress_callback=progress_callback,
    )
    
    ctx = orchestrator.run_pipeline(
        days_lookback=days_lookback,
        top_n_themes=top_n_themes,
        top_n_stocks=top_n_stocks,
        use_llm=use_llm,
        relaxed_filter=relaxed_filter,
    )
    
    return ctx.risk_filtered_picks, ctx.report, ctx
