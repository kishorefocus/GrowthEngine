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

// ─── Prompt 2 Query Keys ─────────────────────────────────────────────────────

export const prompt2Keys = {
  icps: ["icps"] as const,
  leads: (params?: any) => ["leads", params] as const,
  suppression: (search?: string) => ["suppression", search] as const,
  campaigns: ["campaigns"] as const,
  campaign: (id: string) => ["campaign", id] as const,
  campaignStats: (id: string) => ["campaignStats", id] as const,
  sequenceSteps: (campaignId: string) => ["sequenceSteps", campaignId] as const,
  inbox: (params?: any) => ["inbox", params] as const,
  domainHealth: (domain?: string) => ["domainHealth", domain] as const,
};

import {
  campaignsApi,
  icpApi,
  inboxApi,
  leadsApi,
  suppressionApi,
  Campaign,
  ICP,
  Lead,
  SequenceStep,
} from "./api-client";

// ─── ICP Hooks ───────────────────────────────────────────────────────────────

export function useICPs() {
  return useQuery({
    queryKey: prompt2Keys.icps,
    queryFn: icpApi.list,
  });
}
export const useIcps = useICPs;

export function useCreateICP() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<ICP>) => icpApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: prompt2Keys.icps }),
  });
}

export function useDeleteICP() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => icpApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: prompt2Keys.icps }),
  });
}

// ─── Leads Hooks ─────────────────────────────────────────────────────────────

export function useLeads(params?: { icp_id?: string; status?: string; country?: string; verification_status?: string }) {
  return useQuery({
    queryKey: prompt2Keys.leads(params),
    queryFn: () => leadsApi.list(params),
  });
}

export function useCreateLead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<Lead>) => leadsApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["leads"] }),
  });
}

export function useVerifyLead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => leadsApi.verify(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["leads"] }),
  });
}

export function useDeleteLead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => leadsApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["leads"] });
      qc.invalidateQueries({ queryKey: ["suppression"] });
    },
  });
}

export function useImportGlobalReach() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ icp_id, max_results }: { icp_id: string; max_results?: number }) =>
      leadsApi.importGlobalReach(icp_id, max_results),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["leads"] }),
  });
}

export function useImportCsv() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { icp_id?: string; column_mapping: any; rows: any[] }) =>
      leadsApi.importCsv(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["leads"] }),
  });
}

// ─── Suppression Hooks ───────────────────────────────────────────────────────

export function useSuppressionList(search?: string) {
  return useQuery({
    queryKey: prompt2Keys.suppression(search),
    queryFn: () => suppressionApi.list(search),
  });
}

export function useAddSuppression() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ email, reason }: { email: string; reason?: string }) =>
      suppressionApi.add(email, reason),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["suppression"] }),
  });
}

export function useRemoveSuppression() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => suppressionApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["suppression"] }),
  });
}

// ─── Campaigns Hooks ─────────────────────────────────────────────────────────

export function useCampaigns() {
  return useQuery({
    queryKey: prompt2Keys.campaigns,
    queryFn: campaignsApi.list,
  });
}

export function useCampaign(id: string) {
  return useQuery({
    queryKey: prompt2Keys.campaign(id),
    queryFn: () => campaignsApi.get(id),
    enabled: !!id,
  });
}

export function useCampaignStats(id: string) {
  return useQuery({
    queryKey: prompt2Keys.campaignStats(id),
    queryFn: () => campaignsApi.stats(id),
    enabled: !!id,
  });
}

export function useCreateCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<Campaign>) => campaignsApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: prompt2Keys.campaigns }),
  });
}

export function useUpdateCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Campaign> }) =>
      campaignsApi.update(id, data),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: prompt2Keys.campaigns });
      qc.invalidateQueries({ queryKey: prompt2Keys.campaign(id) });
    },
  });
}

export function useDeleteCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => campaignsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: prompt2Keys.campaigns }),
  });
}

