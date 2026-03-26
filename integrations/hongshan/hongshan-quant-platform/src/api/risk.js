/**
 * 风控 API
 */
import apiClient from './client'

const BASE_URL = '/api/risk'

/**
 * 获取风控配置
 */
export function getRiskConfig() {
  return apiClient.get(`${BASE_URL}/config`)
}

/**
 * 更新风控配置
 */
export function updateRiskConfig(configData) {
  return apiClient.put(`${BASE_URL}/config`, configData)
}

/**
 * 获取风险预警列表
 */
export function getRiskAlerts(params = {}) {
  return apiClient.get(`${BASE_URL}/alerts`, { params })
}

/**
 * 处理预警
 */
export function handleAlert(alertId) {
  return apiClient.post(`${BASE_URL}/alerts/${alertId}/handle`)
}

/**
 * 获取风险指标
 */
export function getRiskMetrics() {
  return apiClient.get(`${BASE_URL}/metrics`)
}
