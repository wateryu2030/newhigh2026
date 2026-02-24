import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './components/MainLayout';
import TradingDecision from './pages/TradingDecision';
import StrategyLab from './pages/StrategyLab';
import MarketScanner from './pages/MarketScanner';
import RLTrainingDashboard from './pages/RLTrainingDashboard';
import RLPerformance from './pages/RLPerformance';
import RLDecisionView from './pages/RLDecisionView';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Navigate to="/trading" replace />} />
          <Route path="trading" element={<TradingDecision />} />
          <Route path="strategy-lab" element={<StrategyLab />} />
          <Route path="scanner" element={<MarketScanner />} />
          <Route path="rl" element={<RLTrainingDashboard />} />
          <Route path="rl/performance" element={<RLPerformance />} />
          <Route path="rl/decision" element={<RLDecisionView />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
