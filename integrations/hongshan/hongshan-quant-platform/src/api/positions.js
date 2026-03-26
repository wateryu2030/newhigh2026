/**
 * 持仓 API
 */
import apiClient from './client'

const BASE_URL = '/api/positions'

/**
 * 获取持仓列表
 */
export function getPositions(params = {}) {
  return apiClient.get(`${BASE_URL}/positions`, { params })
}

/**
 * 获取单个持仓
 */
export function getPosition(symbol) {
  return apiClient.get(`${BASE_URL}/positions/${symbol}`)
}

/**
 * 获取账户信息
 */
export function getAccountInfo() {
  return apiClient.get(`${BASE_URL}/account`)
}
