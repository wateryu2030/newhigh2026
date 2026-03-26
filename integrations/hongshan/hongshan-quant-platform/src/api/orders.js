/**
 * 交易委托 API
 */
import apiClient from './client'

const BASE_URL = '/api/orders'

/**
 * 创建委托
 */
export function createOrder(orderData) {
  return apiClient.post(`${BASE_URL}/orders`, orderData)
}

/**
 * 获取委托列表
 */
export function getOrders(params = {}) {
  return apiClient.get(`${BASE_URL}/orders`, { params })
}

/**
 * 获取委托详情
 */
export function getOrder(orderId) {
  return apiClient.get(`${BASE_URL}/orders/${orderId}`)
}

/**
 * 撤销委托
 */
export function cancelOrder(orderId) {
  return apiClient.post(`${BASE_URL}/orders/${orderId}/cancel`)
}
