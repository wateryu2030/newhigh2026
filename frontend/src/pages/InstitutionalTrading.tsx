/**
 * 机构级交易页：下单、持仓、资金、AI 决策面板。
 */
import { Layout, Row, Col } from 'antd';
import OrderPanel from '../trading/OrderPanel';
import PositionPanel from '../trading/PositionPanel';
import AccountPanel from '../trading/AccountPanel';
import AIDecisionPanel from '../ai/AIDecisionPanel';

const { Content } = Layout;

export default function InstitutionalTrading() {
  return (
    <Content style={{ padding: 16, background: '#0b0f17', minHeight: 'calc(100vh - 100px)' }}>
      <Row gutter={16}>
        <Col xs={24} md={12} lg={6}>
          <AccountPanel />
        </Col>
        <Col xs={24} md={12} lg={6}>
          <OrderPanel />
        </Col>
        <Col xs={24} md={12} lg={6}>
          <AIDecisionPanel />
        </Col>
      </Row>
      <Row style={{ marginTop: 16 }}>
        <Col span={24}>
          <PositionPanel />
        </Col>
      </Row>
    </Content>
  );
}
