#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKShare 数据源 Mod - RQAlpha 模块
用于在 RQAlpha 中启用 AKShare 数据源适配器
"""
from rqalpha.interface import AbstractMod
from data_source.akshare_rqalpha_ds import AKShareRQAlphaDataSource


class AKShareDataSourceMod(AbstractMod):
    """AKShare 数据源 Mod"""
    
    def start_up(self, env, mod_config):
        """启动时注册数据源"""
        # 获取配置
        cache_ttl_hours = getattr(mod_config, 'cache_ttl_hours', 1)
        
        # 创建数据源实例
        data_source = AKShareRQAlphaDataSource(cache_ttl_hours=cache_ttl_hours)
        
        # 替换默认数据源
        env.set_data_source(data_source)
        env.user_system_log.info("✅ 已切换到 AKShare 数据源")
    
    def tear_down(self, code, exception=None):
        """清理资源"""
        pass


def load_mod():
    """RQAlpha Mod 加载函数（必需）"""
    return AKShareDataSourceMod()
