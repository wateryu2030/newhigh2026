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
    <div className="flex min-h-[40vh] flex-col items-center justify-center gap-4 rounded-lg border border-slate-600 bg-slate-800/80 px-6 py-12">
      <h2 className="text-lg font-semibold text-white">页面出错</h2>
      <p className="max-w-md text-center text-sm text-slate-400">{error.message}</p>
      <button
        onClick={() => reset()}
        className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
      >
        重试
      </button>
    </div>
  );
}
