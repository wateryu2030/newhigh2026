<template>
  <div class="kline-chart" ref="chartContainer" style="width: 100%; height: 500px;"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  symbol: {
    type: String,
    default: '600519'
  },
  period: {
    type: String,
    default: 'daily'
  }
})

const chartContainer = ref(null)
let chart = null

// 初始化图表
const initChart = () => {
  if (!chartContainer.value) return
  
  chart = echarts.init(chartContainer.value)
  
  const option = {
    title: {
      text: `${props.symbol} K 线图`,
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    grid: {
      left: '10%',
      right: '10%',
      top: '15%',
      bottom: '15%'
    },
    xAxis: {
      type: 'category',
      data: [],
      scale: true,
      boundaryGap: false,
      axisLine: {
        onZero: false
      }
    },
    yAxis: [
      {
        scale: true,
        splitArea: {
          show: true
        }
      },
      {
        scale: true,
        gridIndex: 1,
        height: '30%',
        splitNumber: 2,
        axisLabel: {
          show: false
        },
        axisLine: {
          show: false
        },
        axisTick: {
          show: false
        },
        splitLine: {
          show: false
        }
      }
    ],
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: [0, 1],
        start: 50,
        end: 100
      },
      {
        show: true,
        xAxisIndex: [0, 1],
        type: 'slider',
        bottom: '5%',
        start: 50,
        end: 100
      }
    ],
    series: [
      {
        name: 'K 线',
        type: 'candlestick',
        data: [],
        itemStyle: {
          color: '#dc2626',
          color0: '#16a34a',
          borderColor: '#dc2626',
          borderColor0: '#16a34a'
        }
      },
      {
        name: '成交量',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: [],
        itemStyle: {
          color: function(params) {
            const dataIndex = params.dataIndex;
            const klineData = seriesData[0].data[dataIndex];
            return klineData[1] > klineData[0] ? '#dc2626' : '#16a34a';
          }
        }
      }
    ]
  }
  
  chart.setOption(option)
}

// 加载数据
const seriesData = ref([{ data: [] }, { data: [] }])

const loadData = async () => {
  try {
    // TODO: 调用后端 API
    // const response = await fetch(`http://localhost:8000/api/stocks/${props.symbol}/history`)
    // const data = await response.json()
    
    // 模拟数据
    const mockData = generateMockData()
    
    const dates = mockData.map(item => item.date)
    const klineData = mockData.map(item => [item.open, item.close, item.low, item.high])
    const volumeData = mockData.map(item => item.volume)
    
    seriesData.value = [
      { data: klineData },
      { data: volumeData }
    ]
    
    chart.setOption({
      xAxis: { data: dates },
      series: [
        { data: klineData },
        { data: volumeData }
      ]
    })
  } catch (error) {
    console.error('加载 K 线数据失败:', error)
  }
}

// 生成模拟数据
const generateMockData = () => {
  const data = []
  let basePrice = 1680
  const startDate = new Date('2025-03-26')
  
  for (let i = 0; i < 60; i++) {
    const date = new Date(startDate)
    date.setDate(date.getDate() + i)
    
    const change = (Math.random() - 0.5) * 40
    const open = basePrice + change
    const close = open + (Math.random() - 0.5) * 30
    const high = Math.max(open, close) + Math.random() * 10
    const low = Math.min(open, close) - Math.random() * 10
    const volume = Math.floor(Math.random() * 1000000) + 500000
    
    data.push({
      date: date.toISOString().split('T')[0],
      open: open,
      close: close,
      high: high,
      low: low,
      volume: volume
    })
    
    basePrice = close
  }
  
  return data
}

// 监听属性变化
watch(() => props.symbol, () => {
  loadData()
})

watch(() => props.period, () => {
  loadData()
})

// 生命周期
onMounted(() => {
  initChart()
  loadData()
  
  // 响应式调整
  window.addEventListener('resize', () => {
    chart && chart.resize()
  })
})

onUnmounted(() => {
  chart && chart.dispose()
})

// 暴露方法
defineExpose({
  refresh: loadData
})
</script>

<style scoped>
.kline-chart {
  width: 100%;
  height: 500px;
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
</style>
