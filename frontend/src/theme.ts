import type { ThemeConfig } from 'antd';

export const theme: ThemeConfig = {
  token: {
    colorBgBase: '#0f1419',
    colorBgContainer: '#1a2332',
    colorBorder: '#2d3a4f',
    colorText: '#f1f5f9',
    colorTextSecondary: '#b8c5d6',
    colorPrimary: '#22c55e',
    colorError: '#f87171',
    colorSuccess: '#22c55e',
    colorWarning: '#fbbf24',
    borderRadius: 6,
  },
  components: {
    Layout: { bodyBg: '#0f1419', headerBg: '#1a2332', siderBg: '#1a2332' },
    Menu: { darkItemBg: '#1a2332', darkSubMenuItemBg: '#151d2e', darkItemSelectedBg: '#22c55e22', darkItemSelectedColor: '#22c55e' },
    Table: {
      colorBgContainer: '#1a2332',
      colorBorderSecondary: '#2d3a4f',
      colorText: '#f1f5f9',
      colorIcon: '#94a3b8',
      colorIconHover: '#22c55e',
    },
    Alert: {
      colorInfoBg: '#1e293b',
      colorInfoBorder: '#334155',
      colorInfoText: '#e2e8f0',
      colorTextDescription: '#cbd5e1',
    },
    Card: { colorBgContainer: '#1a2332', colorBorderSecondary: '#2d3a4f' },
    Input: { colorBgContainer: '#1e293b', colorText: '#f1f5f9' },
    Select: { colorBgContainer: '#1e293b', colorText: '#f1f5f9' },
    Button: { colorPrimary: '#22c55e', colorPrimaryHover: '#16a34a', colorText: '#f1f5f9' },
    Tabs: { itemColor: '#94a3b8', itemSelectedColor: '#22c55e', itemHoverColor: '#cbd5e1', inkBarColor: '#22c55e' },
    Drawer: { colorBgElevated: '#1a2332', colorText: '#f1f5f9', colorBorderSecondary: '#2d3a4f' },
  },
};
