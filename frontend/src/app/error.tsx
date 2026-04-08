'use client';

import { useEffect } from 'react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-[40vh] flex-col items-center justify-center gap-4 rounded-lg border border-card-border bg-card-bg/80 px-6 py-12">
      <h2 className="text-lg font-semibold text-on-surface">页面出错</h2>
      <p className="max-w-md text-center text-sm text-text-secondary">{error.message}</p>
      <button
        onClick={() => reset()}
        className="rounded-lg bg-primary-fixed px-4 py-2 text-sm font-medium text-on-warm-fill hover:opacity-90"
      >
        重试
      </button>
    </div>
  );
}
