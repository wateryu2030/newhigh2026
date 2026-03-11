interface StatCardProps {
  title: string;
  value: string | number;
  sub?: string;
  positive?: boolean;
}

export function StatCard({ title, value, sub, positive }: StatCardProps) {
  return (
    <div className="card">
      <p className="text-sm font-medium text-slate-400">{title}</p>
      <p className={`mt-1 text-2xl font-bold sm:text-3xl ${positive === true ? 'text-emerald-400' : positive === false ? 'text-red-400' : 'text-white'}`}>
        {value}
      </p>
      {sub != null && <p className="mt-1 text-xs text-slate-500">{sub}</p>}
    </div>
  );
}
