'use client';

import './globals.css';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="zh" className="dark">
      <body className="min-h-screen bg-slate-900">
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-6">
          <h1 className="text-xl font-bold text-white">应用出错</h1>
          <p className="max-w-md text-center text-slate-400">{error.message}</p>
          <button
            onClick={() => reset()}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
          >
            重试
          </button>
        </div>
      </body>
    </html>
  );
}
