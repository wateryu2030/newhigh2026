# OpenClaw A股数据 Skill 与可扩展技能包
# 使用方式：from skills.a_share_skill import load_skill; skill = load_skill()
from .a_share_skill import AShareSkill, load_skill

__all__ = ["AShareSkill", "load_skill"]
