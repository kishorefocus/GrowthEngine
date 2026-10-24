"""
Campaigns router:
- CRUD for campaigns, sequences, sequence steps
- AI personalization preview
- Pause/resume campaigns
- Per-step stats
- Lead enrollment
- Domain health check
- GET /campaigns/{id}/stats
"""
import json
import logging
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import BrandProfile, User
from app.models.leads import Campaign, EmailMessage, Lead, Reply, Sequence, SequenceStep
from app.schemas.leads import (
    AddLeadsToCampaignRequest,
    CampaignCreate,
    CampaignResponse,
    CampaignStats,
    CampaignUpdate,
    DomainHealthResponse,
    EmailPersonalizeOutput,
    PersonalizePreviewRequest,
    PersonalizePreviewResponse,
    SequenceResponse,
    SequenceStepCreate,
    SequenceStepResponse,
    SequenceStepUpdate,
    StepStats,
)
from app.services.ai import generate
from app.services.audit import write_audit_log
from app.services.claims_guard import is_safe
from app.services.domain_health import check_domain_health

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _campaign_to_response(c: Campaign) -> CampaignResponse:
    return CampaignResponse(
        id=str(c.id),
        name=c.name,
        icp_id=str(c.icp_id) if c.icp_id else None,
        status=c.status,
        daily_limit=c.daily_limit,
        sending_window=c.sending_window,
        timezone_mode=c.timezone_mode,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


def _step_to_response(s: SequenceStep) -> SequenceStepResponse:
    return SequenceStepResponse(
        id=str(s.id),
        sequence_id=str(s.sequence_id),
        step_number=s.step_number,
        delay_days=s.delay_days,
        subject_template=s.subject_template,
        body_template=s.body_template,
        ai_personalize=s.ai_personalize,
        created_at=s.created_at,
    )


def _to_uuid(val: str | uuid.UUID, detail: str = "Campaign not found.") -> uuid.UUID:
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(status_code=404, detail=detail)


# ─── Campaign CRUD ────────────────────────────────────────────────────────────

@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    body: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a campaign and automatically create its default sequence."""
    c = Campaign(
        name=body.name,
        icp_id=uuid.UUID(body.icp_id) if body.icp_id else None,
        daily_limit=body.daily_limit,
        sending_window=body.sending_window.model_dump() if body.sending_window else None,
        timezone_mode=body.timezone_mode,
    )
    db.add(c)
    await db.flush()
    # Auto-create a sequence
    seq = Sequence(campaign_id=c.id)
    db.add(seq)
    await write_audit_log(db, "campaign.created", user_id=current_user.id, entity="campaigns", entity_id=str(c.id))
    await db.commit()
    await db.refresh(c)
    return _campaign_to_response(c)


@router.get("", response_model=list[CampaignResponse])
async def list_campaigns(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Campaign).order_by(Campaign.created_at.desc()))
    return [_campaign_to_response(c) for c in result.scalars()]


@router.get("/domain-health", response_model=DomainHealthResponse)
async def domain_health(
    domain: Optional[str] = Query(None),
    dkim_selector: str = Query("default"),
    _: User = Depends(get_current_user),
):
    """Check SPF, DKIM, DMARC records for the sending domain."""
    target_domain = domain or settings.sending_domain
    if not target_domain:
        raise HTTPException(status_code=400, detail="No SENDING_DOMAIN configured. Pass ?domain= to check a domain.")
    result = await check_domain_health(target_domain, dkim_selector=dkim_selector)
    return DomainHealthResponse(**result)


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    cid = _to_uuid(campaign_id)
    result = await db.execute(select(Campaign).where(Campaign.id == cid))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    return _campaign_to_response(c)


@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: str,
    body: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cid = _to_uuid(campaign_id)
    result = await db.execute(select(Campaign).where(Campaign.id == cid))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    for field, value in body.model_dump(exclude_none=True).items():
        if field == "sending_window" and value:
            setattr(c, field, value if isinstance(value, dict) else value.model_dump())
        else:
            setattr(c, field, value)
    await write_audit_log(db, "campaign.updated", user_id=current_user.id, entity="campaigns", entity_id=campaign_id)
    await db.commit()
    await db.refresh(c)
    return _campaign_to_response(c)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cid = _to_uuid(campaign_id)
    result = await db.execute(select(Campaign).where(Campaign.id == cid))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    await write_audit_log(db, "campaign.deleted", user_id=current_user.id, entity="campaigns", entity_id=campaign_id)
    await db.delete(c)
    await db.commit()


# ─── Pause / Resume ───────────────────────────────────────────────────────────

@router.post("/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cid = _to_uuid(campaign_id)
    result = await db.execute(select(Campaign).where(Campaign.id == cid))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    if c.status not in ("active", "draft"):
        raise HTTPException(status_code=400, detail=f"Cannot pause campaign in status '{c.status}'.")
    c.status = "paused"
    await write_audit_log(db, "campaign.paused", user_id=current_user.id, entity="campaigns", entity_id=campaign_id)
    await db.commit()
    return {"status": "paused"}


@router.post("/{campaign_id}/resume")
@router.post("/{campaign_id}/launch")
async def resume_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cid = _to_uuid(campaign_id)
    result = await db.execute(select(Campaign).where(Campaign.id == cid))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    if c.status not in ("paused", "draft"):
        raise HTTPException(status_code=400, detail=f"Campaign is not paused or in draft (status: '{c.status}').")
    action = "campaign.launched" if c.status == "draft" else "campaign.resumed"
    c.status = "active"
    await write_audit_log(db, action, user_id=current_user.id, entity="campaigns", entity_id=campaign_id)
    await db.commit()
    return {"status": "active"}


# ─── Campaign Stats ───────────────────────────────────────────────────────────

@router.get("/{campaign_id}/stats", response_model=CampaignStats)
async def campaign_stats(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Aggregate per-campaign stats from email_messages."""
    cid = _to_uuid(campaign_id)
    result = await db.execute(select(Campaign).where(Campaign.id == cid))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Campaign not found.")

    def _count(stat: str) -> int:
        return 0  # placeholder — filled below

    msgs = (await db.execute(
        select(EmailMessage).where(EmailMessage.campaign_id == cid)
    )).scalars().all()

    totals = {"sent": 0, "delivered": 0, "opened": 0, "clicked": 0,
              "replied": 0, "bounced": 0, "complained": 0}
    for m in msgs:
        if m.status in totals:
            totals[m.status] += 1
        if m.status in ("delivered", "opened", "clicked", "replied"):
            totals["delivered"] += 1 if m.status == "delivered" else 0
        if m.status in ("sent", "delivered", "opened", "clicked", "replied"):
            totals["sent"] = totals.get("sent", 0)

    # Re-count properly
    from collections import Counter
    counts = Counter(m.status for m in msgs)
    sent = sum(counts.get(s, 0) for s in ["sent", "delivered", "opened", "clicked", "replied", "bounced", "complained"])
    delivered = sum(counts.get(s, 0) for s in ["delivered", "opened", "clicked", "replied"])
    bounced = counts.get("bounced", 0)
    complained = counts.get("complained", 0)
    opened = counts.get("opened", 0)
    clicked = counts.get("clicked", 0)
    replied = counts.get("replied", 0)

    return CampaignStats(
        campaign_id=campaign_id,
        total_leads=len(msgs),
        sent=sent,
        delivered=delivered,
        opened=opened,
        clicked=clicked,
        replied=replied,
        bounced=bounced,
        complained=complained,
        bounce_rate_pct=round(bounced / sent * 100, 2) if sent > 0 else 0.0,
        complaint_rate_pct=round(complained / sent * 100, 2) if sent > 0 else 0.0,
        reply_rate_pct=round(replied / sent * 100, 2) if sent > 0 else 0.0,
    )


# ─── Lead Enrollment ─────────────────────────────────────────────────────────

@router.post("/{campaign_id}/enroll")
async def enroll_leads(
    campaign_id: str,
    body: AddLeadsToCampaignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Enroll verified leads into a campaign. Creates email_message records
    for the first step of the campaign's sequence.
    Only leads with verification_status='valid' may be enrolled.
    """
    cid = _to_uuid(campaign_id)
    result = await db.execute(select(Campaign).where(Campaign.id == cid))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    # Get sequence + first step
    seq_result = await db.execute(select(Sequence).where(Sequence.campaign_id == cid))
    seq = seq_result.scalar_one_or_none()
    if not seq:
        raise HTTPException(status_code=400, detail="Campaign has no sequence.")

    step_result = await db.execute(
        select(SequenceStep)
        .where(SequenceStep.sequence_id == seq.id)
        .order_by(SequenceStep.step_number)
        .limit(1)
    )
    first_step = step_result.scalar_one_or_none()
    if not first_step:
        raise HTTPException(status_code=400, detail="Campaign sequence has no steps.")

    enrolled = 0
    skipped = []

    for lead_id in body.lead_ids:
        lid = _to_uuid(lead_id, "Lead not found.")
        lead_result = await db.execute(select(Lead).where(Lead.id == lid))
        lead = lead_result.scalar_one_or_none()
        if not lead:
            skipped.append({"id": lead_id, "reason": "not_found"})
            continue
        if lead.verification_status != "valid":
            skipped.append({"id": lead_id, "reason": f"verification_status={lead.verification_status}"})
            continue

        # Check for existing message for this step
        existing_msg = await db.execute(
            select(EmailMessage).where(
                EmailMessage.lead_id == lead.id,
                EmailMessage.campaign_id == cid,
                EmailMessage.step_id == first_step.id,
            )
        )
        if existing_msg.scalar_one_or_none():
            skipped.append({"id": lead_id, "reason": "already_enrolled"})
            continue

        import secrets
        token = secrets.token_urlsafe(24)
        msg = EmailMessage(
            lead_id=lead.id,
            campaign_id=cid,
            step_id=first_step.id,
            status="scheduled",
            tracking_token=token,
        )
        db.add(msg)
        lead.status = "queued"
        enrolled += 1

    await write_audit_log(
        db, "campaign.leads_enrolled", user_id=current_user.id,
        entity="campaigns", entity_id=campaign_id,
        meta={"enrolled": enrolled, "skipped": len(skipped)}
    )
    await db.commit()
    return {"enrolled": enrolled, "skipped": skipped}


# ─── Sequences ────────────────────────────────────────────────────────────────

@router.get("/{campaign_id}/sequence", response_model=SequenceResponse)
async def get_sequence(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    cid = _to_uuid(campaign_id)
    seq_result = await db.execute(select(Sequence).where(Sequence.campaign_id == cid))
    seq = seq_result.scalar_one_or_none()
    if not seq:
        raise HTTPException(status_code=404, detail="Sequence not found.")
    return SequenceResponse(id=str(seq.id), campaign_id=str(seq.campaign_id), created_at=seq.created_at)


# ─── Sequence Steps ───────────────────────────────────────────────────────────

@router.get("/{campaign_id}/steps", response_model=list[SequenceStepResponse])
async def list_steps(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    cid = _to_uuid(campaign_id)
    seq_result = await db.execute(select(Sequence).where(Sequence.campaign_id == cid))
    seq = seq_result.scalar_one_or_none()
    if not seq:
        raise HTTPException(status_code=404, detail="Sequence not found.")
    result = await db.execute(
        select(SequenceStep).where(SequenceStep.sequence_id == seq.id).order_by(SequenceStep.step_number)
    )
    return [_step_to_response(s) for s in result.scalars()]


@router.post("/{campaign_id}/steps", response_model=SequenceStepResponse, status_code=status.HTTP_201_CREATED)
async def create_step(
    campaign_id: str,
    body: SequenceStepCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cid = _to_uuid(campaign_id)
    seq_result = await db.execute(select(Sequence).where(Sequence.campaign_id == cid))
    seq = seq_result.scalar_one_or_none()
    if not seq:
        raise HTTPException(status_code=404, detail="Sequence not found.")
    step = SequenceStep(
        sequence_id=seq.id,
        step_number=body.step_number,
        delay_days=body.delay_days,
        subject_template=body.subject_template,
        body_template=body.body_template,
        ai_personalize=body.ai_personalize,
    )
    db.add(step)
    await db.flush()
    await write_audit_log(db, "step.created", user_id=current_user.id, entity="sequence_steps", entity_id=str(step.id))
    await db.commit()
    await db.refresh(step)
    return _step_to_response(step)


@router.put("/{campaign_id}/steps/{step_id}", response_model=SequenceStepResponse)
async def update_step(
    campaign_id: str,
    step_id: str,
    body: SequenceStepUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sid = _to_uuid(step_id, "Step not found.")
    result = await db.execute(select(SequenceStep).where(SequenceStep.id == sid))
    step = result.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found.")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(step, field, value)
    await db.commit()
    await db.refresh(step)
    return _step_to_response(step)


@router.delete("/{campaign_id}/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_step(
    campaign_id: str,
    step_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sid = _to_uuid(step_id, "Step not found.")
    result = await db.execute(select(SequenceStep).where(SequenceStep.id == sid))
    step = result.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found.")
    await db.delete(step)
    await db.commit()


# ─── Per-Step Stats ───────────────────────────────────────────────────────────

@router.get("/{campaign_id}/steps/{step_id}/stats", response_model=StepStats)
async def step_stats(
    campaign_id: str,
    step_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    sid = _to_uuid(step_id, "Step not found.")
    result = await db.execute(select(SequenceStep).where(SequenceStep.id == sid))
    step = result.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found.")
    msgs = (await db.execute(
        select(EmailMessage).where(EmailMessage.step_id == sid)
    )).scalars().all()
    from collections import Counter
    counts = Counter(m.status for m in msgs)
    sent = sum(counts.get(s, 0) for s in ["sent", "delivered", "opened", "clicked", "replied", "bounced"])
    return StepStats(
        step_id=step_id,
        step_number=step.step_number,
        sent=sent,
        delivered=counts.get("delivered", 0),
        opened=counts.get("opened", 0),
        clicked=counts.get("clicked", 0),
        replied=counts.get("replied", 0),
        bounced=counts.get("bounced", 0),
    )


# ─── AI Personalization Preview ───────────────────────────────────────────────

@router.post("/{campaign_id}/preview-ai", response_model=PersonalizePreviewResponse)
async def preview_ai_email(
    campaign_id: str,
    body: PersonalizePreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Preview AI-personalized email for a lead + step.
    Human reviews before any send. Runs claims guard.
    """
    lead_result = await db.execute(select(Lead).where(Lead.id == body.lead_id))
    lead = lead_result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    step_result = await db.execute(select(SequenceStep).where(SequenceStep.id == body.step_id))
    step = step_result.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found.")

    brand_result = await db.execute(select(BrandProfile))
    brand = brand_result.scalar_one_or_none()
    brand_dict = {}
    if brand:
        brand_dict = {
            "product_name": brand.product_name,
            "one_liner": brand.one_liner,
            "value_props": brand.value_props,
            "tone": brand.tone,
            "website_url": brand.website_url,
        }

    prompt_template = (PROMPTS_DIR / "email_personalize.txt").read_text(encoding="utf-8")
    prompt = (
        prompt_template.replace("{first_name}", lead.first_name or "there")
        .replace("{company}", lead.company or "your company")
        .replace("{title}", lead.title or "Business Owner")
        .replace("{industry}", lead.industry or "your industry")
        .replace("{website}", lead.website or "")
        .replace("{country}", lead.country or "")
        .replace("{brand_profile}", json.dumps(brand_dict, indent=2))
        .replace("{subject_template}", step.subject_template or "")
        .replace("{body_template}", step.body_template or "")
        .replace("{website_snippet}", "")
    )


    try:
        result = await generate(
            prompt=prompt,
            response_model=EmailPersonalizeOutput,
            brand_context=brand_dict,
        )
        return PersonalizePreviewResponse(
            subject=result.subject,
            body=result.body,
            claims_safe=True,
            violations=[],
        )
    except Exception as exc:
        safe, violations = is_safe(str(exc))
        return PersonalizePreviewResponse(
            subject="",
            body=f"AI generation failed: {exc}",
            claims_safe=False,
            violations=violations or [str(exc)],
        )
