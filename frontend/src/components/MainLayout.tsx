import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import { LineChartOutlined, ExperimentOutlined, RadarChartOutlined, RobotOutlined } from '@ant-design/icons';

const { Header, Content } = Layout;

const items = [
  { key: '/trading', icon: <LineChartOutlined />, label: '交易决策中心（含新闻热点）' },
  { key: '/institutional', icon: <LineChartOutlined />, label: '机构交易' },
  { key: '/strategy-lab', icon: <ExperimentOutlined />, label: '策略实验室' },
  { key: '/scanner', icon: <RadarChartOutlined />, label: '市场扫描器' },
  { key: '/rl', icon: <RobotOutlined />, label: 'RL 交易' },
];

export default function MainLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const selected = items.some((i) => i.key === location.pathname)
    ? location.pathname
    : location.pathname.startsWith('/rl')
      ? '/rl'
      : location.pathname.startsWith('/institutional')
        ? '/institutional'
        : location.pathname;

  const onMenuSelect = ({ key }: { key: string }) => {
    navigate(key);
  };

  return (
    <Layout style={{ minHeight: '100vh', background: '#0f1419' }}>
      <Header style={{ display: 'flex', alignItems: 'center', background: '#1a2332', padding: '0 24px', borderBottom: '1px solid #2d3a4f' }}>
        <div style={{ color: '#22c55e', fontWeight: 700, fontSize: 18, marginRight: 32 }}>红山量化</div>
        <Menu
          theme="dark"
          mode="horizontal"
          selectedKeys={[selected]}
          items={items}
          onSelect={onMenuSelect}
          style={{ flex: 1, background: 'transparent', borderBottom: 'none', color: '#f1f5f9' }}
        />
      </Header>
      <Content style={{ padding: 16, overflow: 'auto', background: '#0f1419' }}>
        <Outlet />
      </Content>
    </Layout>
  );
}
