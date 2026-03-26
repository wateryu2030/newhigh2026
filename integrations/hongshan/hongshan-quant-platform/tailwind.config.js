/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#1E40AF',      // 深邃蓝 - 主色
        success: '#16A34A',       // 翡翠绿 - 跌
        danger: '#DC2626',        // 中国红 - 涨
        warning: '#F59E0B',       // 琥珀橙 - 警告
        dark: '#111827',          // 深灰 - 主文字
        secondary: '#6B7280',     // 中灰 - 次要文字
        bg: '#F9FAFB',            // 浅灰 - 次要背景
      }
    },
  },
  plugins: [],
}
