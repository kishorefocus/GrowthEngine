# GlobalReach Growth Engine — Architecture

> **Internal admin app** for GlobalReach. Separate from the main product at https://www.getyourclientsb2b.com.
> Gets founders, sales teams and agencies worldwide to visit the site, sign up and use GlobalReach.

---

## Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 14+ (App Router, TypeScript), Tailwind, shadcn/ui, TanStack Query |
| Backend API | FastAPI (Python 3.11), SQLAlchemy 2 + Alembic, Pydantic v2 |
| Database | PostgreSQL on Railway |
| Queue / Scheduler | Redis + ARQ (Railway service 2) |
| Email | Resend (swappable via EmailProvider interface) |
| AI | Anthropic Claude API |
| Auth | Email+password (argon2) + Google OAuth; JWT access (15 min) + rotating refresh tokens |
| Storage | Cloudflare R2 / S3-compatible |
| Observability | Sentry on both ends, structured JSON logs |

---

## Folder Layout

```
GrowthEngine/
  frontend/                    # Next.js 14 (Vercel)
    app/
      (public)/                # Public programmatic SEO & Free Lead-Magnet Tools
        find-leads/[industry]/[city]/page.tsx
        alternatives/[competitor]/[niche]/page.tsx
        use-cases/[slug]/page.tsx
        tools/subject-line-grader/page.tsx
        tools/email-verifier/page.tsx
        layout.tsx
      admin/                   # Protected admin shell (auth-gated via middleware)
        dashboard/             # High-level KPIs, channel attribution, health alerts
        leads/                 # Lead search, CSV import, ICP builder, suppression
        campaigns/             # Sequences, step builder, spam score, AI preview
        inbox/                 # Prospect replies, intent classification, quick replies
        calendar/              # Visual content calendar, approval queue with mockups
        ideas/                 # 5-pillar idea generator (20 batch) & platform drafts
        video/                 # Keyword video planning, R2 upload, YouTube publish
        connections/           # OAuth manager (X, LinkedIn, Meta, YouTube)
        seo/                   # SEO template editor, CSV combination uploader, quality gate
        launch/                # Kanban launch checklists (PH, G2, Capterra, Reddit, IH)
        settings/              # Brand profile, compliance address, tone directives
        login/, register/
      sitemap.ts, robots.ts    # Dynamic sitemap (5k URL cap) and robots.txt
    components/                # Sidebar, TopBar, SEO page renderer, preview mockups
    lib/
      api-client.ts            # Typed fetch wrapper, token refresh, API client SDK
      hooks.ts                 # TanStack Query hooks for all resources
    public/
      gr-attribution.js        # Attribution snippet for main product
    middleware.ts              # Auth guard (Edge runtime)

  backend/                     # FastAPI (Railway service 1)
    app/
      core/
        config.py              # Env vars via pydantic-settings
        database.py            # Async SQLAlchemy engine + session
        jwt.py                 # JWT access/refresh rotation & hashing
        deps.py                # FastAPI auth & role dependencies
      models/                  # All 20+ SQLAlchemy models (full schema)
        base.py, auth.py, leads.py, social.py, seo.py, launch.py, analytics.py
      routers/                 # FastAPI routers
        auth.py, brand.py, analytics.py, webhooks.py
        icps.py, leads.py, campaigns.py, email_events.py
        connections.py, ideas.py, posts.py, videos.py
        seo.py, tools.py, launch.py, reviews.py
      services/                # Shared infrastructure
        ai.py                  # Anthropic Claude wrapper, structured JSON
        claims_guard.py        # Prohibited claims / guarantees validator
        quality_gate.py        # Programmatic SEO quality gate (>600w, <70% sim)
        email_verify.py        # Syntax, MX lookup, disposable, role checks
        domain_health.py       # Live SPF, DKIM, DMARC DNS resolution
        ratelimit.py           # Redis sliding-window rate limiter
        crypto.py              # Fernet encrypt/decrypt for OAuth tokens
        utm.py                 # UTM link builder & short link redirect
        dryrun.py              # DRY_RUN guard wrapping all outbound actions
        storage.py             # Cloudflare R2 / S3 signed upload URLs
        audit.py               # Immutable audit log writer
      providers/               # Swappable providers
        email.py               # EmailProvider (Resend + Stub)
        social.py              # SocialPublisher (X, LinkedIn, IG, FB, YouTube + Stubs)
        video.py               # VideoGenerator (Stub)
      prompts/                 # AI prompt templates (.txt files)
    worker/                    # ARQ workers (Railway service 2)
      main.py                  # WorkerSettings, 8 scheduled cron jobs
      jobs/
        analytics.py           # sync_analytics_rollup (nightly)
        email.py               # send_due_emails, check_campaign_health, process_email_events
        social.py              # publish_due_posts, generate_weekly_content_batch, refresh_social_tokens
        seo.py                 # seo_publish_batch (weekly)
    tests/                     # pytest suite (46 tests, all passing)

  docs/
    ARCHITECTURE.md            # ← this file
    PROGRESS.md                # Build checklist
  docker-compose.yml           # Local dev: PostgreSQL + Redis + API + Frontend
```

---

## Naming Conventions

- **Models**: `PascalCase` classes, `snake_case` table names
- **Routers**: `snake_case` file names, grouped by domain
- **Services**: `verb_noun` functions (e.g. `encrypt_token`, `write_audit_log`)
- **API routes**: RESTful under `/api/v1/`, public routes documented with `(public)` comment
- **Frontend components**: `PascalCase.tsx`, `kebab-case` filenames
- **Query keys**: centralised in `lib/hooks.ts → queryKeys`

