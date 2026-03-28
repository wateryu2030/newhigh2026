/**
 * 新闻 API 客户端（policy-news FastAPI，默认 8001）
 * 开发：vite 将 /news 代理到 8001；生产可设 VITE_NEWS_API_URL
 */
import apiClient from './client'

const NEWS_BASE_URL = import.meta.env.VITE_NEWS_API_URL || ''

export function getNewsList(params = {}) {
  return apiClient.get(`${NEWS_BASE_URL}/news`, { params })
}

export function getNewsDetail(id) {
  return apiClient.get(`${NEWS_BASE_URL}/news/${id}`)
}

export function getCategories() {
  return apiClient.get(`${NEWS_BASE_URL}/news/categories`)
}

export function getSources() {
  return apiClient.get(`${NEWS_BASE_URL}/news/sources`)
}

export function getStats() {
  return apiClient.get(`${NEWS_BASE_URL}/news/stats`)
}

export default {
  getNewsList,
  getNewsDetail,
  getCategories,
  getSources,
  getStats
}
