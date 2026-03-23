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
 * 与股东策略页面设计 token 一致
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
      className="w-full rounded-2xl border p-4 transition-transform duration-200 hover:scale-[1.01] md:p-5"
      style={{
        backgroundColor: 'rgba(255,116,57,0.08)',
        borderColor: 'rgba(255,116,57,0.3)',
      }}
    >
      <h2
        className={`font-medium ${compact ? 'text-xs md:text-sm' : 'text-sm'}`}
        style={{ color: '#FF7439' }}
      >
        {title}
      </h2>
      {description && (
        <p
          className={`mt-1 ${compact ? 'text-xs md:text-sm' : 'text-sm'}`}
          style={{ color: '#A9ABB3' }}
        >
          {description}
        </p>
      )}
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <Link
          href={linkHref}
          className="font-medium hover:underline"
          style={{ color: '#FF3B30' }}
        >
          {linkLabel}
        </Link>
        {hint && (
          <>
            <span style={{ color: '#A9ABB3' }}>|</span>
            <span className={`${compact ? 'text-[10px] md:text-xs' : 'text-xs'}`} style={{ color: '#A9ABB3' }}>
              {hint}
            </span>
          </>
        )}
      </div>
    </div>
  );
}
