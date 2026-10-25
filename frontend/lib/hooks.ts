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
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: prompt2Keys.campaigns });
      qc.invalidateQueries({ queryKey: prompt2Keys.campaign(id) });
    },
  });
}

export function useResumeCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => campaignsApi.resume(id),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: prompt2Keys.campaigns });
      qc.invalidateQueries({ queryKey: prompt2Keys.campaign(id) });
    },
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

// ─── Prompt 3 Query Keys & Hooks ─────────────────────────────────────────────

import {
  calendarApi,
  connectionsApi,
  ideasApi,
  postsApi,
  videoApi,
  ContentIdea,
  Post,
  VideoProject,
} from "./api-client";

export const prompt3Keys = {
  connections: ["connections"] as const,
  ideas: (params?: any) => ["ideas", params] as const,
  posts: (params?: any) => ["posts", params] as const,
  calendar: (params?: any) => ["calendar", params] as const,
  videos: (status?: string) => ["videos", status] as const,
  video: (id: string) => ["video", id] as const,
};

// ─── Connections Hooks ───────────────────────────────────────────────────────

export function useConnections() {
  return useQuery({
    queryKey: prompt3Keys.connections,
    queryFn: connectionsApi.list,
  });
}

export function useConnectMock() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ platform, handle }: { platform: string; handle: string }) =>
      connectionsApi.connectMock(platform, handle),
    onSuccess: () => qc.invalidateQueries({ queryKey: prompt3Keys.connections }),
  });
}

export function useDirectConnect() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { platform: string; handle?: string; external_id?: string; access_token: string }) =>
      connectionsApi.directConnect(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: prompt3Keys.connections }),
  });
}

export function useDisconnectAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => connectionsApi.disconnect(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: prompt3Keys.connections }),
  });
}

// ─── Ideas Hooks ─────────────────────────────────────────────────────────────

export function useIdeas(params?: { pillar?: string; status?: string; source?: string }) {
  return useQuery({
    queryKey: prompt3Keys.ideas(params),
    queryFn: () => ideasApi.list(params),
  });
}

export function useCreateIdea() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<ContentIdea>) => ideasApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ideas"] }),
  });
}

export function useGenerateIdeasBatch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ count, customPrompt }: { count?: number; customPrompt?: string }) =>
      ideasApi.generateBatch(count, customPrompt),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ideas"] }),
  });
}

export function useUpdateIdea() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ContentIdea> }) =>
      ideasApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ideas"] }),
  });
}

export function useDeleteIdea() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => ideasApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ideas"] }),
  });
}

// ─── Posts Hooks ─────────────────────────────────────────────────────────────

export function usePosts(params?: { platform?: string; status?: string; idea_id?: string; limit?: number }) {
  return useQuery({
    queryKey: prompt3Keys.posts(params),
    queryFn: () => postsApi.list(params),
  });
}

export function useCreatePost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<Post>) => postsApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["posts"] });
      qc.invalidateQueries({ queryKey: ["calendar"] });
    },
  });
}

export function useGeneratePlatformPosts() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ ideaId, platforms, linkUrl }: { ideaId: string; platforms?: string[]; linkUrl?: string }) =>
      postsApi.generatePlatformPosts(ideaId, platforms, linkUrl),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["posts"] });
      qc.invalidateQueries({ queryKey: ["calendar"] });
      qc.invalidateQueries({ queryKey: queryKeys.analyticsOverview });
    },
  });
}

export function useApprovePost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, scheduledAt }: { id: string; scheduledAt?: string }) =>
      postsApi.approve(id, scheduledAt),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["posts"] });
      qc.invalidateQueries({ queryKey: ["calendar"] });
      qc.invalidateQueries({ queryKey: queryKeys.analyticsOverview });
    },
  });
}

export function useRejectPost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) =>
      postsApi.reject(id, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["posts"] });
      qc.invalidateQueries({ queryKey: ["calendar"] });
      qc.invalidateQueries({ queryKey: queryKeys.analyticsOverview });
    },
  });
}

export function useReschedulePost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, scheduledAt }: { id: string; scheduledAt: string }) =>
      postsApi.reschedule(id, scheduledAt),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["posts"] });
      qc.invalidateQueries({ queryKey: ["calendar"] });
    },
  });
}

export function useRetryPost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => postsApi.retry(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["posts"] });
      qc.invalidateQueries({ queryKey: ["calendar"] });
    },
  });
}

export function usePublishPost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => postsApi.publish(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["posts"] });
      qc.invalidateQueries({ queryKey: ["calendar"] });
    },
  });
}

export function useUpdatePost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Post> }) =>
      postsApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["posts"] });
      qc.invalidateQueries({ queryKey: ["calendar"] });
    },
  });
}

export function useDeletePost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => postsApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["posts"] });
      qc.invalidateQueries({ queryKey: ["calendar"] });
      qc.invalidateQueries({ queryKey: queryKeys.analyticsOverview });
    },
  });
}

// ─── Calendar Hooks ──────────────────────────────────────────────────────────

export function useCalendarFeed(params?: { start_date?: string; end_date?: string; platform?: string }) {
  return useQuery({
    queryKey: prompt3Keys.calendar(params),
    queryFn: () => calendarApi.getFeed(params),
  });
}

// ─── Video Studio Hooks ──────────────────────────────────────────────────────

export function useVideos(status?: string) {
  return useQuery({
    queryKey: prompt3Keys.videos(status),
    queryFn: () => videoApi.list(status),
  });
}

