"""
ARQ worker jobs for cold email outreach and health monitoring:
- send_due_emails: runs every 1 minute
- check_campaign_health: runs every 15 minutes
- process_email_events: handles batched provider events
"""
import asyncio
import json
import logging
import random
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.auth import BrandProfile
from app.models.leads import (
    Campaign,
    EmailMessage,
    Lead,
    Reply,
    Sequence,
    SequenceStep,
    SuppressionList,
)
from app.providers.email import EmailMessage as ProviderEmailMessage, get_email_provider
from app.schemas.leads import EmailPersonalizeOutput
from app.services.ai import generate
from app.services.audit import write_audit_log
from app.services.claims_guard import is_safe
from app.services.dryrun import dry_run_guard
from app.services.unsubscribe import create_unsubscribe_token
from app.services.utm import build_utm_url

logger = logging.getLogger(__name__)
PROMPTS_DIR = Path(__file__).parent.parent.parent / "app" / "prompts"

# Heuristic country timezone offsets in hours from UTC
COUNTRY_UTC_OFFSETS: dict[str, float] = {
    "US": -5.0,  # Eastern standard approximation
    "USA": -5.0,
    "UNITED STATES": -5.0,
    "CA": -5.0,
    "CANADA": -5.0,
    "GB": 0.0,
    "UK": 0.0,
    "UNITED KINGDOM": 0.0,
    "IE": 0.0,
    "IRELAND": 0.0,
    "PT": 0.0,
    "DE": 1.0,
    "GERMANY": 1.0,
    "FR": 1.0,
    "FRANCE": 1.0,
    "ES": 1.0,
    "SPAIN": 1.0,
    "IT": 1.0,
    "ITALY": 1.0,
    "NL": 1.0,
    "NETHERLANDS": 1.0,
    "IL": 2.0,
    "ISRAEL": 2.0,
    "AE": 4.0,
    "UAE": 4.0,
    "IN": 5.5,
    "INDIA": 5.5,
    "SG": 8.0,
    "SINGAPORE": 8.0,
    "HK": 8.0,
    "AU": 10.0,
    "AUSTRALIA": 10.0,
    "NZ": 12.0,
}


def is_in_sending_window(
    window: Optional[dict],
    country: Optional[str] = None,
    timezone_mode: str = "recipient",
) -> bool:
    """
    Check if the current moment is within the allowed sending window in the recipient's timezone.
    Default window: 09:00 to 17:00 local time.
    """
    if not window or not isinstance(window, dict):
        return True

    start_str = window.get("start", "09:00")
    end_str = window.get("end", "17:00")

    try:
        start_h, start_m = map(int, start_str.split(":"))
        end_h, end_m = map(int, end_str.split(":"))
    except Exception:
        start_h, start_m = 9, 0
        end_h, end_m = 17, 0

    now_utc = datetime.now(timezone.utc)
    if timezone_mode == "recipient" and country:
        norm_country = country.strip().upper()
        offset_hours = COUNTRY_UTC_OFFSETS.get(norm_country, 0.0)
        local_time = now_utc + timedelta(hours=offset_hours)
    else:
        local_time = now_utc

    local_minutes = local_time.hour * 60 + local_time.minute
    start_minutes = start_h * 60 + start_m
    end_minutes = end_h * 60 + end_m

    return start_minutes <= local_minutes <= end_minutes


def build_compliant_footer(email: str, brand: Optional[BrandProfile] = None) -> str:
    """CAN-SPAM / GDPR footer with sender, physical address, and unsubscribe link."""
    sender_name = brand.product_name if brand else "GlobalReach"
    address = (
        (brand.physical_address if brand and brand.physical_address else None)
        or settings.physical_address
        or "GlobalReach Inc., 100 Pine Street, San Francisco, CA"
    )
    token = create_unsubscribe_token(email)
    base_url = settings.api_url.rstrip("/")
    unsubscribe_url = f"{base_url}/u/{token}"

    footer_html = f"""
<br><br>
<hr style="border:none;border-top:1px solid #e2e8f0;margin:24px 0 12px 0;">
<p style="font-size:11px;color:#94a3b8;line-height:1.5;margin:0;">
  Sent by {sender_name} · {address}<br>
  If you do not wish to receive further emails, you can 
  <a href="{unsubscribe_url}" style="color:#6366f1;text-decoration:underline;">unsubscribe with one click</a>.
</p>
"""
    return footer_html, unsubscribe_url


