/**
 * TanStack Query hooks for the Growth Engine API.
 * Each hook wraps an API call with caching, loading, and error states.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  analyticsApi,
  authApi,
  brandApi,
  BrandProfileUpdate,
  clearTokens,
  setTokens,
  UserResponse,
} from "./api-client";

// ─── Query keys ──────────────────────────────────────────────────────────────

export const queryKeys = {
  me: ["me"] as const,
  brand: ["brand"] as const,
  analyticsOverview: ["analytics", "overview"] as const,
};

// ─── Auth hooks ──────────────────────────────────────────────────────────────

export function useMe() {
  return useQuery({
    queryKey: queryKeys.me,
    queryFn: authApi.me,
    retry: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      authApi.login(email, password),
    onSuccess: (data) => {
      setTokens(data.access_token, data.refresh_token);
      qc.invalidateQueries({ queryKey: queryKeys.me });
    },
  });
}

export function useRegister() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      authApi.register(email, password),
    onSuccess: (data) => {
      setTokens(data.access_token, data.refresh_token);
      qc.invalidateQueries({ queryKey: queryKeys.me });
    },
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return () => {
    clearTokens();
    qc.clear();
    window.location.href = "/admin/login";
  };
}

// ─── Brand hooks ─────────────────────────────────────────────────────────────

export function useBrandProfile() {
  return useQuery({
    queryKey: queryKeys.brand,
    queryFn: brandApi.get,
    staleTime: 30 * 1000,
  });
}

export function useUpdateBrandProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: BrandProfileUpdate) => brandApi.update(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.brand });
    },
  });
}

// ─── Analytics hooks ─────────────────────────────────────────────────────────

export function useAnalyticsOverview() {
  return useQuery({
    queryKey: queryKeys.analyticsOverview,
    queryFn: analyticsApi.overview,
    refetchInterval: 60 * 1000, // auto-refresh every 60s
    staleTime: 30 * 1000,
  });
}
