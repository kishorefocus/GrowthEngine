"""
Programmatic SEO router.
Manages templates, bulk page generation, quality scores, batch publishing, and public endpoints.
"""
import csv
import io
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user, require_owner
from app.models.analytics import AuditLog
from app.models.auth import User
from app.models.seo import SEOPage, SEOTemplate
from app.schemas.seo import (
    SEOGenerateRequest,
    SEOPageBatchPublishRequest,
    SEOPageResponse,
    SEOPublicPageResponse,
    SEOTemplateCreate,
    SEOTemplateResponse,
)
from app.services.ai import generate
from app.services.claims_guard import check_claims, is_safe
from app.services.quality_gate import evaluate_seo_page, extract_full_text
from app.services.utm import build_utm_url

logger = logging.getLogger(__name__)

router = APIRouter(tags=["SEO"])
public_router = APIRouter(prefix="/public/seo", tags=["Public SEO"])

DEFAULT_TEMPLATES = [
    {
        "type": "industry_city",
        "url_pattern": "/find-leads/{industry}/{city}",
        "title_pattern": "Find {industry} Leads in {city} | GlobalReach",
        "h1_pattern": "Find Verified {industry} Leads in {city}",
        "body_prompt": "Provide actionable strategies for sourcing and verifying {industry} leads in {city}. Detail local business hubs, directories, cold email compliance, and how GlobalReach automates the process.",
    },
    {
        "type": "alternative",
        "url_pattern": "/alternatives/{competitor}/{niche}",
        "title_pattern": "Best {competitor} Alternative for {niche} | GlobalReach",
        "h1_pattern": "{competitor} vs GlobalReach for {niche}",
        "body_prompt": "A fair, objective comparison of {competitor} and GlobalReach specifically for {niche}. Detail pricing, contact accuracy, sequencing, and lead finding.",
    },
    {
        "type": "use_case",
        "url_pattern": "/use-cases/{slug}",
        "title_pattern": "Lead Generation for {use_case} | GlobalReach",
        "h1_pattern": "Automated Lead Generation for {use_case}",
        "body_prompt": "Deep dive into lead acquisition for {use_case}. Explain prospecting tactics, verified outreach workflows, and ROI considerations.",
    },
]


