<template>
  <div class="market-page">
    <el-container>
      <!-- 顶部导航 -->
      <el-header class="header">
        <div class="logo">🚀 红山量化平台</div>
        <el-menu mode="horizontal" :ellipsis="false">
          <el-menu-item index="1">行情</el-menu-item>
          <el-menu-item index="2">交易</el-menu-item>
          <el-menu-item index="3">持仓</el-menu-item>
          <el-menu-item index="4">策略</el-menu-item>
          <el-menu-item index="5">风控</el-menu-item>
        </el-menu>
      </el-header>

      <!-- 主内容区 -->
      <el-main>
        <!-- 搜索栏 -->
        <div class="search-bar">
          <el-input
            v-model="searchQuery"
            placeholder="搜索股票代码/名称/拼音"
            prefix-icon="Search"
            clearable
            @keyup.enter="handleSearch"
          />
          <el-button type="primary" @click="handleSearch">搜索</el-button>
        </div>

        <!-- 股票列表表格 -->
        <el-table
          :data="stockList"
          style="width: 100%"
          v-loading="loading"
          @row-click="handleRowClick"
        >
          <el-table-column prop="symbol" label="代码" width="100" sortable />
          <el-table-column prop="name" label="名称" width="120" />
          <el-table-column prop="price" label="最新价" sortable>
            <template #default="{ row }">
              <span :class="getPriceClass(row.change)">
                {{ row.price.toFixed(2) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="change" label="涨跌额" sortable>
            <template #default="{ row }">
              <span :class="getPriceClass(row.change)">
                {{ row.change > 0 ? '+' : '' }}{{ row.change.toFixed(2) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="change_percent" label="涨跌幅%" sortable>
            <template #default="{ row }">
              <span :class="getPriceClass(row.change)">
                {{ row.change > 0 ? '+' : '' }}{{ row.change_percent.toFixed(2) }}%
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="volume" label="成交量" sortable />
          <el-table-column prop="amount" label="成交额" sortable>
            <template #default="{ row }">
              {{ formatAmount(row.amount) }}
            </template>
          </el-table-column>
          <el-table-column prop="timestamp" label="时间" width="180" />
        </el-table>

        <!-- 分页 -->
        <div class="pagination">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[20, 50, 100]"
            layout="total, sizes, prev, pager, next"
            :total="total"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </el-main>

      <!-- 底部状态栏 -->
      <el-footer class="footer">
        <div class="status-bar">
          <span>市场状态：<el-tag :type="marketStatus === 'open' ? 'success' : 'info'">
            {{ marketStatus === 'open' ? '交易中' : '已收盘' }}
          </el-tag></span>
          <span>最后更新：{{ lastUpdateTime }}</span>
        </div>
      </el-footer>
    </el-container>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'

// 搜索相关
const searchQuery = ref('')
const stockList = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const marketStatus = ref('open')
const lastUpdateTime = ref('')

// API 基础 URL
const API_BASE = 'http://localhost:8000/api'

// 获取股票列表
const fetchStocks = async () => {
  loading.value = true
  try {
    // TODO: 替换为实际 API 调用
    // const response = await fetch(`${API_BASE}/stocks/list`)
    // const data = await response.json()
    
    // 模拟数据
    const mockData = [
      { symbol: '600519', name: '贵州茅台', price: 1688.00, change: 12.30, change_percent: 0.73, volume: 1234567, amount: 2080000000, timestamp: '2026-03-26 15:45:00' },
      { symbol: '000858', name: '五粮液', price: 168.50, change: -2.30, change_percent: -1.35, volume: 2345678, amount: 395000000, timestamp: '2026-03-26 15:45:00' },
      { symbol: '601318', name: '中国平安', price: 52.80, change: 0.85, change_percent: 1.64, volume: 3456789, amount: 182000000, timestamp: '2026-03-26 15:45:00' },
    ]
    
    stockList.value = mockData
    total.value = mockData.length
    lastUpdateTime.value = new Date().toLocaleTimeString()
  } catch (error) {
    ElMessage.error('获取股票列表失败：' + error.message)
  } finally {
    loading.value = false
  }
}

// 搜索处理
const handleSearch = async () => {
  if (!searchQuery.value.trim()) {
    fetchStocks()
    return
  }
  
  loading.value = true
  try {
    const response = await fetch(`${API_BASE}/stocks/search?q=${encodeURIComponent(searchQuery.value)}`)
    const data = await response.json()
    stockList.value = data
    total.value = data.length
  } catch (error) {
    ElMessage.error('搜索失败：' + error.message)
  } finally {
    loading.value = false
  }
}

// 行点击事件
const handleRowClick = (row) => {
  ElMessage.info(`点击股票：${row.name} (${row.symbol})`)
  // TODO: 跳转到详情页或 K 线图
}

// 价格颜色类
const getPriceClass = (change) => {
  if (change > 0) return 'price-up'
  if (change < 0) return 'price-down'
  return 'price-flat'
}

// 格式化成交额
const formatAmount = (amount) => {
  if (amount >= 1e9) return (amount / 1e9).toFixed(2) + '亿'
  if (amount >= 1e6) return (amount / 1e6).toFixed(2) + '万'
  return amount.toFixed(2)
}

// 分页处理
const handleSizeChange = () => {
  fetchStocks()
}

const handleCurrentChange = () => {
  fetchStocks()
}

// 定时刷新（30 秒）
let refreshTimer = null
const startAutoRefresh = () => {
  refreshTimer = setInterval(() => {
    fetchStocks()
  }, 30000) // 30 秒
}

// 生命周期
onMounted(() => {
  fetchStocks()
  startAutoRefresh()
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.market-page {
  min-height: 100vh;
  background-color: #f5f7fa;
}

.header {
  background-color: #1e40af;
  display: flex;
  align-items: center;
  padding: 0 20px;
}

.logo {
  color: white;
  font-size: 20px;
  font-weight: bold;
  margin-right: 40px;
}

:deep(.el-menu) {
  background-color: #1e40af;
  border: none;
}

:deep(.el-menu-item) {
  color: white;
}

:deep(.el-menu-item:hover),
:deep(.el-menu-item.is-active) {
  background-color: #3b82f6;
}

.search-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  padding: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.footer {
  background-color: #f0f2f5;
  border-top: 1px solid #e4e7ed;
  padding: 10px 20px;
}

.status-bar {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: #606266;
}

.price-up {
  color: #dc2626;
  font-weight: 500;
}

.price-down {
  color: #16a34a;
  font-weight: 500;
}

.price-flat {
  color: #606266;
}
</style>
