import type { ThemeConfig } from 'antd';

export const theme: ThemeConfig = {
  token: {
    colorBgBase: '#0b0f17',
    colorBgContainer: '#111827',
    colorBorder: '#1f2937',
    colorText: '#e0e6ed',
    colorTextSecondary: '#9ca3af',
    colorPrimary: '#10b981',
    colorError: '#ef4444',
    borderRadius: 6,
  },
  components: {
    Layout: { bodyBg: '#0b0f17', headerBg: '#111827', siderBg: '#111827' },
    Menu: { darkItemBg: '#111827', darkSubMenuItemBg: '#0f172a' },
    Table: { colorBgContainer: '#111827' },
    Card: { colorBgContainer: '#111827' },
    Input: { colorBgContainer: '#1f2937' },
    Select: { colorBgContainer: '#1f2937' },
  },
};
