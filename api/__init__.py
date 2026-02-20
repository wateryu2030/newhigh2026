# -*- coding: utf-8 -*-
"""
API 层：统一注册回测、扫描、优化、组合、数据等 HTTP 接口。
与 web_platform 解耦：本包提供 register_routes(app)，由 web_platform 调用。
"""
from .routes import register_routes

__all__ = ["register_routes"]
