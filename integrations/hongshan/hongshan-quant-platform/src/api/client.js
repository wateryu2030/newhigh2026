/**
 * API 客户端配置
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'

// 默认空：开发时走 Vite 同源 + proxy（见 vite.config.js → 8010）；生产 Docker Nginx 同源 /api
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

// 创建 axios 实例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
apiClient.interceptors.request.use(
  config => {
    // 添加用户 ID (从 localStorage 获取)
    const userId = localStorage.getItem('user_id')
    if (userId) {
      config.params = {
        ...config.params,
        user_id: userId
      }
    }
    return config
  },
  error => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    console.error('响应错误:', error)
    
    if (error.response) {
      const { status, data } = error.response
      
      switch (status) {
        case 400:
          ElMessage.error(data.detail || '请求参数错误')
          break
        case 401:
          ElMessage.error('未授权，请登录')
          break
        case 404:
          ElMessage.error(data.detail || '资源不存在')
          break
        case 500:
          ElMessage.error('服务器错误')
          break
        default:
          ElMessage.error(data.detail || '请求失败')
      }
    } else if (error.request) {
      ElMessage.error('网络连接失败，请检查服务器是否启动')
    } else {
      ElMessage.error(error.message || '未知错误')
    }
    
    return Promise.reject(error)
  }
)

export default apiClient
