import React from 'react';
import ReactDOM from 'react-dom/client';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import App from './App';
import { theme } from './theme';
import './index.css';

// 开发环境下可忽略的第三方提示（非本项目错误）：
// - "Permissions policy violation: unload" 来自浏览器扩展 content.js
// - "@ali/tongyi-next-theme" 来自 antd 或扩展对可选主题的检测，本项目使用 theme.ts 自定义主题

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider locale={zhCN} theme={theme}>
      <App />
    </ConfigProvider>
  </React.StrictMode>
);
