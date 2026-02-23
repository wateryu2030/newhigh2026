import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './components/MainLayout';
import TradingDecision from './pages/TradingDecision';
import StrategyLab from './pages/StrategyLab';
import MarketScanner from './pages/MarketScanner';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Navigate to="/trading" replace />} />
          <Route path="trading" element={<TradingDecision />} />
          <Route path="strategy-lab" element={<StrategyLab />} />
          <Route path="scanner" element={<MarketScanner />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
