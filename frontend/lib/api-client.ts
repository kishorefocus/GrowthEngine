/**
 * Typed API client for GlobalReach Growth Engine backend.
 * Auto-refreshes tokens via TanStack Query's error boundary.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_BASE = `${API_URL}/api/v1`;

// ─── Types ───────────────────────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  role: string;
}

export interface UserResponse {
  id: string;
  email: string;
  role: string;
}

export interface BrandProfile {
  id: string;
  product_name: string;
  one_liner: string | null;
  value_props: string[] | null;
  tone: string | null;
  banned_phrases: string[] | null;
  website_url: string | null;
  physical_address: string | null;
}

export interface BrandProfileUpdate {
  product_name?: string;
  one_liner?: string;
  value_props?: string[];
  tone?: string;
  banned_phrases?: string[];
  website_url?: string;
  physical_address?: string;
}

export interface AnalyticsOverview {
  overview: {
    total_visits: number;
    total_signups: number;
    conversion_rate_pct: number;
  };
  email: {
    total_scheduled: number;
    sent: number;
    reply_rate_pct: number;
    bounce_rate_pct: number;
  };
  channels: Record<string, number>;
  signups_by_channel: Record<string, number>;
  top_posts: Array<{ id: string; platform: string; body_preview: string; published_at: string }>;
  top_seo_pages: Array<{ id: string; slug: string; title: string | null; quality_score: number | null }>;
}

export interface HealthResponse {
  status: string;
  service: string;
  timestamp: string;
  dry_run: boolean;
  environment: string;
  database: { status: string; latency_ms: number | null };
}

export interface ApiError {
  detail: string;
  status: number;
}

// ─── Token storage ───────────────────────────────────────────────────────────

const TOKEN_KEY = "gr_access_token";
const REFRESH_KEY = "gr_refresh_token";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(TOKEN_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_KEY);
}

// ─── Core fetch helper ───────────────────────────────────────────────────────

let _isRefreshing = false;
let _refreshQueue: Array<(token: string) => void> = [];

async function refreshAccessToken(): Promise<string> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) throw new Error("No refresh token available");

  const res = await fetch(`${API_BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!res.ok) {
    clearTokens();
    throw new Error("Session expired. Please log in again.");
  }

  const data: TokenResponse = await res.json();
  setTokens(data.access_token, data.refresh_token);
  return data.access_token;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit & { skipAuth?: boolean } = {}
): Promise<T> {
  const { skipAuth, ...fetchOptions } = options;
  const url = `${API_BASE}${path}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(fetchOptions.headers as Record<string, string>),
  };

  if (!skipAuth) {
    const token = getAccessToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  let response = await fetch(url, { ...fetchOptions, headers });

  // Auto-refresh on 401
  if (response.status === 401 && !skipAuth) {
    if (_isRefreshing) {
      // Wait for current refresh
      const newToken = await new Promise<string>((resolve) => {
        _refreshQueue.push(resolve);
      });
      headers["Authorization"] = `Bearer ${newToken}`;
      response = await fetch(url, { ...fetchOptions, headers });
    } else {
      _isRefreshing = true;
      try {
        const newToken = await refreshAccessToken();
        _refreshQueue.forEach((cb) => cb(newToken));
        _refreshQueue = [];
        headers["Authorization"] = `Bearer ${newToken}`;
        response = await fetch(url, { ...fetchOptions, headers });
      } finally {
        _isRefreshing = false;
      }
    }
  }

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const err = await response.json();
      detail = err.detail || detail;
    } catch {}
    const error = new Error(detail) as Error & { status: number };
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) return {} as T;
  return response.json() as Promise<T>;
}

// ─── Auth API ────────────────────────────────────────────────────────────────

export const authApi = {
  register: (email: string, password: string) =>
    apiFetch<TokenResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
      skipAuth: true,
    }),

  login: (email: string, password: string) =>
    apiFetch<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
      skipAuth: true,
    }),

  me: () => apiFetch<UserResponse>("/auth/me"),
};

// ─── Brand API ───────────────────────────────────────────────────────────────

export const brandApi = {
  get: () => apiFetch<BrandProfile>("/brand"),
  update: (data: BrandProfileUpdate) =>
    apiFetch<BrandProfile>("/brand", { method: "PUT", body: JSON.stringify(data) }),
};

// ─── Analytics API ───────────────────────────────────────────────────────────

export const analyticsApi = {
  overview: () => apiFetch<AnalyticsOverview>("/analytics/overview"),
};

// ─── Prompt 2 Interfaces ───────────────────────────────────────────────────

export interface ICP {
  id: string;
  name: string;
  industry?: string;
  geography?: string;
  company_size?: string;
  titles?: string[];
  keywords?: string[];
  created_at: string;
}

export interface Lead {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  company?: string;
  title?: string;
  website?: string;
  country?: string;
  industry?: string;
  source?: string;
  verification_status: "valid" | "invalid" | "risky" | "pending";
  icp_id?: string;
  status: "new" | "queued" | "contacted" | "replied" | "signed_up" | "bounced" | "unsubscribed";
  created_at: string;
}

export interface SuppressionEntry {
  id: string;
  email_or_domain: string;
  reason?: string;
  added_at: string;
}

export interface Campaign {
  id: string;
  name: string;
  icp_id?: string;
  status: "draft" | "active" | "paused" | "completed";
  daily_limit: number;
  sending_window?: { start: string; end: string };
  timezone_mode: "recipient" | "fixed";
  created_at: string;
}

export interface CampaignStats {
  campaign_id: string;
  total_leads: number;
  sent: number;
  delivered: number;
  opened: number;
  clicked: number;
  replied: number;
  bounced: number;
  complained: number;
  bounce_rate_pct: number;
  complaint_rate_pct: number;
  reply_rate_pct: number;
}

export interface SequenceStep {
  id: string;
  sequence_id: string;
  step_number: number;
  delay_days: number;
  subject_template?: string;
  body_template?: string;
  ai_personalize: boolean;
}

export interface StepStats {
  step_id: string;
  step_number: number;
  sent: number;
  delivered: number;
  opened: number;
  clicked: number;
  replied: number;
  bounced: number;
}

export interface ReplyItem {
  id: string;
  message_id: string;
  body?: string;
  classification: "interested" | "not_now" | "not_interested" | "unsubscribe" | "out_of_office" | "other";
  confidence?: number;
  handled: boolean;
  suggested_response?: string;
  lead?: {
    id: string;
    email: string;
    first_name?: string;
    last_name?: string;
    company?: string;
    title?: string;
  };
  created_at: string;
}

export interface DomainHealth {
  domain: string;
  spf: { status: "pass" | "fail"; record?: string; hint: string };
  dkim: { status: "pass" | "fail"; record?: string; selector?: string; hint: string };
  dmarc: { status: "pass" | "fail"; record?: string; hint: string };
  overall: "pass" | "warn" | "fail";
  warmup_schedule: Array<{ week: number; daily_limit: number; note: string }>;
}

// ─── ICP API ─────────────────────────────────────────────────────────────────

export const icpApi = {
  list: () => apiFetch<ICP[]>("/icps"),
  create: (data: Partial<ICP>) =>
    apiFetch<ICP>("/icps", { method: "POST", body: JSON.stringify(data) }),
  delete: (id: string) =>
    apiFetch<void>(`/icps/${id}`, { method: "DELETE" }),
};

// ─── Leads API ───────────────────────────────────────────────────────────────

export const leadsApi = {
  list: (params?: { icp_id?: string; status?: string; country?: string; verification_status?: string }) => {
    const sp = new URLSearchParams();
    if (params?.icp_id) sp.set("icp_id", params.icp_id);
    if (params?.status) sp.set("status", params.status);
    if (params?.country) sp.set("country", params.country);
    if (params?.verification_status) sp.set("verification_status", params.verification_status);
    const qs = sp.toString() ? `?${sp.toString()}` : "";
    return apiFetch<Lead[]>(`/leads${qs}`);
  },
  create: (data: Partial<Lead>) =>
    apiFetch<Lead>("/leads", { method: "POST", body: JSON.stringify(data) }),
  verify: (id: string) =>
    apiFetch<{ id: string; email: string; verification_status: string; checks: any }>(`/leads/${id}/verify`, { method: "POST" }),
  delete: (id: string) =>
    apiFetch<void>(`/leads/${id}`, { method: "DELETE" }),
  importGlobalReach: (icp_id: string, max_results = 50) =>
    apiFetch<{ imported: number; duplicates_skipped: number }>(`/leads/import/globalreach`, {
      method: "POST",
      body: JSON.stringify({ icp_id, max_results }),
    }),
  importCsv: (data: { icp_id?: string; column_mapping: any; rows: any[] }) =>
    apiFetch<{ imported: number; duplicates_skipped: number; errors: number }>("/leads/import/csv", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

// ─── Suppression API ─────────────────────────────────────────────────────────

export const suppressionApi = {
  list: (search?: string) => {
    const qs = search ? `?search=${encodeURIComponent(search)}` : "";
    return apiFetch<SuppressionEntry[]>(`/suppression${qs}`);
  },
  add: (email_or_domain: string, reason?: string) =>
    apiFetch<SuppressionEntry>("/suppression", {
      method: "POST",
      body: JSON.stringify({ email_or_domain, reason }),
    }),
  remove: (id: string) =>
    apiFetch<void>(`/suppression/${id}`, { method: "DELETE" }),
};

// ─── Campaigns API ───────────────────────────────────────────────────────────

export const campaignsApi = {
  list: () => apiFetch<Campaign[]>("/campaigns"),
  get: (id: string) => apiFetch<Campaign>(`/campaigns/${id}`),
  create: (data: Partial<Campaign>) =>
    apiFetch<Campaign>("/campaigns", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<Campaign>) =>
    apiFetch<Campaign>(`/campaigns/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) =>
    apiFetch<void>(`/campaigns/${id}`, { method: "DELETE" }),
  pause: (id: string) =>
    apiFetch<{ status: string }>(`/campaigns/${id}/pause`, { method: "POST" }),
  resume: (id: string) =>
    apiFetch<{ status: string }>(`/campaigns/${id}/resume`, { method: "POST" }),
  launch: (id: string) =>
    apiFetch<{ status: string }>(`/campaigns/${id}/launch`, { method: "POST" }),
  stats: (id: string) =>
    apiFetch<CampaignStats>(`/campaigns/${id}/stats`),
  enrollLeads: (campaign_id: string, lead_ids: string[]) =>
    apiFetch<{ enrolled: number; skipped: any[] }>(`/campaigns/${campaign_id}/enroll`, {
      method: "POST",
      body: JSON.stringify({ campaign_id, lead_ids }),
    }),
  listSteps: (campaign_id: string) =>
    apiFetch<SequenceStep[]>(`/campaigns/${campaign_id}/steps`),
  createStep: (campaign_id: string, step: Partial<SequenceStep>) =>
    apiFetch<SequenceStep>(`/campaigns/${campaign_id}/steps`, {
      method: "POST",
      body: JSON.stringify(step),
    }),
  updateStep: (campaign_id: string, step_id: string, step: Partial<SequenceStep>) =>
    apiFetch<SequenceStep>(`/campaigns/${campaign_id}/steps/${step_id}`, {
      method: "PUT",
      body: JSON.stringify(step),
    }),
  deleteStep: (campaign_id: string, step_id: string) =>
    apiFetch<void>(`/campaigns/${campaign_id}/steps/${step_id}`, { method: "DELETE" }),
  previewAi: (campaign_id: string, lead_id: string, step_id: string) =>
    apiFetch<{ subject: string; body: string; claims_safe: boolean; violations: string[] }>(
      `/campaigns/${campaign_id}/preview-ai`,
      { method: "POST", body: JSON.stringify({ lead_id, step_id }) }
    ),
  domainHealth: (domain?: string) => {
    const qs = domain ? `?domain=${encodeURIComponent(domain)}` : "";
    return apiFetch<DomainHealth>(`/campaigns/domain-health${qs}`);
  },
};

// ─── Inbox API ───────────────────────────────────────────────────────────────

export const inboxApi = {
  listReplies: (params?: { classification?: string; handled?: boolean }) => {
    const sp = new URLSearchParams();
    if (params?.classification) sp.set("classification", params.classification);
    if (params?.handled !== undefined) sp.set("handled", String(params.handled));
    const qs = sp.toString() ? `?${sp.toString()}` : "";
    return apiFetch<ReplyItem[]>(`/inbox/replies${qs}`);
  },
  handleReply: (id: string, handled: boolean) =>
    apiFetch<ReplyItem>(`/inbox/replies/${id}/handle`, {
      method: "POST",
      body: JSON.stringify({ handled }),
    }),
  suppressReply: (id: string) =>
    apiFetch<{ suppressed: string; status: string }>(`/inbox/replies/${id}/suppress`, {
      method: "POST",
    }),
};

// ─── Health API ──────────────────────────────────────────────────────────────

export const healthApi = {
  check: () =>
    fetch(`${API_URL}/healthz`)
      .then((r) => r.json() as Promise<HealthResponse>)
      .catch(() => null),
};

// ─── Prompt 3 Interfaces ───────────────────────────────────────────────────

export interface SocialAccount {
  id: string;
  platform: "x" | "linkedin" | "instagram" | "facebook" | "youtube";
  handle?: string;
  external_id?: string;
  status: "active" | "expired" | "revoked";
  expires_at?: string;
  created_at: string;
  updated_at: string;
}

export interface ContentIdea {
  id: string;
  topic: string;
  pillar?: "how-to" | "build-in-public" | "competitor_alternatives" | "industry_lead_lists" | "tips_and_stats";
  source: "ai" | "manual" | "seo_gap";
  status: "draft" | "approved" | "archived";
  created_at: string;
  updated_at: string;
}

export interface Post {
  id: string;
  idea_id?: string;
  platform: "x" | "linkedin" | "instagram" | "facebook" | "youtube";
  body?: string;
  media_urls?: string[];
  link_url?: string;
  utm?: Record<string, string>;
  status: "draft" | "pending_approval" | "approved" | "scheduled" | "published" | "failed" | "rejected";
  scheduled_at?: string;
  published_at?: string;
  external_post_id?: string;
  error?: string;
  created_at: string;
  updated_at: string;
}

export interface VideoProject {
  id: string;
  title: string;
  target_keyword?: string;
  script?: string;
  shot_list?: Array<{ step_number: number; screen: string; action: string; voiceover_cue: string }>;
  caption?: string;
  youtube_title?: string;
  youtube_description?: string;
  tags?: string[];
  thumbnail_prompt?: string;
  status: "draft" | "planned" | "recorded" | "published";
  asset_url?: string;
  youtube_video_id?: string;
  created_at: string;
  updated_at: string;
}

export interface CalendarItem {
  id: string;
  type: string;
  platform: string;
  title: string;
  body: string;
  status: string;
  scheduled_at: string;
  published_at?: string;
  external_post_id?: string;
  error?: string;
}

export interface CalendarFeedResponse {
  items: CalendarItem[];
  best_time_suggestions: Record<string, string[]>;
}

export interface CrossPostCaptionsResponse {
  video_id: string;
  instagram_reels: string;
  facebook_reels: string;
  linkedin_video: string;
}

// ─── Prompt 3 APIs ─────────────────────────────────────────────────────────

export const connectionsApi = {
  list: () => apiFetch<SocialAccount[]>("/connections"),
  getAuthorizeUrl: (platform: string) =>
    apiFetch<{ platform: string; authorization_url: string; state: string }>(`/connections/${platform}/authorize`),
  connectMock: (platform: string, handle: string) =>
    apiFetch<SocialAccount>(`/connections/connect-mock?platform=${platform}&handle=${encodeURIComponent(handle)}`, {
      method: "POST",
    }),
  directConnect: (data: { platform: string; handle?: string; external_id?: string; access_token: string }) =>
    apiFetch<SocialAccount>("/connections/direct", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  disconnect: (id: string) =>
    apiFetch<void>(`/connections/${id}`, { method: "DELETE" }),
};

export const ideasApi = {
  list: (params?: { pillar?: string; status?: string; source?: string }) => {
    const sp = new URLSearchParams();
    if (params?.pillar) sp.set("pillar", params.pillar);
    if (params?.status) sp.set("status", params.status);
    if (params?.source) sp.set("source", params.source);
    const qs = sp.toString() ? `?${sp.toString()}` : "";
    return apiFetch<ContentIdea[]>(`/ideas${qs}`);
  },
  create: (data: Partial<ContentIdea>) =>
    apiFetch<ContentIdea>("/ideas", { method: "POST", body: JSON.stringify(data) }),
  generateBatch: (count = 20, customPrompt?: string) =>
    apiFetch<{ generated_count: number; ideas: ContentIdea[] }>("/ideas/generate", {
      method: "POST",
      body: JSON.stringify({ count, custom_prompt: customPrompt }),
    }),
  update: (id: string, data: Partial<ContentIdea>) =>
    apiFetch<ContentIdea>(`/ideas/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) =>
    apiFetch<void>(`/ideas/${id}`, { method: "DELETE" }),
};

export const postsApi = {
  list: (params?: { platform?: string; status?: string; idea_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.platform) sp.set("platform", params.platform);
    if (params?.status) sp.set("status", params.status);
    if (params?.idea_id) sp.set("idea_id", params.idea_id);
    if (params?.limit) sp.set("limit", String(params.limit));
    const qs = sp.toString() ? `?${sp.toString()}` : "";
    return apiFetch<Post[]>(`/posts${qs}`);
  },
  get: (id: string) => apiFetch<Post>(`/posts/${id}`),
  create: (data: Partial<Post>) =>
    apiFetch<Post>("/posts", { method: "POST", body: JSON.stringify(data) }),
  generatePlatformPosts: (ideaId: string, platforms?: string[], linkUrl?: string) =>
    apiFetch<{ idea_id: string; posts: Post[] }>("/posts/generate", {
      method: "POST",
      body: JSON.stringify({ idea_id: ideaId, platforms, link_url: linkUrl }),
    }),
  approve: (id: string, scheduledAt?: string) =>
    apiFetch<Post>(`/posts/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ scheduled_at: scheduledAt }),
    }),
  reject: (id: string, reason?: string) =>
    apiFetch<Post>(`/posts/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  reschedule: (id: string, scheduledAt: string) =>
    apiFetch<Post>(`/posts/${id}/reschedule`, {
      method: "POST",
      body: JSON.stringify({ scheduled_at: scheduledAt }),
    }),
  retry: (id: string) =>
    apiFetch<Post>(`/posts/${id}/retry`, { method: "POST" }),
  publish: (id: string) =>
    apiFetch<Post>(`/posts/${id}/publish`, { method: "POST" }),
  update: (id: string, data: Partial<Post>) =>
    apiFetch<Post>(`/posts/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) =>
    apiFetch<void>(`/posts/${id}`, { method: "DELETE" }),
};

export const calendarApi = {
  getFeed: (params?: { start_date?: string; end_date?: string; platform?: string }) => {
    const sp = new URLSearchParams();
    if (params?.start_date) sp.set("start_date", params.start_date);
    if (params?.end_date) sp.set("end_date", params.end_date);
    if (params?.platform) sp.set("platform", params.platform);
    const qs = sp.toString() ? `?${sp.toString()}` : "";
    return apiFetch<CalendarFeedResponse>(`/calendar${qs}`);
  },
};

export const videoApi = {
  list: (status?: string) => {
    const qs = status ? `?status=${encodeURIComponent(status)}` : "";
    return apiFetch<VideoProject[]>(`/videos${qs}`);
  },
  get: (id: string) => apiFetch<VideoProject>(`/videos/${id}`),
  plan: (targetKeyword: string, additionalNotes?: string) =>
    apiFetch<VideoProject>("/videos/plan", {
      method: "POST",
      body: JSON.stringify({ target_keyword: targetKeyword, additional_notes: additionalNotes }),
    }),
  getUploadUrl: (id: string, filename = "video.mp4") =>
    apiFetch<{ upload_url: string; public_url: string; key: string }>(
      `/videos/${id}/upload-url?filename=${encodeURIComponent(filename)}`,
      { method: "POST" }
    ),
  publishYouTube: (id: string) =>
    apiFetch<VideoProject>(`/videos/${id}/publish-youtube`, { method: "POST" }),
  crossPostCaptions: (id: string) =>
    apiFetch<CrossPostCaptionsResponse>(`/videos/${id}/cross-post-captions`, { method: "POST" }),
  update: (id: string, data: Partial<VideoProject>) =>
    apiFetch<VideoProject>(`/videos/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) =>
    apiFetch<void>(`/videos/${id}`, { method: "DELETE" }),
};

// ─── Prompt 4: SEO, Tools, Launch & Reviews Types ────────────────────────────

export interface SEOTemplate {
  id: string;
  type: string;
  url_pattern: string;
  title_pattern: string;
  h1_pattern: string;
  body_prompt: string;
  created_at: string;
  updated_at: string;
}

export interface SEOPageItem {
  id: string;
  template_id?: string;
  slug: string;
  variables?: Record<string, any>;
  title?: string;
  meta_description?: string;
  content_json?: {
    h1: string;
    title: string;
    intro: string;
    sections: Array<{ heading: string; content: string }>;
    faq: Array<{ question: string; answer: string }>;
    comparison_table?: {
      competitor_name?: string;
      features?: Array<{ feature: string; globalreach: string; competitor: string }>;
    };
    cta?: {
      headline: string;
      subheadline: string;
      button_text: string;
      url: string;
    };
  };
  status: "draft" | "published" | "rejected";
  published_at?: string;
  quality_score?: number;
  created_at: string;
  updated_at: string;
}

export interface SEOPublicPage {
  slug: string;
  title: string;
  meta_description: string;
  content_json: Record<string, any>;
  schema_org: Record<string, any>;
  published_at?: string;
}

export interface SubjectRewrite {
  style: string;
  subject: string;
  why_it_works: string;
}

export interface SubjectGradeResult {
  score: number;
  reasons: string[];
  rewrites: SubjectRewrite[];
  input_stats: Record<string, any>;
  cta: {
    headline: string;
    subheadline: string;
    button_text: string;
    url: string;
  };
}

export interface EmailVerifyToolResult {
  email: string;
  syntax_ok: boolean;
  mx_ok: boolean;
  is_disposable: boolean;
  is_role: boolean;
  status: "valid" | "invalid" | "risky" | "locked";
  notes: string[];
  daily_checks_remaining: number;
  requires_email_unlock: boolean;
  cta: {
    headline: string;
    subheadline: string;
    button_text: string;
    url: string;
  };
}

export interface LaunchTaskItem {
  id: string;
  platform: "product_hunt" | "g2" | "capterra" | "reddit" | "indiehackers" | "other";
  title: string;
  description?: string;
  due_date?: string;
  status: "pending" | "in_progress" | "done";
  assets?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface ReviewRequestItem {
  id: string;
  user_email: string;
  platform: "g2" | "capterra";
  status: "pending" | "sent" | "reviewed";
  sent_at?: string;
  created_at: string;
}

// ─── Prompt 4 API Clients ───────────────────────────────────────────────────

export const seoApi = {
  getTemplates: () => apiFetch<SEOTemplate[]>("/seo/templates"),
  createTemplate: (data: {
    type: string;
    url_pattern: string;
    title_pattern: string;
    h1_pattern: string;
    body_prompt: string;
  }) => apiFetch<SEOTemplate>("/seo/templates", { method: "POST", body: JSON.stringify(data) }),
  deleteTemplate: (id: string) => apiFetch<void>(`/seo/templates/${id}`, { method: "DELETE" }),
  generate: (templateId: string, variablesList: Array<Record<string, any>>, csvContent?: string) =>
    apiFetch<SEOPageItem[]>("/seo/generate", {
      method: "POST",
      body: JSON.stringify({
        template_id: templateId,
        variables_list: variablesList,
        csv_content: csvContent,
      }),
    }),
  listPages: (params?: { status?: string; template_id?: string; min_quality_score?: number }) => {
    const sp = new URLSearchParams();
    if (params?.status) sp.set("status", params.status);
    if (params?.template_id) sp.set("template_id", params.template_id);
    if (params?.min_quality_score !== undefined) sp.set("min_quality_score", String(params.min_quality_score));
    const qs = sp.toString() ? `?${sp.toString()}` : "";
    return apiFetch<SEOPageItem[]>(`/seo/pages${qs}`);
  },
  batchPublish: (pageIds: string[]) =>
    apiFetch<{ success: boolean; published_count: number; requested_count: number }>("/seo/pages/batch-publish", {
      method: "POST",
      body: JSON.stringify({ page_ids: pageIds }),
    }),
  getPublicSlugs: async (): Promise<string[]> => {
    const res = await fetch(`${API_URL}/api/v1/public/seo/slugs`, { next: { revalidate: 3600 } });
    if (!res.ok) return [];
    return res.json();
  },
  getPublicPage: async (slug: string): Promise<SEOPublicPage | null> => {
    try {
      const res = await fetch(`${API_URL}/api/v1/public/seo/${slug}`, { next: { revalidate: 86400 } });
      if (!res.ok) return null;
      return res.json();
    } catch {
      return null;
    }
  },
};

export const toolsApi = {
  gradeSubject: async (subjectLine: string, industryContext?: string, emailCaptured?: string, utmSource?: string) => {
    const res = await fetch(`${API_URL}/api/v1/public/tools/subject-grader`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        subject_line: subjectLine,
        industry_context: industryContext,
        email_captured: emailCaptured,
        utm_source: utmSource || "free_tool",
      }),
    });
    if (!res.ok) throw new Error("Failed to grade subject line");
    return res.json() as Promise<SubjectGradeResult>;
  },
  verifyEmail: async (email: string, emailCaptured?: string, utmSource?: string) => {
    const res = await fetch(`${API_URL}/api/v1/public/tools/email-verifier`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email,
        email_captured: emailCaptured,
        utm_source: utmSource || "free_tool",
      }),
    });
    if (!res.ok) throw new Error("Failed to verify email address");
    return res.json() as Promise<EmailVerifyToolResult>;
  },
  getOverview: () =>
    apiFetch<{
      total_runs: number;
      emails_captured: number;
      conversion_rate_pct: number;
      by_tool: Record<string, number>;
    }>("/tools/overview"),
};

export const launchApi = {
  listTasks: (platform?: string, status?: string) => {
    const sp = new URLSearchParams();
    if (platform) sp.set("platform", platform);
    if (status) sp.set("status_filter", status);
    const qs = sp.toString() ? `?${sp.toString()}` : "";
    return apiFetch<LaunchTaskItem[]>(`/launch/tasks${qs}`);
  },
  createTask: (data: Partial<LaunchTaskItem>) =>
    apiFetch<LaunchTaskItem>("/launch/tasks", { method: "POST", body: JSON.stringify(data) }),
  updateTask: (id: string, data: Partial<LaunchTaskItem>) =>
    apiFetch<LaunchTaskItem>(`/launch/tasks/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteTask: (id: string) => apiFetch<void>(`/launch/tasks/${id}`, { method: "DELETE" }),
  generateAssets: (platform: string, taskType: string, customNotes?: string) =>
    apiFetch<{ platform: string; task_type: string; assets: Record<string, any> }>("/launch/generate-assets", {
      method: "POST",
      body: JSON.stringify({ platform, task_type: taskType, custom_notes: customNotes }),
    }),
};

export const reviewsApi = {
  sendRequest: (userEmail: string, platform: "g2" | "capterra") =>
    apiFetch<ReviewRequestItem>("/reviews/request", {
      method: "POST",
      body: JSON.stringify({ user_email: userEmail, platform }),
    }),
  listRequests: () => apiFetch<ReviewRequestItem[]>("/reviews"),
};


