import { Card } from 'antd';
import type { Signal } from '../types';
import styles from './SignalMarkers.module.css';

interface SignalMarkersProps {
  signals: Signal[];
  symbol?: string;
}

export default function SignalMarkers({ signals, symbol }: SignalMarkersProps) {
  if (!signals?.length) {
    return (
      <Card size="small" title="买卖点" style={{ background: '#111827' }}>
        <div className={styles.empty}>暂无信号，选择股票并加载 K 线后显示</div>
      </Card>
    );
  }

  return (
    <Card size="small" title={`买卖点 ${symbol ? `· ${symbol}` : ''}`} style={{ background: '#111827' }}>
      <div className={styles.list}>
        {signals.slice(-20).reverse().map((s, i) => (
          <div
            key={i}
            className={s.type === 'BUY' ? styles.buy : styles.sell}
          >
            <span className={styles.type}>{s.type}</span>
            <span className={styles.date}>{s.date}</span>
            <span className={styles.price}>{s.price?.toFixed(2)}</span>
            {(s.stop_loss != null || s.target != null) && (
              <span className={styles.extra}>
                {s.stop_loss != null && `止损 ${s.stop_loss.toFixed(2)}`}
                {s.target != null && ` 目标 ${s.target.toFixed(2)}`}
              </span>
            )}
            {s.reason && <div className={styles.reason}>{s.reason}</div>}
          </div>
        ))}
      </div>
    </Card>
  );
}
