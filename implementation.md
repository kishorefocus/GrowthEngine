GlobalReach Growth Engine: Full-Stack Build Prompt
Four self-contained prompts, each sized to fit one IDE agent session. Paste them in order, one per fresh chat, and confirm each works before starting the next. Nothing from the original prompt was dropped: every table, endpoint, screen, job and guardrail sits in exactly one part, and Part 1 holds the full database schema so later parts only reference it.
Part 1 also makes the agent write docs/ARCHITECTURE.md and docs/PROGRESS.md in your repo. Parts 2 to 4 tell the agent to read those files first, so you never re-paste shared context.
Part
Scope
Original sections covered
1. Foundation
Monorepo, auth, full schema, brand profile, analytics and attribution, admin shell, dashboard, security base
0, 1, 2, 3, 4, 5.1, 5.2, 5.10, 8
2. Leads and email
Lead engine, verification, campaigns, scheduler, unsubscribe, inbox
5.3, 5.4, admin pages 2 to 4, email jobs
3. Social and video
Content studio, publishers, calendar, video studio, connections
5.5, 5.6, admin pages 6 to 8 (calendar, ideas, video), connections
4. SEO, tools, launch
Programmatic SEO, free tools, launch hub, review requests, hardening, acceptance
5.7, 5.8, 5.9, public routes, SEO manager, launch hub, 10, 11, 13
Prompt 1 of 4: Foundation, schema and analytics
Paste this into a fresh agent session.
Role and goal
You are a senior full-stack engineer. Build GlobalReach Growth Engine, an internal admin app (separate from the main product at https://www.getyourclientsb2b.com) that gets founders, sales teams and agencies worldwide to visit the site, sign up and use GlobalReach. The full app is built across 4 prompts. This prompt builds the foundation everything else plugs into.
The finished app does five jobs: (1) dogfood cold email outreach, (2) social content automation, (3) video content planning, (4) programmatic SEO plus free lead-magnet tools, (5) launch and review tracking for Product Hunt, G2, Capterra, Reddit and IndieHackers. Every channel is attributed with UTM parameters so the dashboard shows which one produced real signups.
Guardrails (apply to all 4 prompts)
• Official APIs only. No browser bots, no scraping LinkedIn, no automated Instagram or Facebook DMs to strangers.
• Social posting goes through official APIs: X API, LinkedIn Posts API (company page), Meta Graph API (Instagram Business and Facebook Page), YouTube Data API. Everything passes a human approval queue by default.
• Cold outreach is email only, with unsubscribe link, physical address, honest sender identity and suppression enforcement (CAN-SPAM, GDPR, CASL).
• Product Hunt, G2, Capterra have no public posting APIs. The app provides checklists, assets and review campaigns; a human submits.
• Reddit and IndieHackers posts are drafted by the app and posted manually.
• Human in the loop everywhere. AI drafts, the owner approves, the system schedules.
• DRY_RUN=true by default: sends and posts are logged instead of executed until the owner flips it.
Tech stack and deployment
Layer
Choice
Frontend
Next.js 14+ (App Router, TypeScript), Tailwind, shadcn/ui, TanStack Query, on Vercel (custom domain already bought)
Backend API
FastAPI (Python 3.11), SQLAlchemy 2 + Alembic, Pydantic v2, on Railway
Database
PostgreSQL on Railway
Queue and scheduler
Redis (Railway) + ARQ or Celery, as a separate Railway service
Email sending
Resend, Postmark or Amazon SES behind a swappable provider interface
AI
Anthropic API (Claude)
Auth
Email and password plus Google OAuth, JWT access and refresh tokens, roles owner and editor
Storage
Cloudflare R2 or S3 for video and image assets
Observability
Sentry on both ends, structured JSON logs
Monorepo layout:
growth-engine/
  apps/web/            # Next.js (Vercel)
  apps/api/            # FastAPI (Railway service 1)
  apps/worker/         # ARQ workers + scheduler (Railway service 2)
  packages/shared/     # shared types, generated OpenAPI client
  docs/                # ARCHITECTURE.md, PROGRESS.md
Generate the TypeScript API client from FastAPI's OpenAPI schema so types stay in sync.
Deployment notes
• Vercel hosts both the public SEO pages (under /(public)) and the admin app (under /admin, behind auth). Free tools can also run on a subdomain such as tools.getyourclientsb2b.com.
• Railway: Dockerfile, health endpoint /healthz, CORS limited to the Vercel domain, Alembic migrations on deploy.
• Cold email will use a separate sending domain (for example getyourclientsb2b.co, never the main domain) with SPF, DKIM, DMARC and warm-up. Prompt 2 builds that part.
Environment variables
Create .env.example for every service with exactly these:
# Core
DATABASE_URL=
REDIS_URL=
JWT_SECRET=
FRONTEND_URL=https://www.getyourclientsb2b.com
API_URL=
ENCRYPTION_KEY=            # Fernet key for encrypting stored OAuth tokens
DRY_RUN=true

# AI
ANTHROPIC_API_KEY=

# Email
EMAIL_PROVIDER=resend
RESEND_API_KEY=
SENDING_DOMAIN=
PHYSICAL_ADDRESS=          # required in email footer
UNSUBSCRIBE_SECRET=

# Social (official APIs)
X_CLIENT_ID= X_CLIENT_SECRET=
LINKEDIN_CLIENT_ID= LINKEDIN_CLIENT_SECRET=
META_APP_ID= META_APP_SECRET=
GOOGLE_CLIENT_ID= GOOGLE_CLIENT_SECRET=   # YouTube + login

# Storage
S3_ENDPOINT= S3_BUCKET= S3_KEY= S3_SECRET=

# GlobalReach dogfooding
GLOBALREACH_API_URL=
GLOBALREACH_API_KEY=

# Signup webhook from the main product
SIGNUP_WEBHOOK_SECRET=
Database schema (create ALL tables now, in Alembic migrations)
Every table has id (UUID), created_at, updated_at. Later prompts only add logic, not tables.
Auth and settings
• users (email, password_hash, role)
• social_accounts (platform, handle, external_id, encrypted_access_token, encrypted_refresh_token, expires_at, status)
• brand_profile (product_name, one_liner, value_props jsonb, tone, banned_phrases jsonb, website_url, physical_address)
Leads and outreach
• icps (name, industry, geography, company_size, titles jsonb, keywords jsonb)
• leads (email, first_name, last_name, company, title, website, country, industry, source, verification_status, icp_id, status: new|queued|contacted|replied|signed_up|bounced|unsubscribed)
• suppression_list (email or domain, reason, added_at), checked before every send
• campaigns (name, icp_id, status, daily_limit, sending_window jsonb, timezone_mode)
• sequences (campaign_id) and sequence_steps (sequence_id, step_number, delay_days, subject_template, body_template, ai_personalize bool)
• email_messages (lead_id, campaign_id, step_id, provider_message_id, status: scheduled|sent|delivered|opened|clicked|replied|bounced|complained, sent_at, tracking_token)
• replies (message_id, body, classification: interested|not_now|not_interested|unsubscribe|out_of_office|other, handled bool)
Social and video
• content_ideas (topic, pillar, source: ai|manual|seo_gap, status)
• posts (idea_id, platform, body, media_urls jsonb, link_url, utm jsonb, status: draft|pending_approval|approved|scheduled|published|failed|rejected, scheduled_at, published_at, external_post_id, error)
• video_projects (title, target_keyword, script, shot_list jsonb, caption, youtube_title, youtube_description, tags jsonb, thumbnail_prompt, status, asset_url, youtube_video_id)
SEO and tools
• seo_templates (type: industry_city|alternative|use_case, url_pattern, title_pattern, h1_pattern, body_prompt)
• seo_pages (template_id, slug, variables jsonb, title, meta_description, content_json, status: draft|published, published_at, quality_score)
• tool_usages (tool_slug, input_hash, email_captured, utm jsonb)
Launch and reviews
• launch_tasks (platform: product_hunt|g2|capterra|reddit|indiehackers|other, title, description, due_date, status, assets jsonb)
• review_requests (user_email, platform, sent_at, status)
Analytics
• link_clicks (utm_source, utm_medium, utm_campaign, utm_content, visitor_id, landed_at)
• signup_attributions (user_email, first_touch jsonb, last_touch jsonb, signed_up_at), populated by a webhook from the main product
• audit_log (user_id, action, entity, entity_id, meta jsonb)
Backend to build now (FastAPI, routes under /api/v1)
Auth. POST /auth/register (first user becomes owner, then registration locks), POST /auth/login, POST /auth/refresh, GET /auth/google/callback. Argon2 hashing, 15-minute JWT access tokens, rotating refresh tokens. All routes are JWT-protected except those marked (public).
Brand profile. GET/PUT /brand. Every AI prompt in later parts injects this as system context so tone stays consistent.
Analytics and attribution.
• GET /r/{code} (public): short-link redirect that logs the click in link_clicks and appends UTM parameters.
• A small JS snippet for the main website that stores UTM parameters and a visitor_id in first-party storage and sends them with the signup event. Ship it as apps/web/public/gr-attribution.js with install instructions in the README.
• POST /webhooks/signup (public, HMAC-signed with SIGNUP_WEBHOOK_SECRET): receives signup events from the main GlobalReach product and writes signup_attributions.
• GET /analytics/overview: visits, signups, conversion rate by channel (email, X, LinkedIn, Instagram, Facebook, YouTube, SEO, tools, Product Hunt, Reddit), top posts, top SEO pages, cost per signup, email metrics (sent, reply rate, bounce rate). Return zeros for channels that do not exist yet.
Shared infrastructure (later prompts import these, so build them properly):
• services/ai.py: Anthropic client wrapper. Injects the brand profile, returns strict JSON validated by Pydantic, retries once on parse failure. Prompt templates live in apps/api/prompts/.
• services/claims_guard.py: final check that rejects generated text containing unverifiable numbers, fake testimonials or guarantees such as "guaranteed 10x leads".
• services/ratelimit.py: Redis-based rate limiter used on all public endpoints.
• services/crypto.py: Fernet encrypt and decrypt for social tokens. Never log tokens.
• services/utm.py: builds UTM-tagged links: utm_source, utm_medium, utm_campaign, utm_content.
• services/dryrun.py: a helper every outbound action calls; when DRY_RUN=true it logs instead of executing.
• Provider interfaces with stub implementations: EmailProvider.send(...), SocialPublisher.publish(post) -> external_id, VideoGenerator. Later prompts fill them in.
• Audit log writer for approvals, sends and deletions.
• apps/worker: ARQ app, job registry, retry and idempotency helpers. Implement the nightly job sync_analytics_rollup now; later prompts register the rest.
Security. Validate all input, parameterized queries only, CORS locked to the Vercel domain, Sentry, structured logs, webhook signature verification, secrets only in Railway and Vercel variables.
Frontend to build now (/admin, protected)
• Login page (email and password, Google) and registration for the first owner only.
• App shell: sidebar, top bar, light and dark mode, responsive, skeleton loaders, toasts, optimistic updates, empty states with next-step guidance, accessible forms.
• Sidebar lists all 11 admin sections; sections not yet built render a "coming in Prompt N" empty state so routes never change later: Dashboard, Leads, Campaigns, Inbox, Content calendar, Ideas and generator, Video studio, SEO manager, Launch hub, Connections, Settings.
• Dashboard (fully working): KPI cards (visits, signups, conversion rate, emails sent, replies), channel attribution chart, today's tasks, items awaiting approval (empty for now).
• Settings (partial): brand profile form, suppression list viewer (read, search, add, remove with audit), team users (invite editor, change role).
• Typed API client generated from OpenAPI, TanStack Query hooks, auth guard with refresh handling.
Tests
pytest for auth, JWT refresh rotation, HMAC webhook verification, UTM builder, claims guard, rate limiter. Playwright for login and dashboard load. Mock external APIs.
Write these files before you finish
• docs/ARCHITECTURE.md: stack, folder layout, naming conventions, interfaces, env vars, the full schema summary, and the guardrails above (copied in full).
• docs/PROGRESS.md: checklist of what is done and what Prompts 2, 3 and 4 will build.
• README with local setup, Vercel and Railway deploy steps and the attribution snippet install steps.
Definition of done
1. All migrations run and every table above exists.
2. I can register as owner, log in, edit the brand profile and see the dashboard.
3. A short link click and a signed webhook event both appear in the analytics overview.
4. Everything deploys to Vercel and Railway.
5. Tests pass.
Before coding, summarize your plan and list any assumptions or missing credentials. Stop when done and report what to paste next.