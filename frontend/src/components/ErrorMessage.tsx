'use client';

interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorMessage({ message, onRetry, className = '' }: ErrorMessageProps) {
  return (
    <div
      className={`rounded-xl border border-[color:var(--color-error-banner-border)] bg-[color:var(--color-error-banner-bg)] p-4 text-on-surface ${className}`}
      role="alert"
    >
      <p className="text-sm font-medium">错误</p>
      <p className="mt-1 text-sm text-text-primary">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 rounded-lg bg-surface-container-high px-3 py-2 text-sm text-on-surface hover:opacity-90"
        >
          重试
        </button>
      )}
    </div>
  );
}

export function PageError({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex min-h-[200px] items-center justify-center py-12">
      <ErrorMessage message={message} onRetry={onRetry} />
    </div>
  );
}
