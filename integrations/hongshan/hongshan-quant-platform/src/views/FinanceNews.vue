<template>
  <div class="finance-news-container">
    <!-- 页面头部 -->
    <el-card class="header-card">
      <div class="header-content">
        <div>
          <h2>💰 金融新闻</h2>
          <p class="subtitle">实时财经资讯 + 政策情报</p>
        </div>
        <div class="stats">
          <el-statistic title="总新闻数" :value="stats.total" />
          <el-statistic title="今日新增" :value="stats.today_count" />
        </div>
      </div>
    </el-card>

    <!-- Awesome Finance Skills 提示 -->
    <el-alert
      title="Awesome Finance Skills 集成中"
      type="info"
      :closable="false"
      show-icon
      class="mb-4"
    >
      <template #default>
        <p>正在集成 <strong>Awesome Finance Skills</strong>，完成后将提供：</p>
        <el-tag v-for="feature in features" :key="feature" size="small" class="mr-2 mt-2">
          {{ feature }}
        </el-tag>
        <p class="mt-2 text-sm text-gray-500">
          当前可使用 <strong>政策新闻</strong> 功能，数据已实时采集并更新。
        </p>
      </template>
    </el-alert>

    <!-- 筛选栏 -->
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm" class="filter-form">
        <el-form-item label="分类">
          <el-select v-model="filterForm.category" placeholder="全部分类" clearable style="width: 150px">
            <el-option label="国务院政策" value="国务院政策" />
            <el-option label="金融政策" value="金融政策" />
            <el-option label="经济新闻" value="经济新闻" />
            <el-option label="住建政策" value="住建政策" />
            <el-option label="科技政策" value="科技政策" />
            <el-option label="农业政策" value="农业政策" />
            <el-option label="民生政策" value="民生政策" />
          </el-select>
        </el-form-item>
        <el-form-item label="情绪">
          <el-select v-model="filterForm.sentiment" placeholder="全部" clearable style="width: 100px">
            <el-option label="📈 利好" value="positive" />
            <el-option label="📉 利空" value="negative" />
            <el-option label="➡️ 中性" value="neutral" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadNews">查询</el-button>
          <el-button @click="resetFilter">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 新闻列表 -->
    <el-card class="news-list-card">
      <template #header>
        <div class="card-header">
          <span>实时新闻</span>
          <el-button :icon="Refresh" circle @click="loadNews" />
        </div>
      </template>

      <el-table :data="newsList" style="width: 100%" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column label="情绪" width="80">
          <template #default="{ row }">
            <el-tooltip :content="getSentimentTooltip(row.sentiment)" placement="top">
              <el-tag :type="getSentimentType(row.sentiment)" size="small">
                {{ getSentimentEmoji(row.sentiment) }}
              </el-tag>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="350">
          <template #default="{ row }">
            <el-link type="primary" @click="viewDetail(row.id)" :underline="false">
              {{ row.title }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="getCategoryTagType(row.category)">
              {{ row.category }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="source" label="来源" width="100" />
        <el-table-column prop="publish_date" label="日期" width="100" />
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next"
          @size-change="loadNews"
          @current-change="loadNews"
        />
      </div>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailVisible" title="新闻详情" width="60%">
      <el-descriptions :column="2" border v-if="currentNews">
        <el-descriptions-item label="标题">{{ currentNews.title }}</el-descriptions-item>
        <el-descriptions-item label="分类">
          <el-tag>{{ currentNews.category }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="来源">{{ currentNews.source }}</el-descriptions-item>
        <el-descriptions-item label="日期">{{ currentNews.publish_date }}</el-descriptions-item>
        <el-descriptions-item label="情绪">
          <el-tag :type="getSentimentType(currentNews.sentiment)">
            {{ getSentimentLabel(currentNews.sentiment) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="影响领域" :span="2">
          <el-tag v-for="domain in parseDomains(currentNews.domains)" :key="domain" size="small">
            {{ domain }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getNewsList, getNewsDetail, getStats } from '../api/news'

// Awesome Finance Skills 功能列表
const features = [
  '实时新闻聚合',
  'A 股/港股数据',
  '情绪分析',
  '时序预测',
  '逻辑链路可视化',
  '投资信号追踪',
  '研报生成',
  '搜索与 RAG'
]

// 筛选表单
const filterForm = reactive({
  category: '',
  sentiment: ''
})

// 新闻列表
const newsList = ref([])
const loading = ref(false)

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 50,
  total: 0
})

// 统计信息
const stats = ref({
  total: 0,
  today_count: 0
})

// 详情对话框
const detailVisible = ref(false)
const currentNews = ref(null)

// 加载新闻列表
async function loadNews() {
  loading.value = true
  try {
    const params = {
      category: filterForm.category || undefined,
      limit: pagination.pageSize,
      offset: (pagination.page - 1) * pagination.pageSize
    }
    
    const res = await getNewsList(params)
    newsList.value = res.data || []
    pagination.total = res.total || 0
  } catch (error) {
    console.error('加载新闻失败:', error)
    ElMessage.error('加载新闻失败，请检查 API 服务是否启动')
    // 模拟数据
    newsList.value = getMockNews()
  } finally {
    loading.value = false
  }
}

// 加载统计
async function loadStats() {
  try {
    const res = await getStats()
    stats.value = res.data || {}
  } catch (error) {
    console.error('加载统计失败:', error)
  }
}

// 查看详情
async function viewDetail(id) {
  try {
    const res = await getNewsDetail(id)
    currentNews.value = res.data
    detailVisible.value = true
  } catch (error) {
    console.error('加载详情失败:', error)
    ElMessage.error('加载详情失败')
  }
}

// 重置筛选
function resetFilter() {
  filterForm.category = ''
  filterForm.sentiment = ''
  pagination.page = 1
  loadNews()
}

// 情绪标签类型
function getSentimentType(sentiment) {
  if (sentiment > 0.1) return 'success'
  if (sentiment < -0.1) return 'danger'
  return 'info'
}

// 情绪表情
function getSentimentEmoji(sentiment) {
  if (sentiment > 0.1) return '📈'
  if (sentiment < -0.1) return '📉'
  return '➡️'
}

// 情绪提示
function getSentimentTooltip(sentiment) {
  if (sentiment > 0.1) return '利好'
  if (sentiment < -0.1) return '利空'
  return '中性'
}

// 情绪标签文字
function getSentimentLabel(sentiment) {
  if (sentiment > 0.1) return '利好'
  if (sentiment < -0.1) return '利空'
  return '中性'
}

// 分类标签类型
function getCategoryTagType(category) {
  const types = {
    '国务院政策': 'warning',
    '金融政策': 'success',
    '经济新闻': 'primary',
    '住建政策': 'info',
    '科技政策': 'success',
    '农业政策': 'success',
    '民生政策': 'warning'
  }
  return types[category] || ''
}

// 解析领域
function parseDomains(domainsStr) {
  try {
    return domainsStr ? JSON.parse(domainsStr) : ['综合']
  } catch {
    return ['综合']
  }
}

// 模拟数据
function getMockNews() {
  return [
    {
      id: 1,
      title: '中共中央办公厅 国务院办公厅关于加快建立长期护理保险制度的意见',
      source: '中国政府网',
      category: '民生政策',
      publish_date: '2026-03-25',
      sentiment: 0.3,
      domains: '["民生","社保"]'
    },
    {
      id: 2,
      title: '前 2 个月全国规模以上工业企业利润同比增长 15.2%',
      source: '新华网',
      category: '经济新闻',
      publish_date: '2026-03-17',
      sentiment: 0.5,
      domains: '["经济"]'
    }
  ]
}

onMounted(() => {
  loadNews()
  loadStats()
})
</script>

<style scoped>
.finance-news-container {
  padding: 20px;
}

.header-card {
  margin-bottom: 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-content h2 {
  margin: 0 0 8px 0;
  font-size: 24px;
}

.subtitle {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.stats {
  display: flex;
  gap: 40px;
}

.filter-card {
  margin-bottom: 20px;
}

.filter-form {
  margin-bottom: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.mb-4 {
  margin-bottom: 16px;
}

.mr-2 {
  margin-right: 8px;
}

.mt-2 {
  margin-top: 8px;
}

.text-sm {
  font-size: 13px;
}

.text-gray-500 {
  color: #6b7280;
}
</style>
