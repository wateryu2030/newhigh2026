import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  // 本地开发与 newhigh 并存：Hongshan API 默认 host 8010（见 integrations/hongshan/docker-compose.yml）
  server: {
    port: 5174,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8010', changeOrigin: true },
      '/ws': { target: 'ws://127.0.0.1:8010', ws: true },
    },
  },
})
