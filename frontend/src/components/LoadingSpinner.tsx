'use client';

export function LoadingSpinner({ className = '' }: { className?: string }) {
  return (
    <div className={`inline-block h-8 w-8 animate-spin rounded-full border-2 border-card-border border-t-fund-indigo ${className}`} role="status" aria-label="加载中" />
  );
}

export function PageLoading({ message = '加载中…' }: { message?: string }) {
  return (
    <div className="flex min-h-[200px] flex-col items-center justify-center gap-4 py-12 text-text-secondary">
      <LoadingSpinner />
      <p className="text-sm">{message}</p>
    </div>
  );
}