export function usePauseCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => campaignsApi.pause(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: prompt2Keys.campaigns }),
  });
}

export function useResumeCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => campaignsApi.resume(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: prompt2Keys.campaigns }),
  });
}

export function useEnrollLeads(campaignId?: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: string[] | { campaign_id: string; lead_ids: string[] }) => {
      if (Array.isArray(args)) {
        return campaignsApi.enrollLeads(campaignId!, args);
      }
      return campaignsApi.enrollLeads(args.campaign_id, args.lead_ids);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["leads"] });
      qc.invalidateQueries({ queryKey: prompt2Keys.campaigns });
    },
  });
}

// ─── Sequence Steps Hooks ─────────────────────────────────────────────────────

export function useSequenceSteps(campaignId: string) {
  return useQuery({
    queryKey: prompt2Keys.sequenceSteps(campaignId),
    queryFn: () => campaignsApi.listSteps(campaignId),
    enabled: !!campaignId,
  });
}
export const useCampaignSteps = useSequenceSteps;

export function useCreateCampaignStep(campaignId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (step: Partial<SequenceStep>) =>
      campaignsApi.createStep(campaignId, step),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: prompt2Keys.sequenceSteps(campaignId) }),
  });
}

export function useUpdateCampaignStep(campaignId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ stepId, data }: { stepId: string; data: Partial<SequenceStep> }) =>
      campaignsApi.updateStep(campaignId, stepId, data),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: prompt2Keys.sequenceSteps(campaignId) }),
  });
}

export function useDeleteCampaignStep(campaignId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (stepId: string) =>
      campaignsApi.deleteStep(campaignId, stepId),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: prompt2Keys.sequenceSteps(campaignId) }),
  });
}

export function useCreateStep() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ campaignId, step }: { campaignId: string; step: Partial<SequenceStep> }) =>
      campaignsApi.createStep(campaignId, step),
    onSuccess: (_, { campaignId }) =>
      qc.invalidateQueries({ queryKey: prompt2Keys.sequenceSteps(campaignId) }),
  });
}

export function useUpdateStep() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ campaignId, stepId, step }: { campaignId: string; stepId: string; step: Partial<SequenceStep> }) =>
      campaignsApi.updateStep(campaignId, stepId, step),
    onSuccess: (_, { campaignId }) =>
      qc.invalidateQueries({ queryKey: prompt2Keys.sequenceSteps(campaignId) }),
  });
}

export function useDeleteStep() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ campaignId, stepId }: { campaignId: string; stepId: string }) =>
      campaignsApi.deleteStep(campaignId, stepId),
    onSuccess: (_, { campaignId }) =>
      qc.invalidateQueries({ queryKey: prompt2Keys.sequenceSteps(campaignId) }),
  });
}

export function usePreviewAi() {
  return useMutation({
    mutationFn: ({ campaignId, leadId, stepId }: { campaignId: string; leadId: string; stepId: string }) =>
      campaignsApi.previewAi(campaignId, leadId, stepId),
  });
}

// ─── Domain Health Hook ──────────────────────────────────────────────────────

export function useDomainHealth(domain?: string) {
  return useQuery({
    queryKey: prompt2Keys.domainHealth(domain),
    queryFn: () => campaignsApi.domainHealth(domain),
    staleTime: 60 * 1000,
  });
}

// ─── Inbox Hooks ─────────────────────────────────────────────────────────────

export function useReplies(params?: { classification?: string; handled?: boolean; limit?: number }) {
  return useQuery({
    queryKey: prompt2Keys.inbox(params),
    queryFn: () => inboxApi.listReplies(params),
    refetchInterval: 15 * 1000,
  });
}
export const useInboxReplies = useReplies;

export function useHandleReply() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => inboxApi.handleReply(id, true),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["inbox"] }),
  });
}

export function useSuppressReply() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => inboxApi.suppressReply(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["inbox"] });
      qc.invalidateQueries({ queryKey: ["suppression"] });
    },
  });
}


