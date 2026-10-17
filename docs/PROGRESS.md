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

## Prompt 3 — Social & Video (TODO)

- [ ] Social OAuth connections (X, LinkedIn, Meta, YouTube)
- [ ] Content idea generator (AI + SEO gap analysis)
- [ ] Post drafting with claims guard
- [ ] Human approval queue
- [ ] Scheduled publishing via ARQ
- [ ] Content calendar UI (drag-and-drop)
- [ ] Video project pipeline (keyword → script → shot list → caption)
- [ ] YouTube upload via Data API
- [ ] X Publisher (API v2 create_tweet)
- [ ] LinkedIn Publisher (Posts API)
- [ ] Meta Publisher (Graph API)

---

## Prompt 4 — SEO, Tools & Launch (TODO)

- [ ] SEO template builder UI
- [ ] Bulk page generation with AI
- [ ] Quality score filtering
- [ ] Next.js public routes: `/(public)/[slug]`
- [ ] Sitemap generation
- [ ] Free tool pages at `tools.getyourclientsb2b.com`
- [ ] Tool usage tracking (email capture + UTM)
- [ ] Launch Hub checklists (PH, G2, Capterra, Reddit, IH)
- [ ] Review request campaigns
- [ ] Analytics rollup table (Prompt 1 job writes to it)
- [ ] Full acceptance testing (Playwright: login, dashboard, brand edit, webhook)
- [ ] Hardening: rate limit all public endpoints, CORS final audit
