'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type BacktestResultResponse } from '@/api/client';

const QUERY_KEYS = {
  dashboard: ['dashboard'] as const,
  dataStatus: ['dataStatus'] as const,
  strategiesMarket: (limit?: number) => ['strategiesMarket', limit] as const,
  backtestResult: (params?: Record<string, string>) => ['backtestResult', params] as const,
  systemStatus: (limit?: number) => ['systemStatus', limit] as const,
  aiDecision: ['aiDecision'] as const,
};

export function useDashboard() {
  return useQuery({
    queryKey: QUERY_KEYS.dashboard,
    queryFn: () => api.dashboard(),
  });
}

export function useDataStatus() {
  return useQuery({
    queryKey: QUERY_KEYS.dataStatus,
    queryFn: () => api.dataStatus(),
  });
}

export function useStrategiesMarket(limit?: number) {
  return useQuery({
    queryKey: QUERY_KEYS.strategiesMarket(limit),
    queryFn: () => api.strategiesMarket(limit),
  });
}

export function useBacktestResult(params?: { symbol?: string; start_date?: string; end_date?: string; signal_source?: string }) {
  return useQuery({
    queryKey: QUERY_KEYS.backtestResult(params ?? {}),
    queryFn: () => api.backtestResult(params),
  });
}

export function useSystemStatus(limit?: number) {
  return useQuery({
    queryKey: QUERY_KEYS.systemStatus(limit),
    queryFn: () => api.systemStatus(limit),
  });
}

export function useAiDecision() {
  return useQuery({
    queryKey: QUERY_KEYS.aiDecision,
    queryFn: () => api.aiDecision(),
  });
}

export function useInvalidateDashboard() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: QUERY_KEYS.dashboard });
}
