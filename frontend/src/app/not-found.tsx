import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="flex min-h-[40vh] flex-col items-center justify-center gap-4 rounded-lg border border-card-border bg-card-bg/80 px-6 py-12">
      <h2 className="text-lg font-semibold text-on-surface">页面不存在</h2>
      <p className="text-sm text-text-secondary">您访问的页面未找到</p>
      <Link
        href="/"
        className="rounded-lg bg-primary-fixed px-4 py-2 text-sm font-medium text-on-warm-fill hover:opacity-90"
      >
        返回首页
      </Link>
    </div>
  );
}
