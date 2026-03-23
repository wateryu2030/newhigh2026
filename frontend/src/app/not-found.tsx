import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="flex min-h-[40vh] flex-col items-center justify-center gap-4 rounded-lg border border-slate-600 bg-slate-800/80 px-6 py-12">
      <h2 className="text-lg font-semibold text-white">页面不存在</h2>
      <p className="text-sm text-slate-400">您访问的页面未找到</p>
      <Link
        href="/"
        className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
      >
        返回首页
      </Link>
    </div>
  );
}
