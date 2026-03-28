<template>
  <div class="app-container">
    <!-- 顶部导航栏 -->
    <header class="header">
      <div class="header-left">
        <div class="logo">
          <el-icon :size="24"><TrendCharts /></el-icon>
          <span>红山量化</span>
        </div>
        <el-menu mode="horizontal" :ellipsis="false" class="nav-menu">
          <el-menu-item index="1" @click="activeTab = 'market'">行情</el-menu-item>
          <el-menu-item index="2" @click="activeTab = 'trade'">交易</el-menu-item>
          <el-menu-item index="3" @click="activeTab = 'position'">持仓</el-menu-item>
          <el-menu-item index="4" @click="activeTab = 'strategy'">策略</el-menu-item>
          <el-menu-item index="5" @click="activeTab = 'risk'">风控</el-menu-item>
          <el-menu-item index="6" @click="activeTab = 'finance'">💰 金融</el-menu-item>
          <el-menu-item index="7" @click="activeTab = 'collector'">📰 采集新闻</el-menu-item>
        </el-menu>
      </div>
      <div class="header-right">
        <el-button :icon="Bell" circle />
        <el-avatar :size="32" icon="UserFilled" />
      </div>
    </header>

    <!-- 主内容区 -->
    <div class="main-container">
      <!-- 左侧边栏 -->
      <aside class="sidebar">
        <div class="sidebar-section">
          <div class="section-title">自选列表</div>
          <el-table :data="watchlist" style="width: 100%" size="small" :show-header="false">
            <el-table-column prop="symbol" label="代码" width="70" />
            <el-table-column prop="name" label="名称" />
            <el-table-column prop="price" label="价格" width="70" align="right">
              <template #default="{ row }">
                <span :class="row.change >= 0 ? 'text-up' : 'text-down'">{{ row.price }}</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </aside>

      <!-- 右侧主内容 -->
      <main class="content">
        <!-- 行情页面 -->
        <div v-if="activeTab === 'market'">
          <el-card style="margin-bottom: 20px;">
            <template #header>
              <h2>行情中心</h2>
            </template>
            <p>实时股票行情，支持搜索和筛选。</p>
          </el-card>

          <!-- K 线图表 -->
          <el-card style="margin-bottom: 20px;">
            <template #header>
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <h3>K 线图表 - 贵州茅台 (600519)</h3>
                <el-radio-group v-model="klinePeriod" size="small">
                  <el-radio-button label="daily">日 K</el-radio-button>
                  <el-radio-button label="weekly">周 K</el-radio-button>
                  <el-radio-button label="monthly">月 K</el-radio-button>
                </el-radio-group>
              </div>
            </template>
            <KlineChart :symbol="'600519'" :period="klinePeriod" />
          </el-card>
        </div>

        <!-- 金融新闻页面 -->
        <div v-else-if="activeTab === 'finance'">
          <FinanceNewsView />
        </div>

        <!-- 政策采集入库（SQLite / 8001，与 Awesome Finance Skills 无硬依赖） -->
        <div v-else-if="activeTab === 'collector'">
          <CollectedNewsView />
        </div>

        <!-- 其他页面占位 -->
        <el-card v-else>
          <template #header>
            <h2>{{ getPageTitle() }}</h2>
          </template>
          <p>功能开发中...</p>
        </el-card>
      </main>
    </div>

    <!-- 底部状态栏 -->
    <footer class="footer">
      <span>总资产：¥500,000</span>
      <span>今日盈亏：+¥12,345 (+1.2%)</span>
    </footer>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { TrendCharts, Bell, UserFilled } from '@element-plus/icons-vue'
import KlineChart from './components/KlineChart.vue'
import FinanceNewsView from './views/FinanceNews.vue'
import CollectedNewsView from './views/News.vue'

const activeTab = ref('market')
const klinePeriod = ref('daily')

const watchlist = ref([
  { symbol: '600519', name: '贵州茅台', price: 1410.27, change: 2.35 },
  { symbol: '000858', name: '五粮液', price: 156.80, change: -1.20 },
  { symbol: '000568', name: '泸州老窖', price: 189.50, change: 0.85 }
])

const getPageTitle = () => {
  const titles = {
    market: '行情中心',
    trade: '交易',
    position: '持仓',
    strategy: '策略',
    risk: '风控',
    finance: '金融新闻',
    collector: '采集新闻'
  }
  return titles[activeTab.value] || '功能开发中'
}
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #F9FAFB; }
.app-container { display: flex; flex-direction: column; height: 100vh; }
.header { display: flex; justify-content: space-between; padding: 0 20px; height: 60px; background: white; border-bottom: 1px solid #E5E7EB; align-items: center; }
.header-left { display: flex; align-items: center; gap: 20px; }
.logo { display: flex; align-items: center; gap: 8px; font-size: 18px; font-weight: 600; color: #1E40AF; }
.nav-menu { border: none !important; }
.main-container { display: flex; flex: 1; overflow: hidden; }
.sidebar { width: 280px; background: white; border-right: 1px solid #E5E7EB; padding: 15px; }
.section-title { font-size: 14px; font-weight: 600; color: #6B7280; margin-bottom: 10px; }
.content { flex: 1; padding: 20px; overflow-y: auto; }
.footer { display: flex; justify-content: space-between; padding: 10px 20px; background: white; border-top: 1px solid #E5E7EB; font-size: 13px; }
.text-up { color: #DC2626; }
.text-down { color: #16A34A; }
</style>
