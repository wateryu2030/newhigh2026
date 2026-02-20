#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库数据源 Mod - 通过 Mod 方式替换 RQAlpha 默认数据源
"""
from rqalpha.interface import AbstractMod
from rqalpha.environment import Environment
from database.db_data_source import DatabaseDataSource


class DatabaseDataSourceMod(AbstractMod):
    """数据库数据源 Mod"""
    
    def start_up(self, env, mod_config):
        """启动时替换数据源"""
        db_path = getattr(mod_config, "db_path", "data/astock.db")
        
        # 创建配置对象
        class DBConfig:
            def __init__(self, path):
                self.db_path = path
        
        db_config = DBConfig(db_path)
        
        # 替换数据源
        env.set_data_source(DatabaseDataSource(db_config))
        env.user_system_log.info("已切换到数据库数据源: {}".format(db_path))
    
    def tear_down(self, code, exception=None):
        pass


def load_mod():
    """Mod 加载函数（必需）"""
    return DatabaseDataSourceMod()