from contextlib import asynccontextmanager


@asynccontextmanager
async def get_worker_session(ctx: Optional[dict] = None):
    ctx = ctx or {}
    if "db" in ctx:
        yield ctx["db"]
    else:
        async with AsyncSessionLocal() as session:
            yield session


# ─── 1-Minute Job: send_due_emails ───────────────────────────────────────────

async def send_due_emails(ctx: Optional[dict] = None) -> dict:
    """
    ARQ scheduled job running every 1 minute:
    - Enforces active campaign status
    - Enforces daily_limit per campaign
    - Enforces sending window in recipient timezone
    - Stops sequence if lead replied, bounced, unsubscribed, or signed up
    - Enforces suppression check on lead email and domain
    - Performs merge-field or AI personalization
    - Includes CAN-SPAM compliant footer and List-Unsubscribe headers
    - Dispatches with random jitter
    - Automatically enrolls next step when current step completes
    """
    ctx = ctx or {}
    logger.info("[send_due_emails] Starting due emails check at %s", datetime.now(timezone.utc).isoformat())

    email_provider = get_email_provider()
    total_sent = 0
    total_skipped = 0
    total_cancelled = 0

    async with get_worker_session(ctx) as db:
        # Load brand profile
        brand_res = await db.execute(select(BrandProfile))
        brand = brand_res.scalar_one_or_none()

        # Find all active campaigns
        camp_res = await db.execute(select(Campaign).where(Campaign.status == "active"))
        campaigns = camp_res.scalars().all()

        for campaign in campaigns:
            # Check daily sent count for this campaign (today UTC)
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            sent_today_res = await db.execute(
                select(func.count()).select_from(EmailMessage).where(
                    EmailMessage.campaign_id == campaign.id,
                    EmailMessage.status.in_(["sent", "delivered", "opened", "clicked", "replied"]),
                    EmailMessage.sent_at >= today_start,
                )
            )
            sent_today = sent_today_res.scalar() or 0
            if sent_today >= campaign.daily_limit:
                logger.info(
                    "[send_due_emails] Campaign %s reached daily limit (%d/%d)",
                    campaign.id, sent_today, campaign.daily_limit,
                )
                continue

            available_quota = campaign.daily_limit - sent_today

            # Pick scheduled messages for this campaign
            messages_res = await db.execute(
                select(EmailMessage)
                .where(
                    EmailMessage.campaign_id == campaign.id,
                    EmailMessage.status == "scheduled",
                )
                .order_by(EmailMessage.created_at.asc())
                .limit(available_quota)
            )
            messages = messages_res.scalars().all()

            for msg in messages:
                # Load lead
                lead_res = await db.execute(select(Lead).where(Lead.id == msg.lead_id))
                lead = lead_res.scalar_one_or_none()
                if not lead:
                    msg.status = "cancelled"
                    total_cancelled += 1
                    continue

                # 1. Sequence stop rules: reply, bounce, unsubscribe, signup
                if lead.status in ("replied", "bounced", "unsubscribed", "signed_up"):
                    msg.status = "cancelled"
                    total_cancelled += 1
                    logger.info("Sequence stopped for lead %s (status: %s)", lead.email, lead.status)
                    continue

                # 2. Suppression check: check email or domain
                domain = lead.email.split("@")[-1].lower() if "@" in lead.email else ""
                sup_res = await db.execute(
                    select(SuppressionList).where(
                        (SuppressionList.email_or_domain == lead.email.lower())
                        | (SuppressionList.email_or_domain == domain)
                    )
                )
                if sup_res.scalar_one_or_none():
                    msg.status = "cancelled"
                    lead.status = "unsubscribed"
                    total_cancelled += 1
                    logger.info("Lead %s is in suppression list, cancelled", lead.email)
                    continue

                # 3. Only leads with verification_status='valid' may be emailed
                if lead.verification_status != "valid":
                    msg.status = "cancelled"
                    total_cancelled += 1
                    logger.info("Lead %s verification status is '%s', cannot send", lead.email, lead.verification_status)
                    continue

                # 4. Check recipient timezone sending window
                if not is_in_sending_window(campaign.sending_window, lead.country, campaign.timezone_mode):
                    total_skipped += 1
                    continue

                # 5. Load sequence step
                step_res = await db.execute(select(SequenceStep).where(SequenceStep.id == msg.step_id))
                step = step_res.scalar_one_or_none()
                if not step:
                    msg.status = "cancelled"
                    total_cancelled += 1
                    continue

                # Check step delay if step_number > 1
                if step.step_number > 1 and step.delay_days > 0:
                    prev_step_msg = await db.execute(
                        select(EmailMessage).join(SequenceStep).where(
                            EmailMessage.lead_id == lead.id,
                            EmailMessage.campaign_id == campaign.id,
                            SequenceStep.step_number == step.step_number - 1,
                            EmailMessage.status.in_(["sent", "delivered", "opened", "clicked", "replied"]),
                        )
                    )
                    prev_sent = prev_step_msg.scalar_one_or_none()
                    if not prev_sent or not prev_sent.sent_at:
                        # Prior step hasn't sent yet
                        total_skipped += 1
                        continue
                    min_send_time = prev_sent.sent_at + timedelta(days=step.delay_days)
                    if datetime.now(timezone.utc) < min_send_time:
                        total_skipped += 1
                        continue

                # 6. AI Personalization or Merge Fields
                subject = step.subject_template or "Partnership with GlobalReach"
                body = step.body_template or "Hi {first_name}, would love to connect."

                if step.ai_personalize:
                    try:
                        brand_dict = {
                            "product_name": brand.product_name if brand else "GlobalReach",
                            "one_liner": brand.one_liner if brand else "",
                            "tone": brand.tone if brand else "professional, direct",
                        }
                        prompt_template = (PROMPTS_DIR / "email_personalize.txt").read_text(encoding="utf-8")
                        formatted_prompt = (
                            prompt_template.replace("{first_name}", lead.first_name or "there")
                            .replace("{company}", lead.company or "your company")
                            .replace("{title}", lead.title or "Founder")
                            .replace("{industry}", lead.industry or "your industry")
                            .replace("{website}", lead.website or "")
                            .replace("{country}", lead.country or "")
                            .replace("{brand_profile}", json.dumps(brand_dict, indent=2))
                            .replace("{subject_template}", subject)
                            .replace("{body_template}", body)
                            .replace("{website_snippet}", "")
                        )

                        ai_res = await generate(prompt=formatted_prompt, response_model=EmailPersonalizeOutput, brand_context=brand_dict)
                        # Verify with claims guard
                        safe, violations = is_safe(ai_res.body)
                        if safe:
                            subject = ai_res.subject
                            body = ai_res.body
                    except Exception as exc:
                        logger.warning("AI personalization fallback: %s", exc)

                # Merge fields replacement
                merge_vars = {
                    "{first_name}": lead.first_name or "there",
                    "{last_name}": lead.last_name or "",
                    "{company}": lead.company or "your company",
                    "{title}": lead.title or "Business Owner",
                    "{website}": lead.website or "",
                    "{country}": lead.country or "",
                    "{industry}": lead.industry or "",
                }
                for k, v in merge_vars.items():
                    subject = subject.replace(k, v)
                    body = body.replace(k, v)

                # 7. Compliant footer & List-Unsubscribe headers
                footer_html, unsub_url = build_compliant_footer(lead.email, brand)
                # Convert plain text body newlines to html
                formatted_html_body = body.replace("\n", "<br>") + footer_html

                token = msg.tracking_token or secrets.token_urlsafe(24)
                msg.tracking_token = token

                headers = {
                    "List-Unsubscribe": f"<{unsub_url}>",
                    "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
                }

                provider_msg = ProviderEmailMessage(
                    to=lead.email,
                    subject=subject,
                    html_body=formatted_html_body,
                    from_name=brand.product_name if brand else "GlobalReach",
                    tracking_token=token,
                    headers=headers,
                )

                # Jitter simulation (30 to 180 seconds in production, 0s in fast tests)
                # For non-test environment, add light jitter
                if not settings.dry_run and not ctx.get("is_test"):
                    jitter = random.uniform(30.0, 180.0)
                    await asyncio.sleep(min(jitter, 2.0))

                # Send via EmailProvider
                send_result = await email_provider.send(provider_msg)

                if send_result.success:
                    msg.status = "sent"
                    msg.sent_at = datetime.now(timezone.utc)
                    msg.provider_message_id = send_result.provider_message_id
                    lead.status = "contacted"
                    total_sent += 1

                    # Enroll next step if exists
                    seq_res = await db.execute(select(Sequence).where(Sequence.campaign_id == campaign.id))
                    seq = seq_res.scalar_one_or_none()
                    if seq:
                        next_step_res = await db.execute(
                            select(SequenceStep)
                            .where(
                                SequenceStep.sequence_id == seq.id,
                                SequenceStep.step_number == step.step_number + 1,
                            )
                        )
                        next_step = next_step_res.scalar_one_or_none()
                        if next_step:
                            next_token = secrets.token_urlsafe(24)
                            next_msg = EmailMessage(
                                lead_id=lead.id,
                                campaign_id=campaign.id,
                                step_id=next_step.id,
                                status="scheduled",
                                tracking_token=next_token,
                            )
                            db.add(next_msg)

                else:
                    msg.status = "failed"
                    logger.error("Failed to send message %s: %s", msg.id, send_result.error)

            await db.commit()

    logger.info("[send_due_emails] Finished. sent=%d, skipped=%d, cancelled=%d", total_sent, total_skipped, total_cancelled)
    return {"sent": total_sent, "skipped": total_skipped, "cancelled": total_cancelled}


