# GlobalReach Growth Engine — Build Progress

## Prompt 1 — Foundation, Schema & Analytics ✅

### Backend
- [x] Extended `config.py` with all env vars (JWT, Anthropic, email, social, storage, etc.)
- [x] `models/base.py` — UUID PK + TimestampMixin
- [x] `models/auth.py` — users, social_accounts, brand_profile
- [x] `models/leads.py` — icps, leads, suppression_list, campaigns, sequences, sequence_steps, email_messages, replies
- [x] `models/social.py` — content_ideas, posts, video_projects
- [x] `models/seo.py` — seo_templates, seo_pages, tool_usages
- [x] `models/launch.py` — launch_tasks, review_requests
- [x] `models/analytics.py` — link_clicks, signup_attributions, audit_log
- [x] `core/jwt.py` — create/verify access + refresh tokens, hash_refresh_token
- [x] `core/deps.py` — get_current_user, require_owner FastAPI dependencies
- [x] `services/crypto.py` — Fernet encrypt/decrypt for OAuth tokens
- [x] `services/utm.py` — UTM link builder + CHANNELS registry
- [x] `services/dryrun.py` — dry_run_guard wrapping all outbound actions
- [x] `services/ratelimit.py` — Redis sliding-window rate limiter
- [x] `services/claims_guard.py` — AI output validation (no guarantees/fake testimonials)
- [x] `services/ai.py` — Anthropic client, brand context injection, Pydantic validation, retry
- [x] `services/audit.py` — immutable audit log writer
- [x] `providers/email.py` — EmailProvider interface + StubEmailProvider + ResendEmailProvider
- [x] `providers/social.py` — SocialPublisher interface + Stubs
- [x] `providers/video.py` — VideoGenerator interface + Stub
- [x] `routers/auth.py` — register (owner-only first), login, refresh (rotation + reuse detection), /me
- [x] `routers/brand.py` — GET/PUT /api/v1/brand
- [x] `routers/analytics.py` — GET /r/{code} short-link redirect, GET /analytics/overview
- [x] `routers/webhooks.py` — POST /webhooks/signup (HMAC-signed)
- [x] `main.py` — full app wiring, CORS, Sentry, structured logging, /healthz
- [x] `worker/main.py` — ARQ WorkerSettings, cron registry
- [x] `worker/jobs/analytics.py` — sync_analytics_rollup nightly job
- [x] `prompts/cold_email.txt` — AI prompt template
- [x] `tests/test_auth.py` — register, login, JWT refresh rotation, auth guard, /me
- [x] `tests/test_services.py` — UTM builder, claims guard, HMAC webhook

