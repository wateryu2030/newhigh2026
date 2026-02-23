import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import { LineChartOutlined, ExperimentOutlined, RadarChartOutlined } from '@ant-design/icons';

const { Header, Content } = Layout;

const items = [
  { key: '/trading', icon: <LineChartOutlined />, label: '交易决策中心' },
  { key: '/strategy-lab', icon: <ExperimentOutlined />, label: '策略实验室' },
  { key: '/scanner', icon: <RadarChartOutlined />, label: '市场扫描器' },
];

export default function MainLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [selected, setSelected] = useState(location.pathname);

  const onMenuSelect = ({ key }: { key: string }) => {
    setSelected(key);
    navigate(key);
  };

  return (
    <Layout style={{ minHeight: '100vh', background: '#0b0f17' }}>
      <Header style={{ display: 'flex', alignItems: 'center', background: '#111827', padding: '0 24px' }}>
        <div style={{ color: '#10b981', fontWeight: 700, fontSize: 18, marginRight: 32 }}>红山量化</div>
        <Menu
          theme="dark"
          mode="horizontal"
          selectedKeys={[selected]}
          items={items}
          onSelect={onMenuSelect}
          style={{ flex: 1, background: 'transparent', borderBottom: 'none' }}
        />
      </Header>
      <Content style={{ padding: 16, overflow: 'auto' }}>
        <Outlet />
      </Content>
    </Layout>
  );
}
