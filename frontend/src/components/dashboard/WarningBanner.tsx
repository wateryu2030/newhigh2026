'use client';

import Link from 'next/link';

interface WarningBannerProps {
  title: string;
  description?: string;
  hint?: string;
  linkHref?: string;
  linkLabel?: string;
  /** 移动端时文字可缩小 */
  compact?: boolean;
}

/**
 * 数据完整性提醒横幅，占满宽度
 * 与 DESIGN.md / globals.css token 一致
 */
export function WarningBanner({
  title,
  description,
  hint,
  linkHref = '/data',
  linkLabel = '查看并更新 →',
  compact = false,
}: WarningBannerProps) {
  return (
    <div
      className="w-full rounded-2xl border border-[color:var(--color-warning-banner-border)] bg-[color:var(--color-warning-banner-bg)] p-4 transition-transform duration-200 hover:scale-[1.01] md:p-5"
    >
      <h2 className={`font-medium text-tertiary ${compact ? 'text-xs md:text-sm' : 'text-sm'}`}>{title}</h2>
      {description && (
        <p className={`mt-1 text-on-surface-variant ${compact ? 'text-xs md:text-sm' : 'text-sm'}`}>
          {description}
        </p>
      )}
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <Link href={linkHref} className="font-medium text-primary-fixed hover:underline">
          {linkLabel}
        </Link>
        {hint && (
          <>
            <span className="text-on-surface-variant">|</span>
            <span className={`text-on-surface-variant ${compact ? 'text-[10px] md:text-xs' : 'text-xs'}`}>
              {hint}
            </span>
          </>
        )}
      </div>
    </div>
  );
}
