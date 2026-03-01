# -*- coding: utf-8 -*-
"""
券商适配层：统一 Broker 接口，模拟 / QMT 等。
"""
from .base import BrokerBase
from .sim_adapter import SimBrokerAdapter

__all__ = ["BrokerBase", "SimBrokerAdapter"]
