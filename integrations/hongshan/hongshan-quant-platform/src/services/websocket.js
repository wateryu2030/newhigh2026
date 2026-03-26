/**
 * WebSocket 实时推送服务
 */

class WebSocketService {
  constructor() {
    this.ws = null
    this.reconnectTimer = null
    this.heartbeatTimer = null
    this.listeners = {}
    this.url = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
  }

  /**
   * 连接 WebSocket
   */
  connect(userId) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('[WebSocket] 已连接')
      return
    }

    const token = localStorage.getItem('access_token')
    const wsUrl = `${this.url}?token=${token}&user_id=${userId}`
    
    this.ws = new WebSocket(wsUrl)

    this.ws.onopen = () => {
      console.log('[WebSocket] 连接成功')
      this.reconnectAttempts = 0
      this.startHeartbeat()
    }

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        this.handleMessage(message)
      } catch (error) {
        console.error('[WebSocket] 消息解析失败:', error)
      }
    }

    this.ws.onclose = () => {
      console.log('[WebSocket] 连接关闭')
      this.stopHeartbeat()
      this.reconnect()
    }

    this.ws.onerror = (error) => {
      console.error('[WebSocket] 错误:', error)
    }
  }

  /**
   * 处理消息
   */
  handleMessage(message) {
    const { type, data } = message
    
    if (this.listeners[type]) {
      this.listeners[type].forEach(callback => callback(data))
    }

    // 默认监听器
    if (this.listeners['*']) {
      this.listeners['*'].forEach(callback => callback(message))
    }
  }

  /**
   * 重连
   */
  reconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('[WebSocket] 重连失败，已达最大尝试次数')
      return
    }

    this.reconnectAttempts++
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000)
    
    console.log(`[WebSocket] ${delay}ms 后重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
    
    this.reconnectTimer = setTimeout(() => {
      const userId = localStorage.getItem('user_id')
      if (userId) {
        this.connect(userId)
      }
    }, delay)
  }

  /**
   * 发送消息
   */
  send(type, data) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, data }))
    } else {
      console.warn('[WebSocket] 连接未打开，无法发送消息')
    }
  }

  /**
   * 监听消息
   */
  on(type, callback) {
    if (!this.listeners[type]) {
      this.listeners[type] = []
    }
    this.listeners[type].push(callback)

    // 返回取消监听函数
    return () => {
      this.listeners[type] = this.listeners[type].filter(cb => cb !== callback)
    }
  }

  /**
   * 开始心跳
   */
  startHeartbeat() {
    this.heartbeatTimer = setInterval(() => {
      this.send('heartbeat', { timestamp: Date.now() })
    }, 30000) // 30 秒
  }

  /**
   * 停止心跳
   */
  stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  /**
   * 断开连接
   */
  disconnect() {
    this.stopHeartbeat()
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }
}

// 单例
export const wsService = new WebSocketService()

// 快捷监听器
export const wsListeners = {
  // 行情推送
  onQuote: (callback) => wsService.on('quote', callback),
  
  // 委托成交
  onOrderFill: (callback) => wsService.on('order_fill', callback),
  
  // 风险预警
  onRiskAlert: (callback) => wsService.on('risk_alert', callback),
  
  // 策略信号
  onStrategySignal: (callback) => wsService.on('strategy_signal', callback),
  
  // 通用监听
  onAll: (callback) => wsService.on('*', callback)
}
