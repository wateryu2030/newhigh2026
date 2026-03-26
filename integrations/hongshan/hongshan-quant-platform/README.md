# 红山量化平台 - Vue 3 前端项目

**创建时间**: 2026-03-26  
**技术栈**: Vue 3 + Element Plus + ECharts + Tailwind CSS

---

## 🚀 快速开始

### 安装依赖
```bash
cd hongshan-quant-platform
npm install
```

### 启动开发服务器
```bash
npm run dev
```

访问 http://localhost:5173 查看应用

### 构建生产版本
```bash
npm run build
```

---

## 📦 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue | 3.x | 前端框架 |
| Element Plus | latest | UI 组件库 |
| ECharts | latest | 图表库 |
| Tailwind CSS | latest | CSS 框架 |
| Vite | latest | 构建工具 |

---

## 📁 项目结构

```
hongshan-quant-platform/
├── src/
│   ├── App.vue          # 主应用组件
│   ├── main.js          # 入口文件
│   ├── assets/          # 静态资源
│   ├── components/      # 公共组件
│   ├── views/           # 页面组件
│   └── styles/          # 全局样式
├── public/              # 公共资源
├── package.json         # 项目配置
├── vite.config.js       # Vite 配置
├── tailwind.config.js   # Tailwind 配置
└── README.md            # 项目说明
```

---

## 🎨 设计规范

### 色彩方案
| 用途 | 颜色 | 色值 |
|------|------|------|
| 主色 | 深邃蓝 | `#1E40AF` |
| 涨 | 中国红 | `#DC2626` |
| 跌 | 翡翠绿 | `#16A34A` |
| 警告 | 琥珀橙 | `#F59E0B` |
| 背景 | 浅灰 | `#F9FAFB` |

### 字体规范
- 页面标题：24px Bold
- 模块标题：18px SemiBold
- 正文：14px Regular
- 辅助文字：12px Regular

---

## 📄 页面规划

| 页面 | 路由 | 状态 |
|------|------|------|
| 行情 | `/market` | ✅ 框架完成 |
| 交易 | `/trade` | ⏳ 待开发 |
| 持仓 | `/position` | ⏳ 待开发 |
| 策略 | `/strategy` | ⏳ 待开发 |
| 风控 | `/risk` | ⏳ 待开发 |

---

## 🔧 开发指南

### 添加新组件
```bash
# 创建组件文件
src/components/YourComponent.vue
```

### 添加新页面
```bash
# 创建页面文件
src/views/YourPage.vue
```

### 使用 Element Plus 组件
```vue
<template>
  <el-button type="primary">按钮</el-button>
</template>
```

### 使用 ECharts 图表
```vue
<template>
  <div ref="chart" style="width: 100%; height: 400px;"></div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import * as echarts from 'echarts'

const chart = ref(null)

onMounted(() => {
  const myChart = echarts.init(chart.value)
  myChart.setOption({ /* 配置项 */ })
})
</script>
```

---

## 📝 下一步

1. ✅ 项目脚手架创建完成
2. ✅ Element Plus 集成完成
3. ✅ Tailwind CSS 配置完成
4. ⏳ 完善各页面组件
5. ⏳ 接入后端 API
6. ⏳ 添加实时数据推送

---

**创建者**: newhigh-01 🚀
