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
      className={`flex min-h-[120px] flex-col items-center justify-center rounded-xl border border-dashed border-card-border bg-surface-container-high/30 py-8 text-center ${className}`}
    >
      <p className="text-sm font-medium text-text-secondary">{title}</p>
      {description && <p className="mt-1 text-xs text-text-dim">{description}</p>}
      {children && <div className="mt-4">{children}</div>}
    </div>
  );
}
