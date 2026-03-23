interface StatCardProps {
  title: string;
  value: string | number;
  sub?: string;
  positive?: boolean;
}

export function StatCard({ title, value, sub, positive }: StatCardProps) {
  const valueColor = positive === true ? '#FF3B30' : positive === false ? '#FF7439' : '#ECEDF6';
  return (
    <div className="card">
      <p className="mb-1 text-xs font-medium uppercase tracking-wider" style={{ color: '#A9ABB3', fontFamily: 'Space Grotesk' }}>
        {title}
      </p>
      <p className="mt-1 text-2xl font-bold sm:text-3xl" style={{ color: valueColor, fontFamily: 'Space Grotesk' }}>
        {value}
      </p>
      {sub != null && <p className="mt-1 text-xs" style={{ color: '#A9ABB3' }}>{sub}</p>}
    </div>
  );
}
