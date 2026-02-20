# -*- coding: utf-8 -*-
"""
实盘监控 API：FastAPI 提供持仓、订单、盈亏等接口，供 Dashboard 消费。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI(title="Astock 实盘监控 API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 占位数据，后续可接入 PortfolioManager / 交易网关
_positions = []
_orders = []
_pnl = 0.0


@app.get("/positions")
def positions():
    """当前持仓列表。"""
    return {"positions": _positions}


@app.get("/orders")
def orders():
    """最近订单列表。"""
    return {"orders": _orders}


@app.get("/pnl")
def pnl():
    """累计盈亏。"""
    return {"pnl": _pnl}


# 可选：挂载 dashboard 静态页
_dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard")
if os.path.isdir(_dashboard_path):
    app.mount("/static", StaticFiles(directory=_dashboard_path), name="static")

    @app.get("/")
    def index():
        p = os.path.join(_dashboard_path, "index.html")
        if os.path.isfile(p):
            return FileResponse(p)
        return {"message": "Astock Monitor API", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