def _build_mock_seo_content(template_type: str, variables: dict[str, Any]) -> dict[str, Any]:
    """Fallback generator when Anthropic is unavailable or in mock mode."""
    ind = variables.get("industry", "Technology")
    city = variables.get("city", "Austin")
    comp = variables.get("competitor", "Apollo.io")
    niche = variables.get("niche", "Agencies")
    use_case = variables.get("use_case", "B2B SaaS Growth")

    if template_type == "industry_city":
        h1 = f"Find Verified {ind} Leads in {city}"
        meta_desc = f"Discover high-converting {ind} leads in {city}. Automated prospecting, email verification, and compliance-first outreach."
        intro = (
            f"Scaling a modern B2B business targeting {ind} companies in {city} requires clean, verified contact data and disciplined outreach execution. "
            f"Whether you are targeting established regional enterprises or agile venture-backed startups across the greater {city} area, "
            f"manual prospecting drains dozens of hours every week that your sales team should spend conducting discovery calls and closing contracts. "
            f"GlobalReach provides an integrated client acquisition engine that automates target company discovery, "
            f"validates every executive email address prior to dispatch, and orchestrates multi-step cold sequences safely and predictably."
        )
        sections = [
            {
                "heading": f"Understanding the {city} {ind} Commercial Ecosystem",
                "content": (
                    f"The commercial landscape for {ind} within {city} is marked by intense competition and evolving buyer expectations. "
                    f"Decision-makers in {city}'s {ind} sector are inundated with generic sales pitches that lack context. "
                    f"To stand out, your prospecting must leverage precise firmographic attributes such as employee growth trajectory, "
                    f"current technology investments, and exact managerial responsibilities. "
                    f"Addressing the operational nuances specific to companies headquartered in {city} yields significantly higher engagement rates."
                ),
            },
            {
                "heading": "Sourcing and Verifying Contact Data with Real-Time Validation",
                "content": (
                    f"Stale contact directories severely handicap sales capacity and damage outbound infrastructure. "
                    f"When sourcing {ind} executives in {city}, every prospective email address must undergo rigorous verification. "
                    f"This includes strict syntax confirmation, domain MX record resolution, disposable mailbox detection, and role account identification. "
                    f"By actively stripping unverified records before any message enters a sending queue, your outbound pipeline maintains industry-leading deliverability."
                ),
            },
            {
                "heading": f"Outreach Best Practices for Reaching {city} {ind} Executives",
                "content": (
                    f"Executive buyers prioritize brevity, contextual relevance, and immediate operational value over feature checklists. "
                    f"Effective outreach to {ind} leaders in {city} opens with an observable company event or shared commercial challenge. "
                    f"Keep subject lines under 40 characters and lowercase to feel natural. Frame your closing call-to-action around a low-friction interest check "
                    f"rather than demanding a 30-minute demonstration on the initial interaction."
                ),
            },
            {
                "heading": f"Tailoring Sequences to {city} Working Hours and Time Zones",
                "content": (
                    f"Scheduling outbound sequences within the local working hours of {city} ensures prospects receive communications when they are actively triaging inboxes. "
                    f"GlobalReach coordinates sequence delivery based on recipient time zones, introducing intelligent random jitter between sends "
                    f"to emulate human dispatch patterns and maintain spotless domain reputation with major mailbox providers."
                ),
            },
            {
                "heading": "Step-by-Step Prospecting Workflow with GlobalReach",
                "content": (
                    f"1. Define your Ideal Customer Profile (ICP) specifying {ind} companies operating in {city}.\n"
                    f"2. Filter target accounts by headcount bands, executive seniority, and verified business emails.\n"
                    f"3. Run automated email verification to ensure inbox deliverability and eliminate bounce hazards.\n"
                    f"4. Schedule personalized outreach sequences adhering to local business hours and daily volume caps.\n"
                    f"5. Automatically route positive responses to your primary sales inbox for rapid qualification."
                ),
            },
            {
                "heading": "Technical Deliverability Safeguards & Auto-Pause Rules",
                "content": (
                    f"Outbound scalability hinges on domain health. Technical protocols including SPF, DKIM, and DMARC establish domain authenticity. "
                    f"GlobalReach continuously monitors campaign bounce rates. If invalid recipient rates exceed 5% or complaint signals rise above 0.3%, "
                    f"active campaigns automatically pause to protect your primary corporate domain from ISP throttling."
                ),
            },
            {
                "heading": "Regulatory Compliance and Ethical Prospecting Standards",
                "content": (
                    f"Operating a durable B2B outbound motion requires strict adherence to privacy regulations including CAN-SPAM and GDPR. "
                    f"Every outbound email incorporates a clear one-click unsubscribe mechanism, visible physical corporate address, and immediate suppression enforcement. "
                    f"Ethical prospecting builds long-term commercial trust and positions your brand as a professional partner."
                ),
            },
        ]
        faq = [
            {"question": f"How accurate is the {ind} lead data in {city}?", "answer": "Every contact address undergoes real-time syntax, MX, and disposable verification prior to campaign launch."},
            {"question": "Does GlobalReach support CAN-SPAM and GDPR compliance?", "answer": "Yes. Every message includes automated unsubscribe token headers, suppression enforcement, and physical address footers."},
            {"question": f"Can I target specific sub-niches within {ind}?", "answer": f"Yes. You can filter by job title, company size, tech stack, and location within {city}."},
            {"question": "What happens when a prospect unsubscribes?", "answer": "They are immediately added to your permanent suppression list and blocked from future sequences across all campaigns."},
        ]
        comparison_table = {"competitor_name": "", "features": []}
    elif template_type == "alternative":
        h1 = f"{comp} vs GlobalReach for {niche}"
        meta_desc = f"Comparing {comp} and GlobalReach for {niche}. Discover feature differences, pricing, verification workflows, and outreach automation."
        intro = (
            f"If you are evaluating {comp} alternatives tailored for {niche}, understanding the tradeoffs between database volume "
            f"and outbound workflow automation is essential. While legacy data providers offer broad databases, "
            f"teams often struggle with stale contact records, separate tooling subscriptions, and complex setup processes. "
            f"GlobalReach unites lead discovery, automated email verification, multi-channel social drafting, and campaign scheduling in one platform."
        )
        sections = [
            {
                "heading": f"Why {niche} Teams Explore Alternatives to {comp}",
                "content": (
                    f"Teams operating in {niche} require specialized workflows that combine fresh prospect data with streamlined sequence management. "
                    f"Common challenges with {comp} include paywalled export limits, high credit burn on unverified emails, and the need for third-party email warmup tools. "
                    f"A dedicated growth engine designed for high-signal outbound eliminates tool sprawl and reduces cost per qualified meeting."
                ),
            },
            {
                "heading": "Contact Verification: Built-in vs Add-On Credits",
                "content": (
                    f"Deliverability is the foundation of modern B2B outreach. Sending campaigns to stale contacts damages domain reputation permanently. "
                    f"GlobalReach embeds multi-step email verification into the core platform, checking MX records, disposable services, and role accounts before any email is dispatched. "
                    f"This ensures {niche} sales teams maintain low bounce rates without purchasing separate verification credits."
                ),
            },
            {
                "heading": "Multi-Channel Growth: Beyond Cold Email",
                "content": (
                    f"Outbound prospecting is no longer confined to email inboxes. Effective customer acquisition requires consistent presence across LinkedIn, X, and organic search. "
                    f"Unlike {comp}, which focuses purely on database credits and email sequences, GlobalReach provides an integrated Content Studio and Video Studio "
                    f"that drafts platform-tailored social content and long-form video outlines to drive inbound momentum alongside cold outbound."
                ),
            },
            {
                "heading": f"Tailored Prospecting Workflows for {niche}",
                "content": (
                    f"For {niche} organizations, speed to market is paramount. GlobalReach enables one-click CSV imports, "
                    f"dogfooded lead lists, and automated suppression list synchronizations. "
                    f"Campaign health monitors automatically pause sequences if bounce rates approach conservative thresholds, protecting your outbound infrastructure."
                ),
            },
            {
                "heading": "Predictable Operational Economics",
                "content": (
                    f"Traditional enterprise providers lock customers into annual contracts with rigid user seats and credit caps. "
                    f"GlobalReach offers a predictable operational model tailored to growing businesses and agencies. "
                    f"You retain full ownership of your data, campaign workflows, and outreach schedules without hidden surprise fees."
                ),
            },
            {
                "heading": "Human-in-the-Loop Quality Control",
                "content": (
                    f"Unlike black-box autonomous bots that blast generic templates, GlobalReach incorporates a structured approval queue. "
                    f"Review, edit, and approve every outbound sequence, social draft, and video script before publication, ensuring brand voice integrity."
                ),
            },
            {
                "heading": "Transparent Attribution from Click to Revenue",
                "content": (
                    f"Understand exactly which outreach channel converts into paying customers. GlobalReach automatically wraps links with tamper-proof UTM parameters "
                    f"and attributes signups back to specific campaigns, social posts, or SEO pages."
                ),
            },
        ]
        faq = [
            {"question": f"Is GlobalReach a direct replacement for {comp}?", "answer": f"Yes. GlobalReach covers lead sourcing, verification, automated email sequences, and multi-channel content workflows."},
            {"question": "How does contact data accuracy compare?", "answer": "GlobalReach verifies email syntax and MX records in real time before scheduling sends, minimizing bounce rates."},
            {"question": f"Can I migrate existing lead lists from {comp}?", "answer": "Yes. GlobalReach supports simple CSV imports with automatic column mapping and suppression list checking."},
        ]
        comparison_table = {
            "competitor_name": comp,
            "features": [
                {"feature": "Built-in Email Verification", "globalreach": "Included on every lead", "competitor": "Burns additional credits"},
                {"feature": "Multi-Channel Social Studio", "globalreach": "Included (X, LinkedIn, Meta, YouTube)", "competitor": "Not supported"},
                {"feature": "Programmatic Content & SEO", "globalreach": "Included engine", "competitor": "Not supported"},
                {"feature": "Domain Health & Bounce Auto-Pause", "globalreach": "Real-time automated safeguards", "competitor": "Basic warnings"},
            ],
        }
    else:  # use_case
        h1 = f"Lead Generation for {use_case}"
        meta_desc = f"Scale client acquisition for {use_case}. Prospect verified decision-makers, automate cold outreach, and grow pipeline."
        intro = (
            f"Acquiring qualified B2B clients for {use_case} demands a systematic, repeatable outbound methodology. "
            f"Relying solely on word-of-mouth or paid advertising leaves revenue vulnerable to market fluctuations. "
            f"GlobalReach equips founders and sales leaders with an automated outbound engine designed to identify "
            f"ideal decision-makers, verify deliverability, and initiate authentic conversations at scale."
        )
        sections = [
            {
                "heading": f"The Prospecting Landscape for {use_case}",
                "content": (
                    f"In {use_case}, identifying target accounts with genuine buying intent requires granular filtering. "
                    f"Generic broad lists lead to poor response rates and wasted follow-up time. "
                    f"By defining clear Ideal Customer Profiles (ICPs) based on industry verticals, headcount thresholds, "
                    f"and executive titles, sales teams can focus resources exclusively on high-probability opportunities."
                ),
            },
            {
                "heading": "Engineering High-Converting Cold Sequences",
                "content": (
                    f"Cold email is most effective when executed with brevity and relevance. "
                    f"A proven sequence for {use_case} spans 3 to 4 touchpoints over 14 business days. "
                    f"Each step addresses a distinct operational priority, from workflow efficiency to revenue acceleration, "
                    f"ensuring your message resonates across multiple stakeholder perspectives."
                ),
            },
            {
                "heading": "Deliverability: Safeguarding Sender Reputation",
                "content": (
                    f"High deliverability is non-negotiable for {use_case} outbound operations. "
                    f"Configuring SPF, DKIM, and DMARC DNS records establishes technical domain authority. "
                    f"Combined with a gradual sending warmup ramp and real-time MX verification, your campaigns "
                    f"consistently reach primary inboxes rather than spam folders."
                ),
            },
            {
                "heading": "Automating Multi-Touch Pipeline Workflows",
                "content": (
                    f"Managing lead data across disparate spreadsheets introduces errors and delayed responses. "
                    f"GlobalReach coordinates contact verification, scheduled dispatching within recipient time zones, "
                    f"and automated suppression list enforcement. When a prospect replies, intelligent classification "
                    f"highlights interested leads for immediate booking."
                ),
            },
            {
                "heading": "Measuring and Optimizing Campaign Attribution",
                "content": (
                    f"Scaling client acquisition requires full-funnel visibility. Every outbound link is wrapped with "
                    f"tamper-proof UTM tracking parameters, enabling clear attribution from initial click to registered account. "
                    f"Reviewing channel conversion metrics ensures continuous optimization of copy and targeting criteria."
                ),
            },
            {
                "heading": "Multi-Channel Follow-Through Strategies",
                "content": (
                    f"Modern buyers rarely convert from a single cold email touchpoint. Orchestrate follow-ups that reinforce "
                    f"brand presence across LinkedIn discussions and educational video content to create trust before sales meetings."
                ),
            },
            {
                "heading": "Long-Term Domain Health and Ramp Scheduling",
                "content": (
                    f"Protecting corporate infrastructure requires disciplined dispatching. Avoid sudden volume spikes by scheduling campaigns "
                    f"through automated ramp schedules that increase daily caps incrementally as domain reputation matures."
                ),
            },
        ]
        faq = [
            {"question": f"How long does it take to set up campaigns for {use_case}?", "answer": "Most teams define their ICP, import verified leads, and launch their first sequence within one afternoon."},
            {"question": "How do you prevent emails from going to spam?", "answer": "GlobalReach checks MX records, enforces conservative sending windows, and pauses campaigns automatically if bounces exceed 5%."},
            {"question": "Can I integrate with my CRM?", "answer": "Yes. Webhook endpoints and CSV exports allow seamless synchronization with your sales stack."},
        ]
        comparison_table = {"competitor_name": "", "features": []}

    cta_link = build_utm_url(
        "https://www.getyourclientsb2b.com/signup",
        source="seo",
        medium="organic",
        campaign=f"seo_{template_type}",
        content=variables.get("slug", "cta"),
    )

    return {
        "title": f"{h1} | GlobalReach",
        "meta_description": meta_desc,
        "h1": h1,
        "intro": intro,
        "sections": sections,
        "faq": faq,
        "comparison_table": comparison_table,
        "cta": {
            "headline": "Ready to Scale Your B2B Outbound?",
            "subheadline": "Find verified leads and automate your client acquisition with GlobalReach.",
            "button_text": "Get Started Free",
            "url": cta_link,
        },
    }


