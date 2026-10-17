"""
PDF Generation Script for GlobalReach Growth Engine Operations Manual & SOP Runbook.
Uses ReportLab to build a publication-grade, professional PDF document.
"""

import os
import sys
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    HRFlowable,
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and print total page count,
    running headers, and running footers on every page except the cover page.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber > 1:
            self.saveState()
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#64748B"))
            
            # Running Header
            self.drawString(
                54, 
                11 * inch - 36, 
                "GlobalReach Growth Engine — Standard Operating Procedures & Operations Manual"
            )
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)
            
            # Running Footer
            self.line(54, 46, 8.5 * inch - 54, 46)
            self.drawString(54, 34, "CONFIDENTIAL — FOR INTERNAL TEAM & OWNER USE ONLY")
            page_text = f"Page {self._pageNumber} of {page_count}"
            self.drawRightString(8.5 * inch - 54, 34, page_text)
            self.restoreState()


def build_pdf(filename="GlobalReach_Growth_Engine_Operations_Manual.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    primary_color = colors.HexColor("#0F172A")    # Slate 900
    brand_blue = colors.HexColor("#0284C7")       # Sky 600
    accent_emerald = colors.HexColor("#059669")   # Emerald 600
    accent_amber = colors.HexColor("#D97706")     # Amber 600
    text_dark = colors.HexColor("#1E293B")        # Slate 800
    text_muted = colors.HexColor("#475569")       # Slate 600
    bg_light = colors.HexColor("#F8FAFC")         # Slate 50
    border_color = colors.HexColor("#E2E8F0")     # Slate 200

    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=28,
        leading=34,
        textColor=primary_color,
        alignment=0,
        spaceAfter=10,
    )

    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=13,
        leading=18,
        textColor=brand_blue,
        alignment=0,
        spaceAfter=25,
    )

    meta_style = ParagraphStyle(
        'CoverMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=14,
        textColor=text_muted,
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=primary_color,
        spaceBefore=18,
        spaceAfter=8,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=brand_blue,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True,
    )

    h3_style = ParagraphStyle(
        'Heading3_Custom',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=text_dark,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13.5,
        textColor=text_dark,
        spaceAfter=6,
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=text_dark,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4,
    )

    callout_style = ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12.5,
        textColor=text_dark,
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=text_dark,
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=text_dark,
    )

    story = []

    # ---------------------------------------------------------
    # COVER / TITLE BLOCK
    # ---------------------------------------------------------
    story.append(Spacer(1, 20))
    story.append(Paragraph("GLOBALREACH GROWTH ENGINE", title_style))
    story.append(Paragraph("Standard Operating Procedures & Complete Automation Runbook", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=brand_blue, spaceBefore=0, spaceAfter=15))

    meta_text = """
    <b>System:</b> GlobalReach Growth Engine v1.0 (Full-Stack Automated Acquisition)<br/>
    <b>Stack:</b> Next.js 14 (Vercel) · FastAPI (Railway) · PostgreSQL 16 · Redis 7 · ARQ Worker · Claude 3.5 Sonnet<br/>
    <b>Target Audience:</b> Business Owner, Growth Lead, Marketing Operations & SDR Team<br/>
    <b>Current Safety Default:</b> <code>DRY_RUN=true</code> (Simulated sends until explicit owner flip)<br/>
    <b>Last Updated:</b> October 2026 · Confidential & Proprietary
    """
    story.append(Paragraph(meta_text, meta_style))
    story.append(Spacer(1, 20))

    # Executive Summary Box
    summary_box = [
        [
            Paragraph(
                "<b>Executive Summary & Core Operating Philosophy:</b><br/>"
                "The GlobalReach Growth Engine automates 5 high-impact customer acquisition pipelines: "
                "<b>Cold Email Outreach</b>, <b>Multi-Platform Social Publishing</b>, <b>Video Content Planning</b>, "
                "<b>Programmatic SEO & Free Lead Magnets</b>, and <b>Launch Hub & Review Ingestion</b>.<br/>"
                "<b>Key Philosophy:</b> <i>AI Drafts, Human Approves.</i> The system handles 95% of the mechanical drafting, "
                "verifications, metrics rollup, and API packaging. The operator's role is strictly review, quality control, "
                "and personal engagement where human trust matters.",
                callout_style
            )
        ]
    ]
    t_summary = Table(summary_box, colWidths=[504])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_light),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(t_summary)
    story.append(Spacer(1, 15))

    # ---------------------------------------------------------
    # SECTION 1: TIME-BASED OPERATOR CADENCE
    # ---------------------------------------------------------
    story.append(Paragraph("1. Operator Time Cadence: When & What to Do", h1_style))
    story.append(Paragraph(
        "To achieve maximum lead volume with minimum time overhead, follow this structured schedule. "
        "The system runs 8 background worker jobs automatically; your manual touchpoints are concentrated into predictable windows.",
        body_style
    ))

    cadence_data = [
        [
            Paragraph("Frequency", table_header_style),
            Paragraph("Duration", table_header_style),
            Paragraph("Module / Screen", table_header_style),
            Paragraph("Action Items & Guidelines", table_header_style),
        ],
        [
            Paragraph("<b>Daily</b><br/>Morning", table_cell_bold),
            Paragraph("10–15 min", table_cell_style),
            Paragraph("Unified Inbox<br/>(<code>/admin/inbox</code>)", table_cell_style),
            Paragraph("• Check prospect replies across active campaigns.<br/>• Triage positive interest vs objections.<br/>• Forward warm leads to calendar / sales call.<br/>• Unsubscribes are auto-handled; do NOT re-add.", table_cell_style),
        ],
        [
            Paragraph("<b>Daily</b><br/>Afternoon", table_cell_bold),
            Paragraph("5 min", table_cell_style),
            Paragraph("Dashboard<br/>(<code>/admin/dashboard</code>)", table_cell_style),
            Paragraph("• Verify campaign health: bounce rate MUST stay under 5%.<br/>• If a campaign hits >5% bounces, worker auto-pauses it.<br/>• Inspect daily attribution pills (SEO, Social, Tools, PH).", table_cell_style),
        ],
        [
            Paragraph("<b>Weekly</b><br/>Sunday 18:00", table_cell_bold),
            Paragraph("Automated", table_cell_style),
            Paragraph("Background Worker<br/>(<code>generate_weekly_batch</code>)", table_cell_style),
            Paragraph("• System automatically generates a full week of draft social posts (X, LinkedIn, Meta) aligned with Brand Profile.<br/>• Posts sit in <code>pending_approval</code> status.", table_cell_style),
        ],
        [
            Paragraph("<b>Weekly</b><br/>Monday 09:00", table_cell_bold),
            Paragraph("20 min", table_cell_style),
            Paragraph("Social Calendar<br/>(<code>/admin/calendar</code>)", table_cell_style),
            Paragraph("• Review generated posts for brand voice & relevance.<br/>• Edit copy or hashtags if needed.<br/>• Click <b>Approve</b>. Worker will publish automatically at scheduled times.", table_cell_style),
        ],
        [
            Paragraph("<b>Weekly</b><br/>Monday 09:30", table_cell_bold),
            Paragraph("20 min", table_cell_style),
            Paragraph("SEO Manager<br/>(<code>/admin/seo</code>)", table_cell_style),
            Paragraph("• Inspect newly generated programmatic SEO draft pages.<br/>• Check Quality Scores (>85 recommended, min 600 words).<br/>• Select a batch of 20–50 verified pages and click <b>Batch Publish</b>.", table_cell_style),
        ],
        [
            Paragraph("<b>Weekly</b><br/>Wednesday", table_cell_bold),
            Paragraph("15 min", table_cell_style),
            Paragraph("Lead Engine<br/>(<code>/admin/leads</code>)", table_cell_style),
            Paragraph("• Upload fresh CSV lead batch from Apollo, LinkedIn, or scrapers.<br/>• Run email verification job.<br/>• Assign verified contacts to active outreach campaigns.", table_cell_style),
        ],
        [
            Paragraph("<b>Monthly</b><br/>1st of Month", table_cell_bold),
            Paragraph("30 min", table_cell_style),
            Paragraph("Launch & Reviews<br/>(<code>/admin/launch</code>)", table_cell_style),
            Paragraph("• Dispatch review-request emails to active opted-in users.<br/>• Audit cold email domain DNS health (SPF/DKIM/DMARC).<br/>• Plan monthly video walkthrough topics in Video Studio.", table_cell_style),
        ],
    ]

    t_cadence = Table(cadence_data, colWidths=[70, 50, 110, 274])
    t_cadence.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg_light]),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_cadence)
    story.append(Spacer(1, 15))

    # ---------------------------------------------------------
    # SECTION 2: MODULE-BY-MODULE OPERATING MANUAL
    # ---------------------------------------------------------
    story.append(Paragraph("2. Module-by-Module Operator Guides", h1_style))

    # Module 1: Cold Email
    story.append(Paragraph("2.1 Cold Email Outreach Engine", h2_style))
    story.append(Paragraph(
        "<b>Purpose:</b> Automate personalized, multi-touch cold email sequences that respect deliverability limits, "
        "sending windows, domain health, and legal compliance (CAN-SPAM, GDPR).",
        body_style
    ))
    story.append(Paragraph("<b>Step-by-Step Workflow:</b>", h3_style))
    story.append(Paragraph("<b>1. ICP & Brand Profile:</b> Configure positioning, USP, and value props in <code>/admin/brand</code>. The AI uses this for dynamic personalization.", bullet_style))
    story.append(Paragraph("<b>2. Sourcing & Importing Leads:</b> Navigate to <code>/admin/leads</code>. Upload a CSV containing columns: <code>email</code>, <code>first_name</code>, <code>company</code>, <code>industry</code>, <code>city</code>, <code>job_title</code>.", bullet_style))
    story.append(Paragraph("<b>3. Lead Verification:</b> Click <b>Verify Leads</b>. The system validates: syntax format, MX DNS record presence, disposable email detection, and role-based accounts (info@, sales@). Only valid leads are marked for campaigns.", bullet_style))
    story.append(Paragraph("<b>4. Sequence Builder:</b> In <code>/admin/campaigns</code>, create a 3-step sequence. Set step delays (e.g. Step 1: Day 0, Step 2: Day 3, Step 3: Day 7). Use tokens like <code>{{first_name}}</code> and <code>{{company}}</code>.", bullet_style))
    story.append(Paragraph("<b>5. Sending Windows:</b> Emails are only dispatched Monday through Friday, 9:00 AM to 5:00 PM in the recipient's timezone.", bullet_style))
    story.append(Paragraph("<b>6. Unsubscribe Enforcement:</b> Every email includes an RFC 8058 header and a one-click HMAC-signed unsubscribe link. Clicking it immediately adds the contact to the global <code>SuppressionList</code> and cancels remaining sequence steps.", bullet_style))

    story.append(Spacer(1, 8))

    # Module 2: Social Content Studio
    story.append(Paragraph("2.2 Social Content Studio & Publishing", h2_style))
    story.append(Paragraph(
        "<b>Purpose:</b> Multi-platform content distribution across X, LinkedIn, Instagram, and Facebook without manual copy-pasting.",
        body_style
    ))
    story.append(Paragraph("<b>Step-by-Step Workflow:</b>", h3_style))
    story.append(Paragraph("<b>1. Connect Accounts:</b> Navigate to <code>/admin/settings</code> or <code>/admin/calendar</code>. Authenticate with official OAuth 2.0 apps for X, LinkedIn Company Page, and Meta (Instagram Business + Facebook Page).", bullet_style))
    story.append(Paragraph("<b>2. Sunday Automated Batch:</b> The worker triggers <code>generate_weekly_content_batch</code> on Sundays at 18:00 UTC. Claude 3.5 Sonnet creates 7 days of posts customized for each platform's character limits.", bullet_style))
    story.append(Paragraph("<b>3. Claims Guard Verification:</b> Every draft passes through <code>claims_guard.py</code> to ensure zero fabricated guarantees, 10x ROI claims, or unverifiable statistics.", bullet_style))
    story.append(Paragraph("<b>4. UTM Tracking:</b> Outbound links are automatically wrapped with UTM campaign tags and shortened via <code>/r/{slug}</code> for click attribution.", bullet_style))
    story.append(Paragraph("<b>5. Approval Queue:</b> Posts are placed in <code>pending_approval</code>. You review them in <code>/admin/calendar</code>. Only posts marked <b>Approved</b> will be published by the <code>publish_due_posts</code> worker job.", bullet_style))

    story.append(Spacer(1, 8))

    # Module 3: Video Content Studio
    story.append(Paragraph("2.3 Video Content Studio & YouTube Pipeline", h2_style))
    story.append(Paragraph(
        "<b>Purpose:</b> Systematize video production for YouTube Shorts, long-form walkthroughs, and social video.",
        body_style
    ))
    story.append(Paragraph("<b>Step-by-Step Workflow:</b>", h3_style))
    story.append(Paragraph("<b>1. Keyword Input:</b> Enter your target search term in <code>/admin/video</code> (e.g. 'B2B lead generation workflow').", bullet_style))
    story.append(Paragraph("<b>2. AI Script Generation:</b> The engine generates 5 distinct content angles, followed by a complete 60–90 second script broken down into <code>[Visual Screen Direction]</code>, <code>[Spoken Dialogue]</code>, and <code>[On-screen Graphic]</code>.", bullet_style))
    story.append(Paragraph("<b>3. Human Recording (Screencast):</b> Open your screen recording tool (OBS, Loom, QuickTime) at 1080p 60fps. Walk through the GlobalReach UI following the generated stage directions.", bullet_style))
    story.append(Paragraph("<b>4. Metadata Export:</b> The system outputs the SEO Title, Description with clickable timestamps, 15 target tags, and a visual Thumbnail Brief.", bullet_style))
    story.append(Paragraph("<b>5. YouTube Upload:</b> Push via Google OAuth. The upload is staged as <b>Private / Unlisted</b> so you can review playback before making it Public.", bullet_style))

    story.append(PageBreak())

    # Module 4: Programmatic SEO & Free Tools
    story.append(Paragraph("2.4 Programmatic SEO Engine & Free Lead Magnets", h2_style))
    story.append(Paragraph(
        "<b>Purpose:</b> Drive high-intent organic search traffic and capture top-of-funnel leads via automated utility tools.",
        body_style
    ))
    story.append(Paragraph("<b>Programmatic SEO Workflow:</b>", h3_style))
    story.append(Paragraph("<b>1. Template Types:</b> Three seeded templates in <code>/admin/seo</code>: "
                           "1) <i>Find {industry} Leads in {city}</i>, "
                           "2) <i>Best {competitor} Alternative for {niche}</i>, and "
                           "3) <i>Lead Generation for {use_case}</i>.", bullet_style))
    story.append(Paragraph("<b>2. Variable Generation:</b> Enter variable combinations (e.g. Industry = FinTech, City = Austin; Competitor = Apollo.io, Niche = Agencies) or upload a CSV.", bullet_style))
    story.append(Paragraph("<b>3. AI Content & Quality Gate:</b> Claude 3.5 Sonnet generates intro, 5–7 deep sections, factual comparison tables, and FAQ schema data. The <b>Quality Gate</b> strictly rejects pages under 600 words, similarity > 70%, or failing <code>claims_guard</code>.", bullet_style))
    story.append(Paragraph("<b>4. Weekly Batch Publish:</b> The owner approves batches of 20–50 pages in <code>/admin/seo</code>. Worker job <code>seo_publish_batch</code> publishes them to public ISR routes with 24-hour revalidation.", bullet_style))
    story.append(Paragraph("<b>5. Sitemaps & Structured Data:</b> Public pages are automatically indexed into <code>/sitemap.xml</code> with valid <code>FAQPage</code>, <code>SoftwareApplication</code>, and <code>BreadcrumbList</code> JSON-LD schema.", bullet_style))

    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>Free Lead-Magnet Tools Operation:</b>", h3_style))
    story.append(Paragraph("• <b>Cold Email Subject Line Grader (<code>/tools/subject-line-grader</code>):</b> Scores subject lines 0–100 based on length, spam triggers, personalization, curiosity, and clarity, returning 3 AI rewrites. Rate limited by IP.", bullet_style))
    story.append(Paragraph("• <b>Free Email Verifier (<code>/tools/email-verifier</code>):</b> Verifies up to 5 emails/day per IP anonymously. Prompts user with an email-capture modal to unlock unlimited/bulk verifications, logging leads to <code>tool_usages</code>.", bullet_style))
    story.append(Paragraph("• <b>Conversion Funnel:</b> Both tools feature a persistent sticky CTA linking directly to <code>getyourclientsb2b.com/signup</code> with pre-tagged UTM attribution.", bullet_style))

    story.append(Spacer(1, 8))

    # Module 5: Launch Hub & Reviews
    story.append(Paragraph("2.5 Launch Hub & Customer Review Ingestion", h2_style))
    story.append(Paragraph(
        "<b>Purpose:</b> Coordinate multi-channel product launches and harvest authentic customer testimonials.",
        body_style
    ))
    story.append(Paragraph("<b>Step-by-Step Workflow:</b>", h3_style))
    story.append(Paragraph("<b>1. Kanban Launch Tasks:</b> In <code>/admin/launch</code>, track pre-seeded launch checklists for Product Hunt, G2, Capterra, Reddit, and IndieHackers.", bullet_style))
    story.append(Paragraph("<b>2. AI Asset Generation:</b> Click <b>Generate Assets</b> on any platform card. System drafts Product Hunt taglines, maker comments, and 2-week launch day schedules.", bullet_style))
    story.append(Paragraph("<b>3. Community Rules Compliance:</b> Reddit drafts (r/SaaS, r/Entrepreneur, r/SideProject) focus on authentic technical build-journeys with <b>zero link dropping</b> to adhere strictly to moderation guidelines.", bullet_style))
    story.append(Paragraph("<b>4. IndieHackers Milestones:</b> Drafts real milestone posts pulling verified numbers from the analytics database.", bullet_style))
    story.append(Paragraph("<b>5. Review Requests:</b> Trigger review emails (direct G2/Capterra rating links) only to active, opted-in platform users via <code>POST /reviews/request</code>.", bullet_style))

    story.append(Spacer(1, 15))

    # ---------------------------------------------------------
    # SECTION 3: SAFETY PROTOCOLS & GUARDRAILS
    # ---------------------------------------------------------
    story.append(Paragraph("3. Safety Protocols & Built-in Guardrails", h1_style))
    story.append(Paragraph(
        "The Growth Engine is engineered with failsafes to protect sender domain reputation and platform API accounts:",
        body_style
    ))

    guardrails_data = [
        [
            Paragraph("Guardrail", table_header_style),
            Paragraph("Mechanism", table_header_style),
            Paragraph("Threshold / Action", table_header_style),
            Paragraph("Operator Responsibility", table_header_style),
        ],
        [
            Paragraph("<b>DRY_RUN Mode</b>", table_cell_bold),
            Paragraph("<code>dry_run_guard</code> decorator across all outbound actions", table_cell_style),
            Paragraph("Default <code>DRY_RUN=true</code>. Outbound emails & posts are simulated and logged.", table_cell_style),
            Paragraph("Keep enabled during testing; flip to <code>false</code> only after domain warmup.", table_cell_style),
        ],
        [
            Paragraph("<b>Campaign Bounce Circuit Breaker</b>", table_cell_bold),
            Paragraph("<code>check_campaign_health</code> worker job (every 15 min)", table_cell_style),
            Paragraph("If campaign bounce rate exceeds <b>5%</b>, campaign is auto-paused immediately.", table_cell_style),
            Paragraph("Investigate lead source quality before resuming paused campaign.", table_cell_style),
        ],
        [
            Paragraph("<b>Daily Sending Limits</b>", table_cell_bold),
            Paragraph("Mailbox rate limiter & ramp schedule", table_cell_style),
            Paragraph("Week 1: 15/day<br/>Week 2: 30/day<br/>Week 3+: 50/day max per mailbox", table_cell_style),
            Paragraph("Never bypass daily sending caps on fresh or warmed domains.", table_cell_style),
        ],
        [
            Paragraph("<b>Claims Guard Filter</b>", table_cell_bold),
            Paragraph("<code>claims_guard.py</code> deterministic regex audit", table_cell_style),
            Paragraph("Blocks banned claims: 'guaranteed', '10x results', fake statistics.", table_cell_style),
            Paragraph("Ensure brand voice prompts stick to verifiable product capabilities.", table_cell_style),
        ],
        [
            Paragraph("<b>SEO Quality Gate</b>", table_cell_bold),
            Paragraph("<code>quality_gate.py</code> content analyzer", table_cell_style),
            Paragraph("Rejects pages <600 words, >70% similarity, or missing local niche data.", table_cell_style),
            Paragraph("Do not attempt to mass-index thin programmatic doorway pages.", table_cell_style),
        ],
        [
            Paragraph("<b>Token Encryption</b>", table_cell_bold),
            Paragraph("Fernet symmetric encryption at rest", table_cell_style),
            Paragraph("All OAuth tokens encrypted using <code>ENCRYPTION_KEY</code> in DB.", table_cell_style),
            Paragraph("Safeguard <code>ENCRYPTION_KEY</code> in Railway environment variables.", table_cell_style),
        ],
    ]

    t_guards = Table(guardrails_data, colWidths=[90, 110, 140, 164])
    t_guards.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg_light]),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_guards)
    story.append(Spacer(1, 15))

    # ---------------------------------------------------------
    # SECTION 4: RUNBOOK — SWITCHING TO LIVE PRODUCTION
    # ---------------------------------------------------------
    story.append(Paragraph("4. Runbook: Safely Turning Off DRY_RUN (Going Live)", h1_style))
    story.append(Paragraph(
        "Follow this rigorous checklist before switching from simulation to live email dispatches and social posts:",
        body_style
    ))

    story.append(Paragraph("Phase 1: Pre-Flight Infrastructure Checklist", h2_style))
    story.append(Paragraph("☐ <b>Dedicated Domain:</b> Never use your root domain (<code>getyourclientsb2b.com</code>) for cold email. Provision a dedicated sending domain (e.g. <code>mail-getyourclientsb2b.com</code>).", bullet_style))
    story.append(Paragraph("☐ <b>DNS Authentication:</b> Verify 4 records: SPF (<code>v=spf1 ...</code>), DKIM (2048-bit key), DMARC (<code>p=quarantine</code> or <code>p=reject</code>), and MX records.", bullet_style))
    story.append(Paragraph("☐ <b>Mailbox Warmup:</b> Run an automated warmup service on all sending mailboxes for a minimum of <b>14 to 21 consecutive days</b> prior to cold outreach.", bullet_style))
    story.append(Paragraph("☐ <b>OAuth Approvals:</b> Verify connected accounts in <code>/admin/settings</code>. Confirm LinkedIn Organization Page permissions and Meta App Review status.", bullet_style))
    story.append(Paragraph("☐ <b>Unsubscribe Test:</b> Send a test email to your personal account. Click the unsubscribe link and verify that your email appears in <code>/admin/campaigns</code> under Suppression List.", bullet_style))

    story.append(Spacer(1, 6))
    story.append(Paragraph("Phase 2: Changing Environment Variables in Railway", h2_style))
    story.append(Paragraph("1. Log in to your <b>Railway Dashboard</b>.", bullet_style))
    story.append(Paragraph("2. Select your <b>API Service</b> > <b>Variables</b> > Change <code>DRY_RUN=false</code>.", bullet_style))
    story.append(Paragraph("3. Select your <b>Worker Service</b> > <b>Variables</b> > Change <code>DRY_RUN=false</code>.", bullet_style))
    story.append(Paragraph("4. Trigger a service redeploy. The worker logs will confirm: <code>ARQ worker started. dry_run=False</code>.", bullet_style))

    story.append(Spacer(1, 6))
    story.append(Paragraph("Phase 3: Emergency Rollback (Killswitch)", h2_style))
    story.append(Paragraph(
        "If abnormal bounce rates (>3%), spam complaints, or platform API warnings occur at any time:<br/>"
        "<b>1.</b> Instantly update Railway variable back to <code>DRY_RUN=true</code> on both API and Worker services.<br/>"
        "<b>2.</b> Navigate to <code>/admin/campaigns</code> and click <b>Pause All</b>.<br/>"
        "<b>3.</b> Outbound transmissions immediately halt and revert to benign dry-run logs in the database.",
        callout_style
    ))

    story.append(PageBreak())

    # ---------------------------------------------------------
    # SECTION 5: ENVIRONMENT VARIABLES & SYSTEM HEALTH
    # ---------------------------------------------------------
    story.append(Paragraph("5. Environment Variables & Quick Reference", h1_style))
    story.append(Paragraph(
        "Reference list of key configuration parameters in <code>backend/.env</code> and Railway:",
        body_style
    ))

    env_data = [
        [
            Paragraph("Variable Name", table_header_style),
            Paragraph("Sample / Default Value", table_header_style),
            Paragraph("Purpose & Description", table_header_style),
        ],
        [
            Paragraph("<code>DRY_RUN</code>", table_cell_bold),
            Paragraph("<code>true</code> (Default)", table_cell_style),
            Paragraph("Global safety switch. Set to <code>false</code> only when live.", table_cell_style),
        ],
        [
            Paragraph("<code>DATABASE_URL</code>", table_cell_bold),
            Paragraph("<code>postgresql+asyncpg://...</code>", table_cell_style),
            Paragraph("PostgreSQL connection string (Railway managed).", table_cell_style),
        ],
        [
            Paragraph("<code>REDIS_URL</code>", table_cell_bold),
            Paragraph("<code>redis://localhost:6379</code>", table_cell_style),
            Paragraph("Redis broker URL for ARQ job queue and rate limiting.", table_cell_style),
        ],
        [
            Paragraph("<code>ANTHROPIC_API_KEY</code>", table_cell_bold),
            Paragraph("<code>sk-ant-...</code>", table_cell_style),
            Paragraph("Claude 3.5 Sonnet API key for SEO, emails, social, and tools.", table_cell_style),
        ],
        [
            Paragraph("<code>JWT_SECRET</code>", table_cell_bold),
            Paragraph("<i>Generated 64-char string</i>", table_cell_style),
            Paragraph("Signs admin session tokens (HS256).", table_cell_style),
        ],
        [
            Paragraph("<code>ENCRYPTION_KEY</code>", table_cell_bold),
            Paragraph("<i>Fernet 32-byte urlsafe key</i>", table_cell_style),
            Paragraph("Encrypts OAuth access and refresh tokens at rest.", table_cell_style),
        ],
        [
            Paragraph("<code>UNSUBSCRIBE_SECRET</code>", table_cell_bold),
            Paragraph("<i>Generated 32-char string</i>", table_cell_style),
            Paragraph("HMAC signing secret for tamper-proof 1-click unsubscribe links.", table_cell_style),
        ],
        [
            Paragraph("<code>SIGNUP_WEBHOOK_SECRET</code>", table_cell_bold),
            Paragraph("<i>Generated 32-char string</i>", table_cell_style),
            Paragraph("HMAC signature verification for main product signup webhooks.", table_cell_style),
        ],
        [
            Paragraph("<code>SENTRY_DSN</code>", table_cell_bold),
            Paragraph("<code>https://...@sentry.io/...</code>", table_cell_style),
            Paragraph("Error tracking and APM performance monitoring for API & Worker.", table_cell_style),
        ],
    ]

    t_env = Table(env_data, colWidths=[140, 160, 204])
    t_env.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg_light]),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_env)
    story.append(Spacer(1, 15))

    # ---------------------------------------------------------
    # SECTION 6: SUMMARY CHECKLIST FOR OPERATORS
    # ---------------------------------------------------------
    story.append(Paragraph("6. Operator Quick-Start Checklist", h1_style))
    checklist_box = [
        [
            Paragraph(
                "<b>Every Morning (5 mins):</b> Open <code>/admin/inbox</code>. If an interested prospect replied, "
                "respond personally to schedule a demo. Check <code>/admin/dashboard</code> to verify all campaign bounce rates are <5%.<br/><br/>"
                "<b>Every Monday (15 mins):</b> Open <code>/admin/calendar</code>. Review the AI-generated social posts for the week, "
                "make any minor edits, and click <b>Approve</b>. Open <code>/admin/seo</code> and batch publish 20–50 verified SEO pages.<br/><br/>"
                "<b>Every Month (30 mins):</b> Run the DNS health check on your cold email domain, trigger review requests "
                "in <code>/admin/launch</code>, and plan new video walkthrough screencasts.<br/><br/>"
                "<b>Remember:</b> The engine handles the heavy lifting, data enrichment, and scheduling. "
                "Your role is human oversight, brand curation, and closing high-value deals.",
                callout_style
            )
        ]
    ]
    t_check = Table(checklist_box, colWidths=[504])
    t_check.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),  # Blue 50
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#BFDBFE")),      # Blue 200
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(t_check)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated PDF manual: {filename}")


if __name__ == "__main__":
    output_filename = "GlobalReach_Growth_Engine_Operations_Manual.pdf"
    if len(sys.argv) > 1:
        output_filename = sys.argv[1]
    build_pdf(output_filename)