export function useVideo(id: string) {
  return useQuery({
    queryKey: prompt3Keys.video(id),
    queryFn: () => videoApi.get(id),
    enabled: !!id,
  });
}

export function usePlanVideo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ targetKeyword, additionalNotes }: { targetKeyword: string; additionalNotes?: string }) =>
      videoApi.plan(targetKeyword, additionalNotes),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["videos"] }),
  });
}

export function useUploadVideoAsset() {
  return useMutation({
    mutationFn: ({ id, filename }: { id: string; filename?: string }) =>
      videoApi.getUploadUrl(id, filename),
  });
}

export function usePublishYouTube() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => videoApi.publishYouTube(id),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: ["videos"] });
      qc.invalidateQueries({ queryKey: prompt3Keys.video(id) });
    },
  });
}

export function useCrossPostCaptions() {
  return useMutation({
    mutationFn: (id: string) => videoApi.crossPostCaptions(id),
  });
}

export function useDeleteVideo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => videoApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["videos"] }),
  });
}

// ─── Prompt 4 Query Keys & Hooks ─────────────────────────────────────────────

import {
  seoApi,
  toolsApi,
  launchApi,
  reviewsApi,
  SEOTemplate,
  SEOPageItem,
  LaunchTaskItem,
  ReviewRequestItem,
} from "./api-client";

export const prompt4Keys = {
  seoTemplates: ["seo", "templates"] as const,
  seoPages: (params?: any) => ["seo", "pages", params] as const,
  toolsOverview: ["tools", "overview"] as const,
  launchTasks: (platform?: string, status?: string) => ["launch", "tasks", platform, status] as const,
  reviews: ["reviews"] as const,
};

// ─── SEO Hooks ───────────────────────────────────────────────────────────────

export function useSEOTemplates() {
  return useQuery({
    queryKey: prompt4Keys.seoTemplates,
    queryFn: seoApi.getTemplates,
  });
}

export function useCreateSEOTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      type: string;
      url_pattern: string;
      title_pattern: string;
      h1_pattern: string;
      body_prompt: string;
    }) => seoApi.createTemplate(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: prompt4Keys.seoTemplates }),
  });
}

export function useDeleteSEOTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => seoApi.deleteTemplate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: prompt4Keys.seoTemplates }),
  });
}

export function useSEOPages(params?: { status?: string; template_id?: string; min_quality_score?: number }) {
  return useQuery({
    queryKey: prompt4Keys.seoPages(params),
    queryFn: () => seoApi.listPages(params),
  });
}

export function useGenerateSEOPages() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      templateId,
      variablesList,
      csvContent,
    }: {
      templateId: string;
      variablesList: Array<Record<string, any>>;
      csvContent?: string;
    }) => seoApi.generate(templateId, variablesList, csvContent),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["seo", "pages"] }),
  });
}

export function useBatchPublishSEOPages() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (pageIds: string[]) => seoApi.batchPublish(pageIds),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["seo", "pages"] });
      qc.invalidateQueries({ queryKey: ["analytics", "overview"] });
    },
  });
}

// ─── Tools Hooks ─────────────────────────────────────────────────────────────

export function useToolsOverview() {
  return useQuery({
    queryKey: prompt4Keys.toolsOverview,
    queryFn: toolsApi.getOverview,
    refetchInterval: 30 * 1000,
  });
}

export function useGradeSubjectLine() {
  return useMutation({
    mutationFn: ({
      subjectLine,
      industryContext,
      emailCaptured,
      utmSource,
    }: {
      subjectLine: string;
      industryContext?: string;
      emailCaptured?: string;
      utmSource?: string;
    }) => toolsApi.gradeSubject(subjectLine, industryContext, emailCaptured, utmSource),
  });
}

export function useVerifyEmailTool() {
  return useMutation({
    mutationFn: ({
      email,
      emailCaptured,
      utmSource,
    }: {
      email: string;
      emailCaptured?: string;
      utmSource?: string;
    }) => toolsApi.verifyEmail(email, emailCaptured, utmSource),
  });
}

// ─── Launch Hub Hooks ────────────────────────────────────────────────────────

export function useLaunchTasks(platform?: string, status?: string) {
  return useQuery({
    queryKey: prompt4Keys.launchTasks(platform, status),
    queryFn: () => launchApi.listTasks(platform, status),
  });
}

export function useCreateLaunchTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<LaunchTaskItem>) => launchApi.createTask(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["launch", "tasks"] }),
  });
}

export function useUpdateLaunchTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<LaunchTaskItem> }) =>
      launchApi.updateTask(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["launch", "tasks"] }),
  });
}

export function useDeleteLaunchTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => launchApi.deleteTask(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["launch", "tasks"] }),
  });
}

export function useGenerateLaunchAssets() {
  return useMutation({
    mutationFn: ({
      platform,
      taskType,
      customNotes,
    }: {
      platform: string;
      taskType: string;
      customNotes?: string;
    }) => launchApi.generateAssets(platform, taskType, customNotes),
  });
}

// ─── Reviews Hooks ───────────────────────────────────────────────────────────

export function useReviewRequests() {
  return useQuery({
    queryKey: prompt4Keys.reviews,
    queryFn: reviewsApi.listRequests,
  });
}

export function useSendReviewRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ userEmail, platform }: { userEmail: string; platform: "g2" | "capterra" }) =>
      reviewsApi.sendRequest(userEmail, platform),
    onSuccess: () => qc.invalidateQueries({ queryKey: prompt4Keys.reviews }),
  });
}



