'use client';

interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorMessage({ message, onRetry, className = '' }: ErrorMessageProps) {
  return (
    <div
      className={`rounded-xl border border-red-500/30 bg-slate-800/80 p-4 text-red-200 ${className}`}
      role="alert"
    >
      <p className="text-sm font-medium">错误</p>
      <p className="mt-1 text-sm text-slate-300">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 rounded-lg bg-slate-700 px-3 py-2 text-sm text-white hover:bg-slate-600"
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
