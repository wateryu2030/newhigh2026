/**
 * 策略 API
 */
import apiClient from './client'

const BASE_URL = '/api/strategies'

/**
 * 创建策略
 */
export function createStrategy(strategyData) {
  return apiClient.post(`${BASE_URL}/strategies`, strategyData)
}

/**
 * 获取策略列表
 */
export function getStrategies() {
  return apiClient.get(`${BASE_URL}/strategies`)
}

/**
 * 启动策略
 */
export function startStrategy(strategyId) {
  return apiClient.post(`${BASE_URL}/strategies/${strategyId}/start`)
}

/**
 * 停止策略
 */
export function stopStrategy(strategyId) {
  return apiClient.post(`${BASE_URL}/strategies/${strategyId}/stop`)
}

/**
 * 执行回测
 */
export function runBacktest(strategyId, backtestData) {
  return apiClient.post(`${BASE_URL}/strategies/${strategyId}/backtest`, backtestData)
}