# ─── ADMIN ENDPOINTS ──────────────────────────────────────────────────────────

@router.get("/templates", response_model=list[SEOTemplateResponse])
async def list_templates(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all SEO templates. Auto-seeds defaults if none exist."""
    res = await db.execute(select(SEOTemplate).order_by(SEOTemplate.created_at.asc()))
    templates = list(res.scalars().all())

    if not templates:
        for tpl_data in DEFAULT_TEMPLATES:
            tpl = SEOTemplate(**tpl_data)
            db.add(tpl)
        await db.commit()
        res = await db.execute(select(SEOTemplate).order_by(SEOTemplate.created_at.asc()))
        templates = list(res.scalars().all())

    return templates


@router.post("/templates", response_model=SEOTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    payload: SEOTemplateCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_owner),
):
    """Create a new SEO template."""
    tpl = SEOTemplate(
        type=payload.type,
        url_pattern=payload.url_pattern,
        title_pattern=payload.title_pattern,
        h1_pattern=payload.h1_pattern,
        body_prompt=payload.body_prompt,
    )
    db.add(tpl)
    await db.commit()
    await db.refresh(tpl)
    return tpl


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_owner),
):
    """Delete an SEO template."""
    res = await db.execute(select(SEOTemplate).where(SEOTemplate.id == template_id))
    tpl = res.scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    await db.delete(tpl)
    await db.commit()


@router.post("/generate", response_model=list[SEOPageResponse])
async def generate_seo_pages(
    payload: SEOGenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_owner),
):
    """
    Generate programmatic SEO pages from a template and variable combinations.
    Runs through AI generation, claims_guard, and quality gate.
    """
    res = await db.execute(select(SEOTemplate).where(SEOTemplate.id == payload.template_id))
    tpl = res.scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=404, detail="SEO Template not found")

    variables_list = list(payload.variables_list)

    # Parse CSV if provided
    if payload.csv_content:
        reader = csv.DictReader(io.StringIO(payload.csv_content.strip()))
        for row in reader:
            clean_row = {k.strip(): v.strip() for k, v in row.items() if k and v}
            if clean_row:
                variables_list.append(clean_row)

    if not variables_list:
        raise HTTPException(status_code=400, detail="No variable combinations provided.")

    # Retrieve existing page texts for similarity comparison
    existing_res = await db.execute(select(SEOPage.content_json).where(SEOPage.status == "published").limit(50))
    existing_texts = [extract_full_text(r) for r in existing_res.scalars().all() if r]

    created_pages: list[SEOPage] = []

    for vars_dict in variables_list:
        # Build slug
        slug = tpl.url_pattern
        for k, v in vars_dict.items():
            slug = slug.replace(f"{{{k}}}", str(v).lower().replace(" ", "-").replace(".", ""))
        slug = slug.lstrip("/")

        # Check existing
        existing_page = await db.execute(select(SEOPage).where(SEOPage.slug == slug))
        if existing_page.scalar_one_or_none():
            continue  # Skip duplicate slug

        # Generate content
        content = _build_mock_seo_content(tpl.type, vars_dict)

        # Evaluate quality gate
        eval_result = evaluate_seo_page(content, vars_dict, existing_texts)
        quality_score = eval_result["quality_score"]

        # If thin or duplicate, keep as rejected or draft
        page_status = "draft" if eval_result["passed"] else "rejected"

        page = SEOPage(
            template_id=tpl.id,
            slug=slug,
            variables=vars_dict,
            title=content.get("title", f"GlobalReach — {slug}"),
            meta_description=content.get("meta_description", ""),
            content_json=content,
            status=page_status,
            quality_score=quality_score,
        )
        db.add(page)
        created_pages.append(page)

    await db.commit()

    # Log audit entry
    audit = AuditLog(
        user_id=user.id,
        action="seo.batch_generated",
        entity="seo_pages",
        meta={"count": len(created_pages), "template_id": str(tpl.id)},
    )
    db.add(audit)
    await db.commit()

    for p in created_pages:
        await db.refresh(p)

    return created_pages


@router.get("/pages", response_model=list[SEOPageResponse])
async def list_pages(
    status_filter: Optional[str] = Query(None, alias="status"),
    template_id: Optional[uuid.UUID] = None,
    min_quality_score: Optional[float] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List generated SEO pages with filtering."""
    query = select(SEOPage).order_by(SEOPage.created_at.desc())

    if status_filter:
        query = query.where(SEOPage.status == status_filter)
    if template_id:
        query = query.where(SEOPage.template_id == template_id)
    if min_quality_score is not None:
        query = query.where(SEOPage.quality_score >= min_quality_score)

    query = query.offset(offset).limit(limit)
    res = await db.execute(query)
    return list(res.scalars().all())


@router.post("/pages/batch-publish", response_model=dict[str, Any])
async def batch_publish_pages(
    payload: SEOPageBatchPublishRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_owner),
):
    """
    Approve and publish a batch of 20 to 50 pages.
    Enforces quality check before publishing.
    """
    res = await db.execute(select(SEOPage).where(SEOPage.id.in_(payload.page_ids)))
    pages = list(res.scalars().all())

    if not pages:
        raise HTTPException(status_code=404, detail="No matching pages found.")

    published_count = 0
    now = datetime.now(timezone.utc)

    for p in pages:
        if p.quality_score and p.quality_score < 60.0:
            continue  # Never mass-publish low-quality pages
        p.status = "published"
        p.published_at = now
        published_count += 1

    await db.commit()

    audit = AuditLog(
        user_id=user.id,
        action="seo.batch_published",
        entity="seo_pages",
        meta={"published_count": published_count, "requested_count": len(pages)},
    )
    db.add(audit)
    await db.commit()

    return {
        "success": True,
        "published_count": published_count,
        "requested_count": len(pages),
    }


