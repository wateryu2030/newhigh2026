/**
 * 股票行情 API
 */
import apiClient from './client'

const BASE_URL = '/api/stocks'

/**
 * 获取实时行情
 */
export function getQuote(symbol) {
  return apiClient.get(`${BASE_URL}/quote/${symbol}`)
}

/**
 * 批量获取行情
 */
export function getQuotes(symbols) {
  return apiClient.get(`${BASE_URL}/quotes`, {
    params: { symbols: symbols.join(',') }
  })
}

/**
 * 获取历史行情
 */
export function getHistory(symbol, startDate, endDate, adjust = 'qfq') {
  return apiClient.get(`${BASE_URL}/${symbol}/history`, {
    params: { start_date: startDate, end_date: endDate, adjust }
  })
}

/**
 * 获取 K 线数据
 */
export function getKline(symbol, period = 'daily', limit = 100) {
  return apiClient.get(`${BASE_URL}/${symbol}/kline`, {
    params: { period, limit }
  })
}

/**
 * 获取股票信息
 */
export function getStockInfo(symbol) {
  return apiClient.get(`${BASE_URL}/${symbol}/info`)
}

/**
 * 搜索股票
 */
export function searchStocks(keyword) {
  return apiClient.get(`${BASE_URL}/search`, {
    params: { keyword }
  })
}
