<template>
  <div class="news-container">
    <!-- 页面头部 -->
    <el-card class="header-card">
      <div class="header-content">
        <div>
          <h2>📰 政策新闻</h2>
          <p class="subtitle">实时采集国务院、新华网等官方政策信息</p>
        </div>
        <div class="stats">
          <el-statistic title="总新闻数" :value="stats.total" />
          <el-statistic title="今日新增" :value="stats.today_count" />
          <el-statistic title="分类数" :value="stats.by_category ? Object.keys(stats.by_category).length : 0" />
        </div>
      </div>
    </el-card>

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
            <el-option label="其他政策" value="其他政策" />
          </el-select>
        </el-form-item>
        <el-form-item label="来源">
          <el-select v-model="filterForm.source" placeholder="全部来源" clearable style="width: 150px">
            <el-option label="中国政府网" value="中国政府网" />
            <el-option label="新华网" value="新华网" />
            <el-option label="财联社" value="财联社" />
            <el-option label="华尔街见闻" value="华尔街见闻" />
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
          <span>新闻列表</span>
          <el-button :icon="Refresh" circle @click="loadNews" />
        </div>
      </template>

      <el-table :data="newsList" style="width: 100%" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column label="情绪" width="70">
          <template #default="{ row }">
            <el-tag :type="getSentimentType(row.sentiment)" size="small">
              {{ getSentimentEmoji(row.sentiment) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="300">
          <template #default="{ row }">
            <el-link type="primary" @click="viewDetail(row.id)" :underline="false">
              {{ row.title }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.category }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="source" label="来源" width="100" />
        <el-table-column prop="publish_date" label="日期" width="100" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="viewDetail(row.id)">详情</el-button>
          </template>
        </el-table-column>
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
        <el-descriptions-item label="影响领域">
          <el-tag v-for="domain in parseDomains(currentNews.domains)" :key="domain" size="small">
            {{ domain }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="内容" :span="2">
          <div class="news-content">{{ currentNews.content || '暂无详细内容' }}</div>
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

// 筛选表单
const filterForm = reactive({
  category: '',
  source: ''
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
  today_count: 0,
  by_category: {}
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
      source: filterForm.source || undefined,
      limit: pagination.pageSize,
      offset: (pagination.page - 1) * pagination.pageSize
    }
    
    const res = await getNewsList(params)
    newsList.value = res.data || []
    pagination.total = res.total || 0
  } catch (error) {
    console.error('加载新闻失败:', error)
    ElMessage.error('加载新闻失败，请检查 API 服务是否启动')
    // 模拟数据（开发测试用）
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
  filterForm.source = ''
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

// 情绪标签文字
function getSentimentLabel(sentiment) {
  if (sentiment > 0.1) return '利好'
  if (sentiment < -0.1) return '利空'
  return '中性'
}

// 解析领域
function parseDomains(domainsStr) {
  try {
    return domainsStr ? JSON.parse(domainsStr) : ['综合']
  } catch {
    return ['综合']
  }
}

// 模拟数据（API 未启动时使用）
function getMockNews() {
  return [
    {
      id: 1,
      title: '中共中央办公厅 国务院办公厅关于加快建立长期护理保险制度的意见',
      source: '中国政府网',
      category: '民生政策',
      publish_date: '2026-03-25',
      sentiment: 0.3,
      domains: '["民生","社保"]',
      content: '为积极应对人口老龄化，解决失能人员长期护理保障问题...'
    },
    {
      id: 2,
      title: '国务院关于修改《社会团体登记管理条例》的决定',
      source: '中国政府网',
      category: '国务院政策',
      publish_date: '2026-03-17',
      sentiment: 0,
      domains: '["综合"]',
      content: '对社会团体登记管理条例进行修订...'
    },
    {
      id: 3,
      title: '前 2 个月全国规模以上工业企业利润同比增长 15.2%',
      source: '新华网',
      category: '经济新闻',
      publish_date: '2026-03-17',
      sentiment: 0.5,
      domains: '["经济"]',
      content: '国家统计局数据显示，1-2 月份全国规模以上工业企业利润实现较快增长...'
    }
  ]
}

onMounted(() => {
  loadNews()
  loadStats()
})
</script>

<style scoped>
.news-container {
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

.news-content {
  line-height: 1.8;
  white-space: pre-wrap;
}
</style>
