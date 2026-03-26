<template>
  <div class="strategy-page">
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
          <!-- 左侧：策略列表 -->
          <el-col :span="16">
            <el-card>
              <template #header>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <h3>策略列表</h3>
                  <el-button type="primary" @click="showCreateDialog">新建策略</el-button>
                </div>
              </template>
              
              <el-table :data="strategies" style="width: 100%" v-loading="loading">
                <el-table-column prop="name" label="策略名称" width="150" />
                <el-table-column prop="type" label="类型" width="100">
                  <template #default="{ row }">
                    <el-tag :type="getTypeTag(row.type)" size="small">{{ row.type }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="symbols" label="标的" width="200" />
                <el-table-column prop="status" label="状态" width="80">
                  <template #default="{ row }">
                    <el-tag :type="row.status === 'running' ? 'success' : 'info'" size="small">
                      {{ row.status === 'running' ? '运行中' : '已停止' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="totalReturn" label="总收益" width="100" sortable>
                  <template #default="{ row }">
                    <span :class="row.totalReturn >= 0 ? 'text-up' : 'text-down'">
                      {{ row.totalReturn >= 0 ? '+' : '' }}{{ row.totalReturn }}%
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="sharpe" label="夏普比率" width="100" sortable />
                <el-table-column prop="maxDrawdown" label="最大回撤" width="100" sortable>
                  <template #default="{ row }">
                    <span class="text-down">{{ row.maxDrawdown }}%</span>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="200" fixed="right">
                  <template #default="{ row }">
                    <el-button 
                      v-if="row.status === 'stopped'"
                      type="success" 
                      size="small" 
                      @click="startStrategy(row)"
                    >启动</el-button>
                    <el-button 
                      v-else
                      type="warning" 
                      size="small" 
                      @click="stopStrategy(row)"
                    >停止</el-button>
                    <el-button type="primary" size="small" @click="backtest(row)">回测</el-button>
                    <el-button type="danger" size="small" @click="deleteStrategy(row)">删除</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
            
            <!-- 回测结果 -->
            <el-card style="margin-top: 20px;" v-if="showBacktest">
              <template #header>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <h3>回测结果 - {{ backtestResult.strategyName }}</h3>
                  <el-button @click="showBacktest = false">关闭</el-button>
                </div>
              </template>
              
              <el-row :gutter="20">
                <el-col :span="6">
                  <el-statistic title="总收益率" :value="backtestResult.totalReturn" suffix="%" />
                </el-col>
                <el-col :span="6">
                  <el-statistic title="年化收益" :value="backtestResult.annualReturn" suffix="%" />
                </el-col>
                <el-col :span="6">
                  <el-statistic title="夏普比率" :value="backtestResult.sharpe" />
                </el-col>
                <el-col :span="6">
                  <el-statistic title="最大回撤" :value="backtestResult.maxDrawdown" suffix="%" />
                </el-col>
              </el-row>
              
              <div id="backtest-chart" style="height: 400px; margin-top: 20px;"></div>
            </el-card>
          </el-col>
          
          <!-- 右侧：策略详情 -->
          <el-col :span="8">
            <el-card v-if="selectedStrategy">
              <template #header>
                <h3>策略详情</h3>
              </template>
              
              <el-descriptions :column="1" border>
                <el-descriptions-item label="策略名称">{{ selectedStrategy.name }}</el-descriptions-item>
                <el-descriptions-item label="策略类型">{{ selectedStrategy.type }}</el-descriptions-item>
                <el-descriptions-item label="交易标的">{{ selectedStrategy.symbols }}</el-descriptions-item>
                <el-descriptions-item label="运行状态">
                  <el-tag :type="selectedStrategy.status === 'running' ? 'success' : 'info'">
                    {{ selectedStrategy.status === 'running' ? '运行中' : '已停止' }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="启动时间">{{ selectedStrategy.startTime || '-' }}</el-descriptions-item>
                <el-descriptions-item label="持仓周期">{{ selectedStrategy.holdPeriod }}天</el-descriptions-item>
                <el-descriptions-item label="交易频率">{{ selectedStrategy.tradeFreq }}</el-descriptions-item>
              </el-descriptions>
              
              <el-divider>性能指标</el-divider>
              
              <el-descriptions :column="1" border>
                <el-descriptions-item label="总收益率">
                  <span :class="selectedStrategy.totalReturn >= 0 ? 'text-up' : 'text-down'">
                    {{ selectedStrategy.totalReturn >= 0 ? '+' : '' }}{{ selectedStrategy.totalReturn }}%
                  </span>
                </el-descriptions-item>
                <el-descriptions-item label="夏普比率">{{ selectedStrategy.sharpe }}</el-descriptions-item>
                <el-descriptions-item label="最大回撤">
                  <span class="text-down">{{ selectedStrategy.maxDrawdown }}%</span>
                </el-descriptions-item>
                <el-descriptions-item label="胜率">{{ selectedStrategy.winRate }}%</el-descriptions-item>
                <el-descriptions-item label="交易次数">{{ selectedStrategy.tradeCount }}</el-descriptions-item>
              </el-descriptions>
            </el-card>
            
            <el-card v-else>
              <el-empty description="请选择一个策略查看详情" />
            </el-card>
          </el-col>
        </el-row>
      </el-main>
    </el-container>
    
    <!-- 新建策略对话框 -->
    <el-dialog v-model="dialogVisible" title="新建策略" width="500px">
      <el-form :model="newStrategy" label-width="100px">
        <el-form-item label="策略名称">
          <el-input v-model="newStrategy.name" placeholder="输入策略名称" />
        </el-form-item>
        <el-form-item label="策略类型">
          <el-select v-model="newStrategy.type" placeholder="选择策略类型">
            <el-option label="双均线" value="双均线" />
            <el-option label="MACD" value="MACD" />
            <el-option label="RSI" value="RSI" />
            <el-option label="布林带" value="布林带" />
            <el-option label="自定义" value="自定义" />
          </el-select>
        </el-form-item>
        <el-form-item label="交易标的">
          <el-input v-model="newStrategy.symbols" placeholder="多个标的用逗号分隔，如：600519,000858" />
        </el-form-item>
        <el-form-item label="持仓周期">
          <el-input-number v-model="newStrategy.holdPeriod" :min="1" :max="60" /> 天
        </el-form-item>
        <el-form-item label="描述">
          <el-input 
            v-model="newStrategy.description" 
            type="textarea" 
            :rows="3"
            placeholder="策略描述（可选）"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createStrategy">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { getStrategies, createStrategy as apiCreateStrategy, startStrategy, stopStrategy, runBacktest } from '../api/strategies'

const router = useRouter()

const loading = ref(false)
const showBacktest = ref(false)
const dialogVisible = ref(false)
const selectedStrategy = ref(null)

const backtestResult = ref({
  strategyName: '',
  totalReturn: 0,
  annualReturn: 0,
  sharpe: 0,
  maxDrawdown: 0
})

const newStrategy = ref({
  name: '',
  type: '双均线',
  symbols: '',
  holdPeriod: 5,
  description: ''
})

const strategies = ref([])

// 加载策略列表
const loadStrategies = async () => {
  try {
    const data = await getStrategies()
    strategies.value = data.map(s => ({
      id: s.id,
      name: s.name,
      type: s.strategy_type,
      symbols: Array.isArray(s.symbols) ? s.symbols.join(',') : s.symbols,
      status: s.status,
      startTime: s.start_time,
      holdPeriod: s.params?.hold_period || 5,
      tradeFreq: '低频',
      totalReturn: 0,
      sharpe: 0,
      maxDrawdown: 0,
      winRate: 0,
      tradeCount: 0
    }))
  } catch (error) {
    console.error('加载策略失败:', error)
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

// 获取策略类型标签
const getTypeTag = (type) => {
  const map = {
    '双均线': 'primary',
    'MACD': 'success',
    'RSI': 'warning',
    '布林带': 'danger',
    '自定义': 'info'
  }
  return map[type] || 'info'
}

// 显示创建对话框
const showCreateDialog = () => {
  dialogVisible.value = true
}

// 创建策略
const createStrategy = async () => {
  if (!newStrategy.value.name || !newStrategy.value.symbols) {
    ElMessage.warning('请填写策略名称和交易标的')
    return
  }
  
  try {
    await apiCreateStrategy({
      name: newStrategy.value.name,
      strategy_type: newStrategy.value.type,
      symbols: newStrategy.value.symbols.split(',').map(s => s.trim()),
      params: {
        hold_period: newStrategy.value.holdPeriod,
        description: newStrategy.value.description
      },
      description: newStrategy.value.description
    })
    
    ElMessage.success('策略创建成功')
    dialogVisible.value = false
    newStrategy.value = {
      name: '',
      type: '双均线',
      symbols: '',
      holdPeriod: 5,
      description: ''
    }
    loadStrategies()
  } catch (error) {
    ElMessage.error('创建失败：' + (error.response?.data?.detail || error.message))
  }
}

// 启动策略
const startStrategyFn = async (row) => {
  ElMessageBox.confirm(
    `确认启动策略「${row.name}」吗？`,
    '启动确认',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await startStrategy(row.id)
      row.status = 'running'
      row.startTime = new Date().toLocaleString('zh-CN')
      ElMessage.success('策略已启动')
    } catch (error) {
      ElMessage.error('启动失败：' + (error.response?.data?.detail || error.message))
    }
  }).catch(() => {})
}

// 停止策略
const stopStrategyFn = async (row) => {
  ElMessageBox.confirm(
    `确认停止策略「${row.name}」吗？`,
    '停止确认',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await stopStrategy(row.id)
      row.status = 'stopped'
      row.startTime = null
      ElMessage.success('策略已停止')
    } catch (error) {
      ElMessage.error('停止失败：' + (error.response?.data?.detail || error.message))
    }
  }).catch(() => {})
}

// 回测
const backtest = async (row) => {
  showBacktest.value = true
  
  try {
    const result = await runBacktest(row.id, {
      start_date: '2025-01-01',
      end_date: new Date().toISOString().split('T')[0],
      initial_capital: 500000
    })
    
    backtestResult.value = {
      strategyName: row.name,
      totalReturn: result.total_return,
      annualReturn: result.annual_return,
      sharpe: result.sharpe_ratio,
      maxDrawdown: result.max_drawdown
    }
    
    ElMessage.success('回测完成')
  } catch (error) {
    ElMessage.error('回测失败：' + (error.response?.data?.detail || error.message))
  }
}

// 删除策略
const deleteStrategy = (row) => {
  ElMessageBox.confirm(
    `确认删除策略「${row.name}」吗？`,
    '删除确认',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'danger'
    }
  ).then(() => {
    const index = strategies.value.findIndex(s => s.id === row.id)
    if (index > -1) {
      strategies.value.splice(index, 1)
    }
    if (selectedStrategy.value && selectedStrategy.value.id === row.id) {
      selectedStrategy.value = null
    }
    ElMessage.success('策略已删除')
  }).catch(() => {})
}

// 选择策略
const handleRowClick = (row) => {
  selectedStrategy.value = row
}

onMounted(() => {
  loadStrategies()
})
</script>

<style scoped>
.strategy-page {
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