### Frontend
- [x] `lib/api-client.ts` — typed API client, auto-refresh on 401
- [x] `lib/hooks.ts` — TanStack Query hooks (auth, brand, analytics)
- [x] `middleware.ts` — Next.js Edge auth guard for /admin/*
- [x] `app/providers.tsx` — QueryClient + ThemeProvider + Toaster
- [x] `app/layout.tsx` — root layout with Providers
- [x] `app/admin/login/page.tsx` — split-panel login with DRY_RUN notice
- [x] `app/admin/register/page.tsx` — owner-only registration
- [x] `app/admin/layout.tsx` — sidebar + top bar shell
- [x] `app/admin/dashboard/page.tsx` — full KPI cards + channel chart + top posts/SEO
- [x] `app/admin/settings/page.tsx` — brand profile form
- [x] `components/sidebar.tsx` — all 11 sections with coming-soon badges
- [x] `components/top-bar.tsx` — dynamic title + DRY_RUN indicator
- [x] `components/coming-soon.tsx` — reusable empty state
- [x] `app/admin/leads/page.tsx` — Prompt 2 placeholder
- [x] `app/admin/campaigns/page.tsx` — Prompt 2 placeholder
- [x] `app/admin/inbox/page.tsx` — Prompt 2 placeholder
- [x] `app/admin/calendar/page.tsx` — Prompt 3 placeholder
- [x] `app/admin/ideas/page.tsx` — Prompt 3 placeholder
- [x] `app/admin/video/page.tsx` — Prompt 3 placeholder
- [x] `app/admin/connections/page.tsx` — Prompt 3 placeholder
- [x] `app/admin/seo/page.tsx` — Prompt 4 placeholder
- [x] `app/admin/launch/page.tsx` — Prompt 4 placeholder
- [x] `public/gr-attribution.js` — attribution snippet for main product

### Docs
- [x] `docs/ARCHITECTURE.md`
- [x] `docs/PROGRESS.md`
- [x] `README.md`

---

## Prompt 2 — Leads & Email ✅

- [x] Lead import (CSV with column mapping, GlobalReach API via dogfooding)
- [x] ICP builder UI (CRUD with industry, geography, company size, titles, keywords)
- [x] Email verification (syntax, MX check, disposable domain blocklist, role account detection)
- [x] Suppression list UI (import, export, search, remove with audit, pre-send enforcement)
- [x] Campaign builder (sequences, steps, delays, spam-score heuristic)
- [x] AI Personalization with Claude 3.5 Sonnet, claims guard check, and live preview
- [x] ARQ worker: `send_due_emails` (respects daily_limit, sending_window in recipient tz, jitter, suppression)
- [x] ARQ worker: `check_campaign_health` (auto-pauses on >5% bounce or >0.3% complaint)
- [x] Inbound webhook & reply classification (`reply_classify` → interested/not_now/unsubscribe/etc.)
- [x] Inbox page with AI reply suggestions and 1-click handle/suppress actions
- [x] Unsubscribe handler (`GET /u/{token}`) with signed HMAC tokens & confirmation page
- [x] Compliant footer with physical address, one-click unsubscribe, and List-Unsubscribe headers
- [x] Sending Domain Health (SPF, DKIM, DMARC DNS resolution) & 6-week warm-up ramp card
- [x] Pytest suite (28/28 passed) covering suppression, stop rules, daily limits, auto-pause, tokens, and webhooks


---

## Prompt 3 — Social & Video ✅

- [x] Social OAuth connections (X, LinkedIn, Meta, YouTube) with Fernet encrypted tokens in `social_accounts`
- [x] Content idea generator (`POST /ideas/generate`) across 5 pillars: how-to, build-in-public, competitor alternatives, industry lead lists, tips & stats
- [x] Platform-adapted post drafting (`POST /posts/generate`) with `social_adapt` template:
  - X: Hook + thread option (<280 chars per tweet)
  - LinkedIn: 800–1,300 chars, line breaks, closing discussion question
  - Instagram: Caption, 5–8 hashtags, carousel slide text, image prompt
  - Facebook: Concise post with link
- [x] Strict UTM link wrapping via `services/utm.py` and short links via `/r/{code}`
- [x] `claims_guard` validation on all generated social text (no guarantees/fake testimonials)
- [x] Human approval queue state machine (`draft` → `pending_approval` → `approved` → `scheduled` → `published` | `failed` | `rejected`) with `audit_log` entries
- [x] Visual Content Calendar UI with week & month views, time rescheduling, and side-by-side platform preview mockups
- [x] Best-time posting suggestions heuristic (starts with weekday morning heuristic, becomes data-driven with ≥30 posts)
- [x] Video Studio pipeline (`POST /videos/plan`): keyword input, 60s Shorts script, 5–8m YouTube outline, screen-recording shot list, description with chapters & UTM, tags, thumbnail prompt
- [x] Cloudflare R2 / S3 signed asset upload URLs (`POST /videos/{id}/upload-url`)
- [x] YouTube Data API v3 publishing (`POST /videos/{id}/publish-youtube`, private until owner approves)
- [x] Cross-post caption variants for Instagram Reels, Facebook Reels, and LinkedIn video
- [x] Official publishers:
  - `XPublisher`: API v2 (`POST /2/tweets`) with thread support
  - `LinkedInPublisher`: Posts API for organization page
  - `InstagramPublisher`: Graph API media container create + publish
  - `FacebookPublisher`: Page feed API
  - Rate limiting handling, backoff retries, error logging to `posts.error`, and `dry_run_guard`
- [x] Background ARQ worker jobs:
  - `publish_due_posts` (runs every 1 minute)
  - `generate_weekly_content_batch` (Sunday 18:00)
  - `refresh_social_tokens` (hourly token expiry check and refresh)
- [x] Dashboard updates: wired "Items Awaiting Approval" card, social rows in Channel Attribution, and top posts
- [x] Pytest suite (37/37 tests passed) covering UTM wrapping, length limits, approval state machine, backoff, tokens, and video pipeline

---

## Prompt 4 — SEO, Tools, Launch Hub & Hardening ✅

- [x] SEO template builder UI (`/admin/seo`) with type, URL pattern, title pattern, H1, and body prompt
- [x] Bulk programmatic page generation with Claude 3.5 Sonnet (`POST /seo/generate`) via variable combinations & CSV upload
- [x] Quality score filtering (`quality_gate.py`): enforces >600 words, similarity <70%, niche/local detail check, and `claims_guard`
- [x] Next.js public routes with 24h ISR:
  - `/find-leads/[industry]/[city]`
  - `/alternatives/[competitor]/[niche]`
  - `/use-cases/[slug]`
- [x] Dynamic sitemap generation (`/sitemap.xml`) with 5,000 URL per file capping & `/robots.txt`
- [x] Free lead-magnet tools:
  - Subject Line Grader (`/tools/subject-line-grader`): 0-100 deliverability score, spam trigger analysis, 3 AI rewrites
  - Single Email Verifier (`/tools/email-verifier`): syntax, MX DNS resolution, disposable domain check, role account check
- [x] Tool usage tracking with email capture unlock & UTM parameter tracking (`tool_usages` table)
- [x] Launch Hub (`/admin/launch`): Kanban board across Product Hunt, G2, Capterra, Reddit, and IndieHackers with status tracking
- [x] AI Launch Asset Generator: Reddit build-journey posts (no link drops, technical lessons), PH maker comments, IH milestone posts, G2 listings
- [x] Review request campaigns (`POST /reviews/request`): sends direct G2/Capterra review request emails, audit logged, dry-run protected
- [x] ARQ worker jobs confirmed & scheduled (all 8 jobs idempotent):
  1. `send_due_emails` (1 min)
  2. `publish_due_posts` (1 min)
  3. `refresh_social_tokens` (hourly)
  4. `generate_weekly_content_batch` (Sunday 18:00)
  5. `process_email_events` (continuous)
  6. `check_campaign_health` (15 min)
  7. `sync_analytics_rollup` (nightly at 2:00 UTC)
  8. `seo_publish_batch` (weekly)
- [x] Security & Hardening: rate limiting on all public endpoints (`ratelimit.py`), CORS locked, HMAC webhook verification, Fernet token encryption at rest
- [x] Pytest suite (46/46 tests passed) across all modules
- [x] Next.js production build cleanly compiled (31 static pages, SSG, and ISR routes)
