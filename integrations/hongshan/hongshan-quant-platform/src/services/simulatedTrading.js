/**
 * 模拟交易服务
 * 用于实盘模拟测试
 */

import { getQuote } from './stocks'
import { createOrder, getOrders, cancelOrder } from './orders'
import { getPositions, getAccountInfo } from './positions'

class SimulatedTradingService {
  constructor() {
    this.userId = localStorage.getItem('user_id') || 'simulated-user'
    this.isSimulated = true
    this.simulationDelay = 1000 // 模拟延迟 (ms)
  }

  /**
   * 模拟下单
   */
  async placeOrder(orderData) {
    console.log('[模拟交易] 下单:', orderData)
    
    // 模拟网络延迟
    await this._delay(this.simulationDelay)
    
    try {
      // 调用真实 API
      const result = await createOrder({
        ...orderData,
        user_id: this.userId
      })
      
      console.log('[模拟交易] 下单成功:', result)
      
      // 发送飞书通知 (通过后端)
      this._notifyTrade(orderData, result)
      
      return result
    } catch (error) {
      console.error('[模拟交易] 下单失败:', error)
      throw error
    }
  }

  /**
   * 模拟撤单
   */
  async cancelOrderById(orderId) {
    console.log('[模拟交易] 撤单:', orderId)
    
    await this._delay(this.simulationDelay)
    
    try {
      const result = await cancelOrder(orderId)
      console.log('[模拟交易] 撤单成功:', result)
      return result
    } catch (error) {
      console.error('[模拟交易] 撤单失败:', error)
      throw error
    }
  }

  /**
   * 获取模拟持仓
   */
  async getPositions() {
    try {
      const positions = await getPositions({ user_id: this.userId })
      return positions
    } catch (error) {
      console.error('[模拟交易] 获取持仓失败:', error)
      return []
    }
  }

  /**
   * 获取模拟账户信息
   */
  async getAccountInfo() {
    try {
      const account = await getAccountInfo()
      return account
    } catch (error) {
      console.error('[模拟交易] 获取账户失败:', error)
      return {
        total_assets: 500000,
        available_cash: 500000,
        market_value: 0,
        total_profit: 0,
        total_profit_rate: 0
      }
    }
  }

  /**
   * 获取当前委托
   */
  async getCurrentOrders() {
    try {
      const orders = await getOrders({
        user_id: this.userId,
        status: 'pending'
      })
      return orders
    } catch (error) {
      console.error('[模拟交易] 获取委托失败:', error)
      return []
    }
  }

  /**
   * 模拟成交回报
   */
  _notifyTrade(orderData, orderResult) {
    // 后端会自动发送飞书通知
    console.log('[模拟交易] 已触发飞书通知')
  }

  /**
   * 延迟工具
   */
  _delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms))
  }

  /**
   * 设置模拟模式
   */
  setSimulationMode(enabled) {
    this.isSimulated = enabled
    console.log('[模拟交易] 模拟模式:', enabled ? '开启' : '关闭')
  }

  /**
   * 设置模拟延迟
   */
  setDelay(ms) {
    this.simulationDelay = ms
    console.log('[模拟交易] 延迟设置为:', ms, 'ms')
  }
}

// 单例
export const simulatedTradingService = new SimulatedTradingService()