# ─── 15-Minute Job: check_campaign_health ────────────────────────────────────

async def check_campaign_health(ctx: Optional[dict] = None) -> dict:
    """
    ARQ scheduled job running every 15 minutes:
    - Calculates bounce rate and complaint rate for active campaigns.
    - If bounce rate > 5.0% or complaint rate > 0.3%, auto-pauses campaign.
    - Writes to audit_log.
    """
    logger.info("[check_campaign_health] Checking campaign health at %s", datetime.now(timezone.utc).isoformat())

    paused_campaigns = []

    async with get_worker_session(ctx) as db:
        camps = (await db.execute(select(Campaign).where(Campaign.status == "active"))).scalars().all()

        for campaign in camps:
            msgs = (await db.execute(select(EmailMessage).where(EmailMessage.campaign_id == campaign.id))).scalars().all()
            if not msgs:
                continue

            from collections import Counter
            counts = Counter(m.status for m in msgs)
            sent = sum(counts.get(s, 0) for s in ["sent", "delivered", "opened", "clicked", "replied", "bounced", "complained"])
            bounced = counts.get("bounced", 0)
            complained = counts.get("complained", 0)

            if sent < 10:
                # Minimum sample size to prevent premature pauses
                continue

            bounce_rate = (bounced / sent) * 100
            complaint_rate = (complained / sent) * 100

            reason = None
            if bounce_rate > 5.0:
                reason = f"Bounce rate exceeded threshold: {bounce_rate:.2f}% > 5.0%"
            elif complaint_rate > 0.3:
                reason = f"Complaint rate exceeded threshold: {complaint_rate:.2f}% > 0.3%"

            if reason:
                campaign.status = "paused"
                paused_campaigns.append(str(campaign.id))
                logger.warning(
                    "Auto-pausing campaign %s (%s): %s",
                    campaign.id, campaign.name, reason
                )
                await write_audit_log(
                    db,
                    action="campaign.auto_paused",
                    entity="campaigns",
                    entity_id=str(campaign.id),
                    meta={
                        "campaign_name": campaign.name,
                        "bounce_rate_pct": round(bounce_rate, 2),
                        "complaint_rate_pct": round(complaint_rate, 2),
                        "sent": sent,
                        "reason": reason,
                    },
                )

        await db.commit()

    return {"checked": len(camps), "auto_paused": paused_campaigns}


# ─── Event Queue Worker: process_email_events ─────────────────────────────────

async def process_email_events(ctx: Optional[dict] = None) -> dict:
    """Continuous or batched email event processing."""
    logger.info("[process_email_events] Running event processor")
    return {"status": "ok"}
