<template>
  <div class="position-page">
    <el-container>
      <!-- 顶部导航 -->
      <el-header class="header">
        <div class="logo">🚀 红山量化平台</div>
        <el-menu mode="horizontal" :ellipsis="false" @select="handleMenuSelect">
          <el-menu-item index="market">行情</el-menu-item>
          <el-menu-item index="trade">交易</el-menu-item>
          <el-menu-item index="position">持仓</el-menu-item>
          <el-menu-item index="strategy">策略</el-menu-item>
          <el-menu-item index="risk">风控</el-menu-item>
        </el-menu>
      </el-header>

      <!-- 主内容区 -->
      <el-main>
        <!-- 资产概览 -->
        <el-row :gutter="20" style="margin-bottom: 20px;">
          <el-col :span="6">
            <el-card>
              <div class="asset-card">
                <div class="asset-label">总资产</div>
                <div class="asset-value">¥{{ totalAssets.toLocaleString() }}</div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card>
              <div class="asset-card">
                <div class="asset-label">可用资金</div>
                <div class="asset-value">¥{{ availableCash.toLocaleString() }}</div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card>
              <div class="asset-card">
                <div class="asset-label">持仓市值</div>
                <div class="asset-value">¥{{ marketValue.toLocaleString() }}</div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card>
              <div class="asset-card">
                <div class="asset-label">浮动盈亏</div>
                <div class="asset-value" :class="profit >= 0 ? 'text-up' : 'text-down'">
                  {{ profit >= 0 ? '+' : '' }}¥{{ profit.toLocaleString() }}
                </div>
                <div class="asset-percent" :class="profitRate >= 0 ? 'text-up' : 'text-down'">
                  {{ profitRate >= 0 ? '+' : '' }}{{ profitRate }}%
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <!-- 持仓列表 -->
        <el-card>
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <h3>持仓明细</h3>
              <el-button type="primary" size="small" @click="refreshPositions">刷新</el-button>
            </div>
          </template>
          
          <el-table :data="positions" style="width: 100%" v-loading="loading">
            <el-table-column prop="symbol" label="代码" width="100" sortable />
            <el-table-column prop="name" label="名称" width="120" />
            <el-table-column prop="costPrice" label="成本价" width="100" sortable />
            <el-table-column prop="currentPrice" label="当前价" width="100" sortable>
              <template #default="{ row }">
                <span :class="row.currentPrice >= row.costPrice ? 'text-up' : 'text-down'">
                  {{ row.currentPrice.toFixed(2) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="quantity" label="持仓数量" width="100" sortable />
            <el-table-column prop="marketValue" label="持仓市值" width="120" sortable>
              <template #default="{ row }">
                ¥{{ row.marketValue.toLocaleString() }}
              </template>
            </el-table-column>
            <el-table-column prop="profit" label="浮动盈亏" width="120" sortable>
              <template #default="{ row }">
                <span :class="row.profit >= 0 ? 'text-up' : 'text-down'">
                  {{ row.profit >= 0 ? '+' : '' }}¥{{ row.profit.toLocaleString() }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="profitRate" label="盈亏比例" width="100" sortable>
              <template #default="{ row }">
                <span :class="row.profitRate >= 0 ? 'text-up' : 'text-down'">
                  {{ row.profitRate >= 0 ? '+' : '' }}{{ row.profitRate }}%
                </span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" size="small" @click="handleTrade(row)">交易</el-button>
                <el-button type="danger" size="small" @click="handleSell(row)">卖出</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- 交易记录 -->
        <el-card style="margin-top: 20px;">
          <template #header>
            <h3>交易记录</h3>
          </template>
          
          <el-table :data="tradeHistory" style="width: 100%">
            <el-table-column prop="date" label="日期" width="120" />
            <el-table-column prop="symbol" label="代码" width="100" />
            <el-table-column prop="name" label="名称" width="120" />
            <el-table-column prop="type" label="类型" width="80">
              <template #default="{ row }">
                <el-tag :type="row.type === 'buy' ? 'success' : 'danger'" size="small">
                  {{ row.type === 'buy' ? '买入' : '卖出' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="price" label="成交价" width="100" />
            <el-table-column prop="quantity" label="数量" width="100" />
            <el-table-column prop="amount" label="金额" width="120">
              <template #default="{ row }">
                ¥{{ row.amount.toLocaleString() }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { getPositions, getAccountInfo } from '../api/positions'
import { getOrders, cancelOrder } from '../api/orders'

const router = useRouter()

const loading = ref(false)

// 账户信息
const availableCash = ref(331200)
const marketValue = ref(168800)
const totalAssets = computed(() => availableCash.value + marketValue.value)
const profit = ref(12345)
const profitRate = computed(() => ((profit.value / (totalAssets.value - profit.value)) * 100).toFixed(2))

// 持仓列表
const positions = ref([
  {
    symbol: '600519',
    name: '贵州茅台',
    costPrice: 1650.00,
    currentPrice: 1688.00,
    quantity: 100,
    marketValue: 168800,
    profit: 3800,
    profitRate: 2.30
  }
])

// 交易记录
const tradeHistory = ref([])

// 加载交易记录
const loadTradeHistory = async () => {
  try {
    const orders = await getOrders({ status: 'filled', limit: 50 })
    tradeHistory.value = orders.map(order => ({
      date: new Date(order.order_time).toLocaleDateString('zh-CN'),
      symbol: order.symbol,
      name: order.stock_name,
      type: order.order_type,
      price: order.order_price,
      quantity: order.order_quantity,
      amount: order.filled_amount
    }))
  } catch (error) {
    console.error('加载交易记录失败:', error)
  }
}

// 菜单选择
const handleMenuSelect = (index) => {
  const routes = {
    market: '/market',
    trade: '/trade',
    position: '/position',
    strategy: '/strategy',
    risk: '/risk'
  }
  if (routes[index]) {
    router.push(routes[index])
  }
}

// 刷新持仓
const refreshPositions = async () => {
  loading.value = true
  try {
    const [positionsData, accountData] = await Promise.all([
      getPositions({ show_closed: false }),
      getAccountInfo()
    ])
    
    positions.value = positionsData.map(pos => ({
      ...pos,
      symbol: pos.symbol,
      name: pos.stock_name,
      costPrice: pos.cost_price,
      currentPrice: pos.current_price,
      quantity: pos.quantity,
      marketValue: pos.market_value,
      profit: pos.profit,
      profitRate: pos.profit_rate
    }))
    
    availableCash.value = accountData.available_cash
    marketValue.value = accountData.market_value
    profit.value = accountData.total_profit
    
    ElMessage.success('持仓已刷新')
  } catch (error) {
    ElMessage.error('刷新失败：' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

// 交易
const handleTrade = (row) => {
  router.push(`/trade?symbol=${row.symbol}`)
}

// 卖出
const handleSell = (row) => {
  ElMessageBox.confirm(
    `确认卖出 ${row.name} (${row.symbol}) 吗？`,
    '卖出确认',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    ElMessage.success('卖出委托已提交')
  }).catch(() => {})
}

onMounted(() => {
  refreshPositions()
  loadTradeHistory()
})
</script>

<style scoped>
.position-page {
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

.asset-card {
  text-align: center;
}

.asset-label {
  font-size: 14px;
  color: #6b7280;
  margin-bottom: 8px;
}

.asset-value {
  font-size: 24px;
  font-weight: bold;
  color: #1e40af;
}

.asset-percent {
  font-size: 14px;
  margin-top: 4px;
}

.text-up {
  color: #dc2626;
}

.text-down {
  color: #16a34a;
}
</style>
