'use client';

/** 列表/卡片区通用骨架（移动端友好） */
export function PageSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="animate-pulse space-y-3" aria-hidden>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="h-24 rounded-xl border border-card-border bg-surface-container-high/60"
        />
      ))}
    </div>
  );
}
