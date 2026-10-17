# GlobalReach Growth Engine — Standard Operating Procedures & Operations Manual

> **Document Classification:** Internal SOP & Runbook  
> **Target Audience:** Business Owner, Growth Lead, Marketing Ops & SDR Team  
> **Stack:** Next.js 14 (Vercel) · FastAPI (Railway) · PostgreSQL 16 · Redis 7 · ARQ Worker · Claude 3.5 Sonnet  
> **Safety Default:** `DRY_RUN=true` (Simulation mode active until owner flips to live)  
> **PDF Version Available at:** [`GlobalReach_Growth_Engine_Operations_Manual.pdf`](../GlobalReach_Growth_Engine_Operations_Manual.pdf) and [`docs/OPERATIONS_MANUAL.pdf`](OPERATIONS_MANUAL.pdf)

---

## Executive Summary & Core Operating Philosophy

The **GlobalReach Growth Engine** is an automated outbound acquisition and content platform designed to acquire customers for [GlobalReach](https://www.getyourclientsb2b.com). It unifies five key acquisition pipelines:
1. **Cold Email Outreach Engine** (ICP modeling, lead verification, 3-step sequence scheduler, deliverability guardrails, automated suppression).
2. **Social Content Studio** (Multi-platform content generation for X, LinkedIn, Instagram, Facebook with automated UTM link tracking).
3. **Video Content Studio** (Target keyword ideation, 60–90 second screencast scripts with visual stage directions, publish metadata, and YouTube pipeline).
4. **Programmatic SEO & Free Lead Magnets** (Scalable programmatic landing pages, quality gate scoring, Subject Line Grader, and Free Email Verifier).
5. **Launch Hub & Reviews** (Checklist tracking for Product Hunt, G2, Capterra, Reddit, IndieHackers, with automated asset drafting and review request emails).

### Core Philosophy: *AI Drafts, Human Approves*
The system handles 95% of the mechanical work (drafting, formatting, MX verification, token refresh, metrics rollup). The operator's role is strictly review, curation, and personal engagement where human connection matters.

---

## 1. Operating Cadence: When & What to Do

Follow this time-efficient schedule to achieve maximum lead volume with minimal manual overhead:

| Frequency | Duration | Module / Screen | Action Items & Guidelines |
|---|---|---|---|
| **Daily (Morning)** | 10–15 min | Unified Inbox (`/admin/inbox`) | • Review prospect responses across all active campaigns.<br>• Triage interested replies vs objections.<br>• Forward warm leads to booking link / sales call.<br>• *Note:* Unsubscribes are auto-suppressed by the system; do not re-add them. |
| **Daily (Afternoon)** | 5 min | Dashboard (`/admin/dashboard`) | • Monitor campaign health: **Bounce rate MUST stay under 5%**.<br>• If a campaign hits >5% bounces, the background worker automatically pauses it.<br>• Inspect daily channel attribution pills (SEO, Social, Tools, Product Hunt). |
| **Weekly (Sunday 18:00 UTC)** | Automated | Background Worker (`generate_weekly_batch`) | • System automatically generates a full week of draft social posts (X, LinkedIn, Meta) aligned with Brand Profile.<br>• Posts sit in `pending_approval` state. |
| **Weekly (Monday 09:00)** | 20 min | Social Calendar (`/admin/calendar`) | • Review generated posts for brand voice, tone, and timeliness.<br>• Make any minor copy edits.<br>• Click **Approve**. The worker publishes approved posts automatically at scheduled times. |
| **Weekly (Monday 09:30)** | 20 min | SEO Manager (`/admin/seo`) | • Inspect newly generated programmatic SEO draft pages.<br>• Verify Quality Scores (>85 recommended, min 600 words).<br>• Select a batch of 20–50 verified pages and click **Batch Publish**. |
| **Weekly (Wednesday)** | 15 min | Lead Engine (`/admin/leads`) | • Upload fresh CSV lead batch from Apollo, LinkedIn, or scrapers.<br>• Click **Verify Leads** (checks MX records, syntax, disposable domains).<br>• Assign verified leads to active outreach campaigns. |
| **Monthly (1st of Month)** | 30 min | Launch & Reviews (`/admin/launch`) | • Dispatch review-request emails to active opted-in customers for G2 / Capterra.<br>• Run DNS health check on your cold email domain (SPF/DKIM/DMARC).<br>• Plan monthly video walkthrough screencasts in Video Studio. |

---

## 2. Module-by-Module Operator Guides

### 2.1 Cold Email Outreach Engine
- **Step 1 — Brand Profile:** Configure your value proposition, USP, and target audience in `/admin/brand`. The AI uses this for contextual outreach.
- **Step 2 — Importing Leads:** In `/admin/leads`, upload a CSV with columns: `email`, `first_name`, `company`, `industry`, `city`, `job_title`.
- **Step 3 — Lead Verification:** Click **Verify Leads**. The engine executes a 3-tier check: RFC syntax, MX DNS lookup, disposable domain blacklist, and role-based filtering (`support@`, `sales@`).
- **Step 4 — Campaign Setup:** In `/admin/campaigns`, create a 3-step sequence. Set step delays (Step 1: Day 0, Step 2: Day 3, Step 3: Day 7). Personalize with tokens like `{{first_name}}` and `{{company}}`.
- **Step 5 — Sending Windows:** Outbound sends occur only Monday through Friday between 9:00 AM and 5:00 PM in the recipient's local timezone.
- **Step 6 — Unsubscribe Compliance:** Every email automatically includes an RFC 8058 header and a one-click HMAC-signed unsubscribe link. Clicking it immediately adds the contact to the global `SuppressionList` and aborts all subsequent sequence steps.

### 2.2 Social Content Studio
- **Step 1 — Connect Accounts:** In `/admin/settings`, authenticate official OAuth 2.0 apps for X, LinkedIn Company Page, and Meta (Instagram Business + Facebook Page). Tokens are stored encrypted with Fernet.
- **Step 2 — Sunday Automated Batch:** Every Sunday at 18:00 UTC, the ARQ worker generates 7 days of social content customized to each network's character limit (X: 280, LinkedIn: 3000, Instagram: 2200, Facebook: 63206).
- **Step 3 — Claims Guard:** All drafts pass through `claims_guard.py` to strip out exaggerated promises, false guarantees, or unverifiable statistics.
- **Step 4 — UTM Tracking:** Outbound links are wrapped with UTM parameters and shortened via `/r/{slug}` for attribution analytics.
- **Step 5 — Approval Queue:** Posts enter `pending_approval`. You review them in `/admin/calendar` and click **Approve** or **Reject**. The worker job `publish_due_posts` dispatches only approved posts at their scheduled time.

### 2.3 Video Content Studio
- **Step 1 — Keyword Input:** Enter target keywords in `/admin/video` (e.g., "B2B client acquisition engine").
- **Step 2 — AI Script Generation:** The system returns 5 distinct content angles, followed by a complete 60–90 second script divided into:
  - `[Screen Visual Direction]`
  - `[Spoken Audio Dialogue]`
  - `[On-Screen Graphic / Text Overlay]`
- **Step 3 — Screen Recording:** Record your screen (1080p, 60fps) using OBS, Loom, or Camtasia, following the stage directions.
- **Step 4 — Publishing Metadata:** Copy the AI-generated SEO title, clickable timestamp description, 15 target tags, and visual thumbnail prompt.
- **Step 5 — YouTube Staging:** Upload via Google OAuth. The upload defaults to **Private / Unlisted** so you can review playback before making it public.

### 2.4 Programmatic SEO Engine & Free Tools
- **Templates Available:**
  1. `Find {industry} Leads in {city}`
  2. `Best {competitor} Alternative for {niche}`
  3. `Lead Generation for {use_case}`
- **Quality Gate:** Rejects any page under 600 words, with >70% token similarity to existing pages, or containing banned phrases from `claims_guard`.
- **Publishing:** Approve batches of 20–50 pages weekly in `/admin/seo`. Pages are rendered with Next.js ISR (24-hour cache), valid JSON-LD (`FAQPage`, `SoftwareApplication`, `BreadcrumbList`), and linked in `/sitemap.xml`.
- **Free Tools:**
  - **Subject Line Grader (`/tools/subject-line-grader`):** Instant 0–100 score + 3 AI rewrites; rate limited by IP.
  - **Email Verifier (`/tools/email-verifier`):** 5 free checks per day per IP; email capture modal unlocks unlimited checks, logging leads to `tool_usages`.
  - Both tools feature a sticky CTA linking to GlobalReach signup with UTM parameters.

### 2.5 Launch Hub & Customer Reviews
- **Kanban Launch Hub (`/admin/launch`):** Seeded checklists for Product Hunt, G2, Capterra, Reddit, and IndieHackers.
- **AI Asset Generation:** Produces Product Hunt taglines, maker comments, 2-week launch plans, and IndieHackers milestone drafts using live analytics metrics.
- **Reddit Compliance:** Generates authentic build-journey post drafts for `r/SaaS`, `r/Entrepreneur`, and `r/SideProject` with **zero link dropping** to avoid moderator bans.
- **Review Requests:** Dispatches direct G2/Capterra review request emails to active, opted-in customers via `POST /reviews/request`.

---

## 3. Built-in Safety Guardrails & Thresholds

| Guardrail | Mechanism | Threshold / Action | Operator Responsibility |
|---|---|---|---|
| **DRY_RUN Mode** | `dry_run_guard` decorator | Outbound dispatches are simulated & logged to DB | Keep enabled during testing; flip only after domain warmup |
| **Bounce Circuit Breaker** | `check_campaign_health` (15 min) | If bounce rate exceeds **5%**, campaign is auto-paused | Clean lead lists before resuming paused campaign |
| **Daily Sending Ramp** | Mailbox rate limiter | Wk 1: 15/day · Wk 2: 30/day · Wk 3+: 50/day max | Never exceed 50 cold emails per mailbox per day |
| **Claims Guard** | `claims_guard.py` regex scanner | Blocks banned phrases (guaranteed results, fake stats) | Ensure brand voice stays factual and verifiable |
| **SEO Quality Gate** | `quality_gate.py` analyzer | Rejects pages <600 words or >70% similarity | Approve only high-quality pages in batches of 20–50 |
| **Token Security** | Fernet symmetric encryption | All OAuth tokens encrypted at rest in DB | Keep `ENCRYPTION_KEY` secure in Railway environment |

---

## 4. Runbook: Safely Turning Off DRY_RUN (Going Live)

Follow this checklist before setting `DRY_RUN=false` in production:

### Phase 1: Pre-Flight Infrastructure Checklist
- [ ] **Dedicated Cold Email Domain:** Use a dedicated secondary domain (e.g. `mail-getyourclientsb2b.com`), never your root domain.
- [ ] **DNS Records Validated:** SPF, DKIM (2048-bit), DMARC (`p=quarantine`), and MX records configured.
- [ ] **Mailbox Warmup:** Mailboxes warmed up for **14 to 21 consecutive days** using a warmup tool.
- [ ] **OAuth App Approvals:** Developer apps for X, LinkedIn Company Page, and Meta verified.
- [ ] **Unsubscribe Test:** Send a test email, click the unsubscribe link, and confirm email is added to `/admin/campaigns` Suppression List.

### Phase 2: Flipping to Live Mode
1. Open your **Railway Dashboard**.
2. Select your **API Service** > **Variables** > Set `DRY_RUN=false`.
3. Select your **Worker Service** > **Variables** > Set `DRY_RUN=false`.
4. Trigger a service redeploy. The worker logs will display: `ARQ worker started. dry_run=False`.

### Phase 3: Emergency Rollback (Killswitch)
If bounce rates exceed 3%, spam complaints arise, or platform API warnings occur:
1. Immediately change `DRY_RUN=true` in Railway variables.
2. Go to `/admin/campaigns` and click **Pause All**.
3. All outbound transmissions immediately revert to simulated dry-run logging.

---

## 5. Quick Reference & Operator Checklist

- **Every Morning (5 mins):** Check `/admin/inbox` for prospect replies; reply personally to book demos. Verify campaign bounce rates in `/admin/dashboard` are <5%.
- **Every Monday (15 mins):** Review and approve social posts in `/admin/calendar`. Publish 20–50 programmatic SEO pages in `/admin/seo`.
- **Every Month (30 mins):** Run DNS domain health check, send review requests in `/admin/launch`, and plan video walkthrough topics.
- **Remember:** The Growth Engine automates the repetitive mechanics. Your focus is quality control, authentic engagement, and closing deals.
