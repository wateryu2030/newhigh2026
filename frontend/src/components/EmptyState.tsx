'use client';

interface EmptyStateProps {
  title?: string;
  description?: string;
  className?: string;
  children?: React.ReactNode;
}

export function EmptyState({
  title = '暂无数据',
  description,
  className = '',
  children,
}: EmptyStateProps) {
  return (
    <div
      className={`flex min-h-[120px] flex-col items-center justify-center rounded-xl border border-dashed border-slate-600 bg-slate-800/30 py-8 text-center ${className}`}
    >
      <p className="text-sm font-medium text-slate-400">{title}</p>
      {description && <p className="mt-1 text-xs text-slate-500">{description}</p>}
      {children && <div className="mt-4">{children}</div>}
    </div>
  );
}
