interface StatCardProps {
  title: string;
  value: string | number;
  sub?: string;
  positive?: boolean;
}

export function StatCard({ title, value, sub, positive }: StatCardProps) {
  const valueTone =
    positive === true ? 'text-primary-fixed' : positive === false ? 'text-tertiary' : 'text-on-surface';
  return (
    <div className="card">
      <p className="mb-1 font-label text-xs font-medium uppercase tracking-wider text-on-surface-variant">
        {title}
      </p>
      <p className={`mt-1 font-label text-2xl font-bold sm:text-3xl ${valueTone}`}>{value}</p>
      {sub != null && <p className="mt-1 text-xs text-on-surface-variant">{sub}</p>}
    </div>
  );
}