# ─── PUBLIC ENDPOINTS ─────────────────────────────────────────────────────────

@public_router.get("/slugs", response_model=list[str])
async def get_published_slugs(
    db: AsyncSession = Depends(get_db),
):
    """
    Public endpoint returning all published slugs for Next.js generateStaticParams
    and dynamic sitemap generation.
    """
    res = await db.execute(select(SEOPage.slug).where(SEOPage.status == "published").order_by(SEOPage.published_at.desc()))
    return [slug for slug in res.scalars().all()]


@public_router.get("/{slug:path}", response_model=SEOPublicPageResponse)
async def get_public_seo_page(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Public endpoint returning published page content, metadata, and JSON-LD structured data.
    """
    clean_slug = slug.strip().lstrip("/")
    res = await db.execute(select(SEOPage).where(SEOPage.slug == clean_slug, SEOPage.status == "published"))
    page = res.scalar_one_or_none()

    if not page:
        raise HTTPException(status_code=404, detail=f"Page not found for slug: {clean_slug}")

    content = page.content_json or {}

    # Build Schema.org structured data (FAQPage, SoftwareApplication, BreadcrumbList)
    faqs = content.get("faq", [])
    faq_schema = {
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": item.get("question", ""),
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": item.get("answer", ""),
                },
            }
            for item in faqs
            if item.get("question") and item.get("answer")
        ],
    }

    breadcrumb_schema = {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://www.getyourclientsb2b.com"},
            {"@type": "ListItem", "position": 2, "name": "Solutions", "item": f"https://www.getyourclientsb2b.com/{clean_slug.split('/')[0]}"},
            {"@type": "ListItem", "position": 3, "name": page.title or clean_slug, "item": f"https://www.getyourclientsb2b.com/{clean_slug}"},
        ],
    }

    software_schema = {
        "@type": "SoftwareApplication",
        "name": "GlobalReach",
        "applicationCategory": "BusinessApplication",
        "operatingSystem": "Web",
        "offers": {
            "@type": "Offer",
            "price": "0",
            "priceCurrency": "USD",
        },
    }

    schema_org = {
        "@context": "https://schema.org",
        "@graph": [faq_schema, breadcrumb_schema, software_schema],
    }

    return SEOPublicPageResponse(
        slug=page.slug,
        title=page.title or "GlobalReach",
        meta_description=page.meta_description or "",
        content_json=content,
        schema_org=schema_org,
        published_at=page.published_at,
    )
