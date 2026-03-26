<template>
  <div class="risk-page">
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
        <!-- 风险概览 -->
        <el-row :gutter="20" style="margin-bottom: 20px;">
          <el-col :span="6">
            <el-card>
              <div class="risk-card">
                <div class="risk-label">整体风险等级</div>
                <div class="risk-level" :class="riskLevelClass">
                  {{ riskLevel }}
                </div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card>
              <div class="risk-card">
                <div class="risk-label">VaR (95%)</div>
                <div class="risk-value">¥{{ var95.toLocaleString() }}</div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card>
              <div class="risk-card">
                <div class="risk-label">最大回撤</div>
                <div class="risk-value text-down">{{ maxDrawdown }}%</div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card>
              <div class="risk-card">
                <div class="risk-label">预警数量</div>
                <div class="risk-value text-up">{{ alertCount }}</div>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <!-- 左侧：风险指标 -->
          <el-col :span="12">
            <!-- 风险指标监控 -->
            <el-card style="margin-bottom: 20px;">
              <template #header>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <h3>风险指标监控</h3>
                  <el-button type="primary" size="small" @click="refreshRiskData">刷新</el-button>
                </div>
              </template>
              
              <el-table :data="riskMetrics" style="width: 100%" size="small">
                <el-table-column prop="name" label="指标" width="150" />
                <el-table-column prop="current" label="当前值" width="120">
                  <template #default="{ row }">
                    <span :class="getRiskValueClass(row.current, row.warning, row.critical)">
                      {{ row.current }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="warning" label="预警线" width="100" />
                <el-table-column prop="critical" label="警戒线" width="100" />
                <el-table-column prop="status" label="状态" width="80">
                  <template #default="{ row }">
                    <el-tag :type="getStatusType(row.status)" size="small">
                      {{ row.status }}
                    </el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
            
            <!-- 持仓集中度 -->
            <el-card>
              <template #header>
                <h3>持仓集中度分析</h3>
              </template>
              
              <el-progress 
                :percentage="positionConcentration.stock" 
                status="warning"
                format="text"
              >
                <template #default="{ percentage }">
                  <span>股票仓位：{{ percentage }}%</span>
                </template>
              </el-progress>
              
              <el-progress 
                :percentage="positionConcentration.industry" 
                status="info"
                format="text"
                style="margin-top: 15px;"
              >
                <template #default="{ percentage }">
                  <span>行业集中度：{{ percentage }}%</span>
                </template>
              </el-progress>
              
              <el-progress 
                :percentage="positionConcentration.single" 
                status="success"
                format="text"
                style="margin-top: 15px;"
              >
                <template #default="{ percentage }">
                  <span>个股集中度：{{ percentage }}%</span>
                </template>
              </el-progress>
            </el-card>
          </el-col>
          
          <!-- 右侧：预警和日志 -->
          <el-col :span="12">
            <!-- 风险预警 -->
            <el-card style="margin-bottom: 20px;">
              <template #header>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <h3>风险预警</h3>
                  <el-button type="primary" size="small" @click="showAlertSettings">设置</el-button>
                </div>
              </template>
              
              <el-timeline>
                <el-timeline-item 
                  v-for="alert in alerts" 
                  :key="alert.id"
                  :timestamp="alert.time"
                  placement="top"
                  :type="alert.type"
                >
                  <el-card>
                    <p><strong>{{ alert.title }}</strong></p>
                    <p>{{ alert.message }}</p>
                    <p v-if="alert.suggestion" style="color: #6b7280; font-size: 13px;">
                      建议：{{ alert.suggestion }}
                    </p>
                  </el-card>
                </el-timeline-item>
              </el-timeline>
              
              <el-empty v-if="alerts.length === 0" description="暂无风险预警" />
            </el-card>
            
            <!-- 风控日志 -->
            <el-card>
              <template #header>
                <h3>风控日志</h3>
              </template>
              
              <el-table :data="riskLogs" style="width: 100%" size="small" max-height="300">
                <el-table-column prop="time" label="时间" width="160" />
                <el-table-column prop="type" label="类型" width="80">
                  <template #default="{ row }">
                    <el-tag :type="row.type === 'warning' ? 'warning' : 'danger'" size="small">
                      {{ row.type === 'warning' ? '预警' : '触发' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="message" label="内容" />
              </el-table>
            </el-card>
          </el-col>
        </el-row>
      </el-main>
    </el-container>
    
    <!-- 预警设置对话框 -->
    <el-dialog v-model="alertDialogVisible" title="风险预警设置" width="600px">
      <el-form :model="alertSettings" label-width="120px">
        <el-form-item label="最大回撤预警">
          <el-input-number v-model="alertSettings.maxDrawdownWarning" :min="1" :max="50" /> %
        </el-form-item>
        <el-form-item label="最大回撤警戒">
          <el-input-number v-model="alertSettings.maxDrawdownCritical" :min="1" :max="50" /> %
        </el-form-item>
        <el-form-item label="单日亏损预警">
          <el-input-number v-model="alertSettings.dailyLossWarning" :min="1" :max="20" /> %
        </el-form-item>
        <el-form-item label="个股集中度上限">
          <el-input-number v-model="alertSettings.singleStockLimit" :min="10" :max="100" /> %
        </el-form-item>
        <el-form-item label="行业集中度上限">
          <el-input-number v-model="alertSettings.industryLimit" :min="20" :max="100" /> %
        </el-form-item>
        <el-form-item label="总仓位上限">
          <el-input-number v-model="alertSettings.totalPositionLimit" :min="50" :max="100" /> %
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="alertDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveAlertSettings">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { getRiskConfig, updateRiskConfig as apiUpdateRiskConfig, getRiskAlerts, handleAlert as apiHandleAlert, getRiskMetrics } from '../api/risk'

const router = useRouter()

const alertDialogVisible = ref(false)

// 风险等级
const riskLevel = ref('低风险')
const riskLevelClass = computed(() => {
  const map = {
    '低风险': 'risk-low',
    '中风险': 'risk-medium',
    '高风险': 'risk-high'
  }
  return map[riskLevel.value] || 'risk-low'
})

// 风险指标
const var95 = ref(28500)
const maxDrawdown = ref(-8.3)
const alertCount = ref(2)

// 风险指标监控
const riskMetrics = ref([
  { name: '组合 VaR(95%)', current: '28,500', warning: '30,000', critical: '50,000', status: '正常' },
  { name: '最大回撤', current: '-8.3%', warning: '-10%', critical: '-15%', status: '正常' },
  { name: '日波动率', current: '1.2%', warning: '2%', critical: '3%', status: '正常' },
  { name: 'Beta 系数', current: '0.85', warning: '1.2', critical: '1.5', status: '正常' },
  { name: '夏普比率', current: '1.85', warning: '1.0', critical: '0.5', status: '正常' },
  { name: '流动性比率', current: '0.65', warning: '0.5', critical: '0.3', status: '正常' }
])

// 持仓集中度
const positionConcentration = ref({
  stock: 65,
  industry: 45,
  single: 33
})

// 风险预警
const alerts = ref([
  {
    id: 1,
    time: '2026-03-26 10:30:00',
    type: 'warning',
    title: '个股集中度预警',
    message: '贵州茅台持仓占比达到 33%，接近设定的 35% 上限',
    suggestion: '考虑适当减仓或分散投资'
  },
  {
    id: 2,
    time: '2026-03-26 09:45:00',
    type: 'warning',
    title: '行业集中度提示',
    message: '白酒行业持仓占比达到 45%',
    suggestion: '关注行业政策风险'
  }
])

// 风控日志
const riskLogs = ref([
  { time: '2026-03-26 10:30:15', type: 'warning', message: '个股集中度接近阈值' },
  { time: '2026-03-26 09:45:20', type: 'warning', message: '行业集中度监控提示' },
  { time: '2026-03-25 15:00:00', type: 'trigger', message: '日终风险检查完成' },
  { time: '2026-03-25 10:15:30', type: 'warning', message: '组合 VaR 接近预警线' }
])

// 预警设置
const alertSettings = ref({
  maxDrawdownWarning: 10,
  maxDrawdownCritical: 15,
  dailyLossWarning: 5,
  singleStockLimit: 35,
  industryLimit: 50,
  totalPositionLimit: 80
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

// 获取风险值样式类
const getRiskValueClass = (current, warning, critical) => {
  if (current.includes('%')) {
    const curr = parseFloat(current)
    const warn = parseFloat(warning)
    if (curr < warn) return 'text-down'
  }
  return ''
}

// 获取状态类型
const getStatusType = (status) => {
  const map = {
    '正常': 'success',
    '预警': 'warning',
    '触发': 'danger'
  }
  return map[status] || 'info'
}

// 刷新风险数据
const refreshRiskData = async () => {
  try {
    const [metrics, config, alerts] = await Promise.all([
      getRiskMetrics(),
      getRiskConfig(),
      getRiskAlerts({ status: 'unread', limit: 10 })
    ])
    
    riskLevel.value = metrics.max_drawdown < -10 ? '高风险' : metrics.max_drawdown < -5 ? '中风险' : '低风险'
    var95.value = metrics.var_95 || 0
    maxDrawdown.value = metrics.max_drawdown || 0
    alertCount.value = metrics.alert_count || 0
    
    positionConcentration.value = {
      stock: metrics.position_ratio || 0,
      industry: metrics.industry_concentration || 0,
      single: metrics.single_stock_concentration || 0
    }
    
    alertSettings.value = {
      maxDrawdownWarning: config.max_drawdown_warning * 100,
      maxDrawdownCritical: config.max_drawdown_critical * 100,
      dailyLossWarning: config.daily_loss_limit * 100,
      singleStockLimit: config.single_stock_limit * 100,
      industryLimit: config.industry_limit * 100,
      totalPositionLimit: config.max_position_ratio * 100
    }
    
    alerts.value = alerts.map(a => ({
      id: a.id,
      time: a.alert_time,
      type: a.alert_level,
      title: a.title,
      message: a.message,
      suggestion: a.suggestion
    }))
    
    ElMessage.success('风险数据已刷新')
  } catch (error) {
    ElMessage.error('刷新失败：' + (error.response?.data?.detail || error.message))
  }
}

// 显示预警设置
const showAlertSettings = () => {
  alertDialogVisible.value = true
}

// 保存预警设置
const saveAlertSettings = async () => {
  try {
    await apiUpdateRiskConfig({
      max_drawdown_warning: alertSettings.value.maxDrawdownWarning / 100,
      max_drawdown_critical: alertSettings.value.maxDrawdownCritical / 100,
      daily_loss_limit: alertSettings.value.dailyLossWarning / 100,
      single_stock_limit: alertSettings.value.singleStockLimit / 100,
      industry_limit: alertSettings.value.industryLimit / 100,
      max_position_ratio: alertSettings.value.totalPositionLimit / 100
    })
    
    ElMessage.success('预警设置已保存')
    alertDialogVisible.value = false
    refreshRiskData()
  } catch (error) {
    ElMessage.error('保存失败：' + (error.response?.data?.detail || error.message))
  }
}

// 处理预警
const handleAlert = async (alert) => {
  try {
    await apiHandleAlert(alert.id)
    alert.status = 'handled'
    ElMessage.success('预警已处理')
  } catch (error) {
    ElMessage.error('处理失败')
  }
}

onMounted(() => {
  refreshRiskData()
})
</script>

<style scoped>
.risk-page {
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

.risk-card {
  text-align: center;
}

.risk-label {
  font-size: 14px;
  color: #6b7280;
  margin-bottom: 8px;
}

.risk-level {
  font-size: 28px;
  font-weight: bold;
}

.risk-low {
  color: #16a34a;
}

.risk-medium {
  color: #f59e0b;
}

.risk-high {
  color: #dc2626;
}

.risk-value {
  font-size: 24px;
  font-weight: bold;
  color: #1e40af;
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