---

## Interfaces

### EmailProvider
```python
class EmailProvider(ABC):
    async def send(message: EmailMessage) -> SendResult: ...
    async def check_bounces() -> list[str]: ...
```

### SocialPublisher
```python
class SocialPublisher(ABC):
    async def publish(post: PostPayload) -> PublishResult: ...
```

### VideoGenerator
```python
class VideoGenerator(ABC):
    async def generate(spec: VideoSpec) -> VideoResult: ...
```

---

## Full Database Schema

Every table has `id` (UUID), `created_at`, `updated_at`.

### Auth & Settings
| Table | Key Fields |
|---|---|
| `users` | email, password_hash (argon2), role (owner\|editor), refresh_token_hash |
| `social_accounts` | platform, handle, encrypted_access_token, encrypted_refresh_token, expires_at |
| `brand_profile` | product_name, one_liner, value_props (jsonb), tone, banned_phrases (jsonb), website_url, physical_address |

### Leads & Outreach
| Table | Key Fields |
|---|---|
| `icps` | name, industry, geography, company_size, titles (jsonb), keywords (jsonb) |
| `leads` | email, first_name, last_name, company, title, source, verification_status, icp_id, status |
| `suppression_list` | email_or_domain, reason, added_at — checked before every send |
| `campaigns` | name, icp_id, status, daily_limit, sending_window (jsonb), timezone_mode |
| `sequences` | campaign_id |
| `sequence_steps` | sequence_id, step_number, delay_days, subject_template, body_template, ai_personalize |
| `email_messages` | lead_id, campaign_id, step_id, provider_message_id, status, sent_at, tracking_token |
| `replies` | message_id, body, classification, handled |

### Social & Video
| Table | Key Fields |
|---|---|
| `content_ideas` | topic, pillar, source (ai\|manual\|seo_gap), status |
| `posts` | idea_id, platform, body, media_urls, utm (jsonb), status, scheduled_at, external_post_id |
| `video_projects` | title, target_keyword, script, shot_list, youtube_title, tags, status, asset_url |

### SEO & Tools
| Table | Key Fields |
|---|---|
| `seo_templates` | type (industry_city\|alternative\|use_case), url_pattern, title_pattern, body_prompt |
| `seo_pages` | template_id, slug, variables, title, content_json, status, quality_score |
| `tool_usages` | tool_slug, input_hash, email_captured, utm (jsonb) |

### Launch & Reviews
| Table | Key Fields |
|---|---|
| `launch_tasks` | platform, title, description, due_date, status, assets (jsonb) |
| `review_requests` | user_email, platform, sent_at, status |

### Analytics
| Table | Key Fields |
|---|---|
| `link_clicks` | utm_source, utm_medium, utm_campaign, utm_content, visitor_id, short_code, landed_at |
| `signup_attributions` | user_email, first_touch (jsonb), last_touch (jsonb), signed_up_at |
| `audit_log` | user_id, action, entity, entity_id, meta (jsonb) |

---

## Security Guardrails (apply to all 4 prompts)

- **Official APIs only** — no browser bots, no scraping LinkedIn, no automated DMs to strangers
- **Social posting** via official APIs: X API, LinkedIn Posts API, Meta Graph API, YouTube Data API — all through human approval queue
- **Cold outreach** is email only, with unsubscribe link, physical address, honest sender identity, and suppression enforcement (CAN-SPAM, GDPR, CASL)
- **Email Unsubscribe**: Signed URL-safe HMAC tokens (`UNSUBSCRIBE_SECRET` via `itsdangerous`), public `GET /u/{token}` endpoint, automatic suppression, and header inclusion (`List-Unsubscribe`, `List-Unsubscribe-Post`)
- **Automated Safety Monitoring**: Background worker checks health every 15 min; auto-pauses any campaign exceeding 5.0% bounce rate or 0.3% complaint rate with audit logging
- **Sequence Stop Rules**: Sequences stop advancing immediately when a lead replies, bounces, unsubscribes, or signs up
- **Product Hunt, G2, Capterra** — no public posting APIs; app provides checklists and assets; human submits
- **Reddit and IndieHackers** — posts drafted, posted manually
- **Human in the loop everywhere** — AI drafts, owner approves, system schedules
- **DRY_RUN=true by default** — sends and posts are logged instead of executed until owner flips it
- **Parameterized queries only**, CORS locked to Vercel domain, Sentry on both ends, secrets only in Railway/Vercel vars
- **Fernet encryption** for all stored OAuth tokens, never logged
- **Claims guard** on every AI output — rejects guarantees, fake testimonials, unverifiable statistics

---

## Environment Variables

See `backend/.env.example` for the full list. Key variables:

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL asyncpg connection string |
| `REDIS_URL` | Redis connection string |
| `JWT_SECRET` | ≥32 char secret for JWT signing |
| `ENCRYPTION_KEY` | Fernet key for OAuth token encryption |
| `DRY_RUN` | `true` by default — set `false` to enable live sends |
| `ANTHROPIC_API_KEY` | Claude API key |
| `RESEND_API_KEY` | Resend email sending API key |
| `SENDING_DOMAIN` | Cold email sending domain (NOT the main domain) |
| `SIGNUP_WEBHOOK_SECRET` | HMAC secret for signup webhook from main product |
