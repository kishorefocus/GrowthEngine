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

// ─── Health API ──────────────────────────────────────────────────────────────

export const healthApi = {
  check: () =>
    fetch(`${API_URL}/healthz`)
      .then((r) => r.json() as Promise<HealthResponse>)
      .catch(() => null),
};
