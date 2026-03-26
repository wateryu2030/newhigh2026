<template>
  <div class="trade-page">
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
        <el-row :gutter="20">
          <!-- 左侧：交易表单 -->
          <el-col :span="12">
            <el-card>
              <template #header>
                <h3>股票交易</h3>
              </template>
              
              <!-- 股票选择 -->
              <el-form :model="tradeForm" label-width="100px">
                <el-form-item label="股票代码">
                  <el-input v-model="tradeForm.symbol" placeholder="输入股票代码" />
                </el-form-item>
                
                <el-form-item label="股票名称">
                  <el-input v-model="tradeForm.name" :disabled="true" />
                </el-form-item>
                
                <el-form-item label="当前价格">
                  <el-input v-model="tradeForm.price" :disabled="true" />
                </el-form-item>
                
                <el-form-item label="交易类型">
                  <el-radio-group v-model="tradeForm.type">
                    <el-radio label="buy">买入</el-radio>
                    <el-radio label="sell">卖出</el-radio>
                  </el-radio-group>
                </el-form-item>
                
                <el-form-item label="委托价格">
                  <el-input-number v-model="tradeForm.orderPrice" :min="0" :precision="2" :step="0.01" />
                </el-form-item>
                
                <el-form-item label="委托数量">
                  <el-input-number v-model="tradeForm.quantity" :min="100" :step="100" />
                </el-form-item>
                
                <el-form-item label="总金额">
                  <el-input v-model="totalAmount" :disabled="true" />
                </el-form-item>
                
                <el-form-item>
                  <el-button type="primary" @click="submitOrder" :loading="submitting">
                    {{ tradeForm.type === 'buy' ? '买入' : '卖出' }}
                  </el-button>
                  <el-button @click="resetForm">重置</el-button>
                </el-form-item>
              </el-form>
            </el-card>
          </el-col>
          
          <!-- 右侧：持仓和委托 -->
          <el-col :span="12">
            <!-- 可用资金 -->
            <el-card style="margin-bottom: 20px;">
              <template #header>
                <h3>账户信息</h3>
              </template>
              <el-descriptions :column="2" border>
                <el-descriptions-item label="可用资金">¥{{ availableCash.toLocaleString() }}</el-descriptions-item>
                <el-descriptions-item label="总资产">¥{{ totalAssets.toLocaleString() }}</el-descriptions-item>
                <el-descriptions-item label="持仓市值">¥{{ marketValue.toLocaleString() }}</el-descriptions-item>
                <el-descriptions-item label="浮动盈亏">
                  <span :class="profit >= 0 ? 'text-up' : 'text-down'">
                    {{ profit >= 0 ? '+' : '' }}¥{{ profit.toLocaleString() }}
                  </span>
                </el-descriptions-item>
              </el-descriptions>
            </el-card>
            
            <!-- 当前委托 -->
            <el-card>
              <template #header>
                <h3>当前委托</h3>
              </template>
              <el-table :data="currentOrders" style="width: 100%" size="small">
                <el-table-column prop="symbol" label="代码" width="80" />
                <el-table-column prop="name" label="名称" />
                <el-table-column prop="type" label="类型" width="60">
                  <template #default="{ row }">
                    <el-tag :type="row.type === 'buy' ? 'success' : 'danger'" size="small">
                      {{ row.type === 'buy' ? '买入' : '卖出' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="price" label="价格" width="80" />
                <el-table-column prop="quantity" label="数量" width="80" />
                <el-table-column prop="status" label="状态" width="60" />
              </el-table>
            </el-card>
          </el-col>
        </el-row>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { getQuote, searchStocks } from '../api/stocks'
import { createOrder } from '../api/orders'
import { getAccountInfo } from '../api/positions'
import { simulatedTradingService } from '../services/simulatedTrading'

const router = useRouter()

// 交易表单
const tradeForm = ref({
  symbol: '600519',
  name: '贵州茅台',
  price: 1688.00,
  type: 'buy',
  orderPrice: 1688.00,
  quantity: 100
})

const submitting = ref(false)

// 账户信息
const availableCash = ref(500000)
const marketValue = ref(168800)
const totalAssets = computed(() => availableCash.value + marketValue.value)
const profit = ref(12345)

// 当前委托
const currentOrders = ref([
  { symbol: '600519', name: '贵州茅台', type: 'buy', price: 1680.00, quantity: 100, status: '已报' }
])

// 总金额
const totalAmount = computed(() => {
  return (tradeForm.value.orderPrice * tradeForm.value.quantity).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
})

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

// 提交订单
const submitOrder = async () => {
  submitting.value = true
  
  try {
    // 使用模拟交易服务
    const result = await simulatedTradingService.placeOrder({
      symbol: tradeForm.value.symbol,
      order_type: tradeForm.value.type,
      order_style: 'limit',
      order_price: tradeForm.value.orderPrice,
      order_quantity: tradeForm.value.quantity
    })
    
    ElMessage.success(`${tradeForm.value.type === 'buy' ? '买入' : '卖出'}委托已提交！`)
    
    // 添加到委托列表
    currentOrders.value.push({
      symbol: tradeForm.value.symbol,
      name: tradeForm.value.name,
      type: tradeForm.value.type,
      price: tradeForm.value.orderPrice,
      quantity: tradeForm.value.quantity,
      status: result.status || '已报'
    })
    
    // 刷新账户信息
    await fetchAccountInfo()
    
  } catch (error) {
    ElMessage.error('委托失败：' + (error.response?.data?.detail || error.message))
  } finally {
    submitting.value = false
  }
}

// 重置表单
const resetForm = () => {
  tradeForm.value = {
    symbol: '',
    name: '',
    price: 0,
    type: 'buy',
    orderPrice: 0,
    quantity: 100
  }
}

// 监听股票代码变化
const fetchStockInfo = async () => {
  if (!tradeForm.value.symbol) return
  
  try {
    const data = await getQuote(tradeForm.value.symbol)
    tradeForm.value.name = data.name
    tradeForm.value.price = data.current_price
    tradeForm.value.orderPrice = data.current_price
  } catch (error) {
    ElMessage.warning('获取股票信息失败')
  }
}

// 获取账户信息
const fetchAccountInfo = async () => {
  try {
    const account = await getAccountInfo()
    availableCash.value = account.available_cash
    marketValue.value = account.market_value
    profit.value = account.total_profit
  } catch (error) {
    console.error('获取账户信息失败:', error)
  }
}

onMounted(() => {
  fetchStockInfo()
  fetchAccountInfo()
})
</script>

<style scoped>
.trade-page {
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

.text-up {
  color: #dc2626;
  font-weight: 500;
}

.text-down {
  color: #16a34a;
  font-weight: 500;
}
</style>
