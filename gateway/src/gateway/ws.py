"""WebSocket endpoints: /ws/market, /ws/trades, /ws/portfolio (stub for real-time push)."""

import asyncio
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
_connections: Set[WebSocket] = set()


@router.websocket("/market")
async def ws_market(websocket: WebSocket) -> None:
    """Real-time market data (stub: wire to data-engine stream)."""
    await websocket.accept()
    _connections.add(websocket)
    try:
        while True:
            _ = await websocket.receive_text()
            await websocket.send_json({"path": "market", "type": "klines", "data": []})
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        _connections.discard(websocket)


@router.websocket("/trades")
async def ws_trades(websocket: WebSocket) -> None:
    """Real-time trades (stub: wire to execution-engine)."""
    await websocket.accept()
    _connections.add(websocket)
    try:
        while True:
            _ = await websocket.receive_text()
            await websocket.send_json({"path": "trades", "trades": []})
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        _connections.discard(websocket)


@router.websocket("/portfolio")
async def ws_portfolio(websocket: WebSocket) -> None:
    """Real-time portfolio/equity (stub: wire to portfolio-engine)."""
    await websocket.accept()
    _connections.add(websocket)
    try:
        while True:
            _ = await websocket.receive_text()
            await websocket.send_json({"path": "portfolio", "equity": 0, "positions": []})
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        _connections.discard(websocket)
