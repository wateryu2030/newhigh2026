"""
WebSocket 实时推送
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, List
import json
import asyncio
from datetime import datetime

router = APIRouter()


class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        # user_id -> [WebSocket]
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """接受连接"""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """断开连接"""
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
    
    async def send_personal_message(self, message: dict, user_id: str):
        """发送个人消息"""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass
    
    async def broadcast(self, message: dict):
        """广播消息"""
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except:
                    pass


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, user_id: str = None, token: str = None):
    """WebSocket 连接端点"""
    # TODO: 验证 Token
    
    if not user_id:
        await websocket.close(code=4001, reason="Missing user_id")
        return
    
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 处理心跳
            if message.get('type') == 'heartbeat':
                await websocket.send_json({
                    'type': 'heartbeat_ack',
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            # 处理订阅
            elif message.get('type') == 'subscribe':
                channels = message.get('data', {}).get('channels', [])
                await websocket.send_json({
                    'type': 'subscribed',
                    'channels': channels
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket, user_id)


# ============== 推送函数 ==============

async def push_quote(symbol: str, quote: dict):
    """推送行情"""
    await manager.broadcast({
        'type': 'quote',
        'data': {
            'symbol': symbol,
            **quote
        }
    })


async def push_order_fill(user_id: str, order: dict):
    """推送委托成交"""
    await manager.send_personal_message({
        'type': 'order_fill',
        'data': order
    }, user_id)


async def push_risk_alert(user_id: str, alert: dict):
    """推送风险预警"""
    await manager.send_personal_message({
        'type': 'risk_alert',
        'data': alert
    }, user_id)


async def push_strategy_signal(user_id: str, signal: dict):
    """推送策略信号"""
    await manager.send_personal_message({
        'type': 'strategy_signal',
        'data': signal
    }, user_id)
