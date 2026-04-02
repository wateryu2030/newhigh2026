'use client';

import type { ReactNode } from 'react';

import { EmptyState } from './EmptyState';
import { PageError } from './ErrorMessage';
import { PageLoading } from './LoadingSpinner';

export type AsyncStateProps<T> = {
  loading: boolean;
  error: string | null;
  data: T | null | undefined;
  isEmpty?: (data: T) => boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  children: (data: T) => ReactNode;
  onRetry?: () => void;
  loadingMessage?: string;
};

export function AsyncState<T>({
  loading,
  error,
  data,
  isEmpty,
  emptyTitle = '暂无数据',
  emptyDescription,
  children,
  onRetry,
  loadingMessage,
}: AsyncStateProps<T>) {
  if (loading) {
    return <PageLoading message={loadingMessage} />;
  }
  if (error) {
    return <PageError message={error} onRetry={onRetry} />;
  }
  if (data == null) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />;
  }
  if (isEmpty?.(data)) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />;
  }
  return <>{children(data)}</>;
}
