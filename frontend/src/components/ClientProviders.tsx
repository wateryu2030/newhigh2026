'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { LangProvider } from '@/context/LangContext';
import { AuthProvider } from '@/context/AuthContext';
import { LanApiHintBanner } from '@/components/LanApiHintBanner';
import { ChunkLoadRecovery } from '@/components/ChunkLoadRecovery';
import { ServiceWorkerRegister } from '@/components/ServiceWorkerRegister';

export function ClientProviders({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, retry: 1 } } }));
  return (
    <QueryClientProvider client={queryClient}>
      <LangProvider>
        <AuthProvider>
          <ServiceWorkerRegister />
          <ChunkLoadRecovery />
          <LanApiHintBanner />
          {children}
        </AuthProvider>
      </LangProvider>
    </QueryClientProvider>
  );
}
