"""
Email events and inbox router:
- POST /webhooks/email (public) — provider event webhook (delivered, bounced, opened, clicked, complained)
- POST /webhooks/email/inbound (public) — inbound reply webhook with AI classification
- GET /inbox/replies — list inbound replies for human review
- POST /inbox/replies/{id}/handle — mark reply as handled
- POST /inbox/replies/{id}/suppress — one-click suppress lead from reply
"""
import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import BrandProfile, User
from app.models.leads import Campaign, EmailMessage, Lead, Reply, SuppressionList
from app.schemas.leads import (
    ReplyClassifyOutput,
    ReplyHandleRequest,
    ReplyResponse,
)
from app.services.ai import generate
from app.services.audit import write_audit_log

logger = logging.getLogger(__name__)

router = APIRouter(tags=["email_events"])
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


# ─── Provider Event Webhook (Delivery / Bounce / Open / Click) ────────────────

@router.post("/webhooks/email", status_code=status.HTTP_200_OK)
async def provider_email_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_webhook_signature: Optional[str] = Header(None, alias="X-Webhook-Signature"),
    svix_signature: Optional[str] = Header(None, alias="svix-signature"),
):
    """
    Public webhook endpoint receiving email provider events:
    delivered, bounced, complained, opened, clicked.
    Verifies signature if secret is configured.
    Updates email_messages.status and auto-suppresses bounces and complaints.
    """
    body_bytes = await request.body()

    # Verify signature if SIGNUP_WEBHOOK_SECRET / EMAIL_WEBHOOK_SECRET configured
    expected_secret = getattr(settings, "email_webhook_secret", settings.signup_webhook_secret)
    sig_to_check = x_webhook_signature or svix_signature
    if sig_to_check and expected_secret:
        expected = hmac.new(expected_secret.encode(), body_bytes, hashlib.sha256).hexdigest()
        provided = sig_to_check.replace("sha256=", "").strip()
        if not hmac.compare_digest(provided, expected):
            logger.warning("Invalid email webhook signature: provided=%s", provided[:10])
            raise HTTPException(status_code=401, detail="Invalid webhook signature.")

    try:
        data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {exc}")

    event_type = data.get("type") or data.get("event") or ""
    provider_id = (
        data.get("data", {}).get("email_id")
        or data.get("id")
        or data.get("message_id")
        or data.get("email_id")
    )
    recipient = (
        data.get("data", {}).get("to", [None])[0]
        if isinstance(data.get("data", {}).get("to"), list)
        else data.get("data", {}).get("to") or data.get("recipient") or data.get("email")
    )

    normalized_status = None
    if "delivered" in event_type.lower():
        normalized_status = "delivered"
    elif "bounce" in event_type.lower():
        normalized_status = "bounced"
    elif "complain" in event_type.lower() or "spam" in event_type.lower():
        normalized_status = "complained"
    elif "open" in event_type.lower():
        normalized_status = "opened"
    elif "click" in event_type.lower():
        normalized_status = "clicked"

    if not normalized_status:
        return {"status": "ignored", "event": event_type}

    message = None
    if provider_id:
        result = await db.execute(
            select(EmailMessage).where(EmailMessage.provider_message_id == str(provider_id))
        )
        message = result.scalar_one_or_none()

    if not message and recipient:
        lead_res = await db.execute(select(Lead).where(Lead.email == recipient.lower().strip()))
        lead = lead_res.scalar_one_or_none()
        if lead:
            msg_res = await db.execute(
                select(EmailMessage)
                .where(EmailMessage.lead_id == lead.id)
                .order_by(EmailMessage.created_at.desc())
                .limit(1)
            )
            message = msg_res.scalar_one_or_none()

    if message:
        message.status = normalized_status
        logger.info("Updated email message %s status to %s", message.id, normalized_status)

        if normalized_status in ("bounced", "complained"):
            lead_res = await db.execute(select(Lead).where(Lead.id == message.lead_id))
            lead = lead_res.scalar_one_or_none()
            if lead:
                lead.status = normalized_status
                sup_check = await db.execute(
                    select(SuppressionList).where(SuppressionList.email_or_domain == lead.email.lower())
                )
                if not sup_check.scalar_one_or_none():
                    db.add(
                        SuppressionList(
                            email_or_domain=lead.email.lower(),
                            reason=f"provider_event_{normalized_status}",
                            added_at=datetime.now(timezone.utc),
                        )
                    )
            await write_audit_log(
                db,
                f"email.{normalized_status}",
                entity="email_messages",
                entity_id=str(message.id),
                meta={"recipient": recipient, "provider_id": provider_id},
            )

    await db.commit()
    return {"status": "processed", "event": normalized_status}


# ─── Inbound Reply Parse Webhook (Inbound Email + AI Classification) ─────────

@router.post("/webhooks/email/inbound", status_code=status.HTTP_200_OK)
async def inbound_reply_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Inbound parse webhook for email replies.
    Stores reply in `replies`, classifies intent with Claude (interested, not_now, etc.),
    adds to suppression if classification is 'unsubscribe', and generates suggested response.
    """
    try:
        body_bytes = await request.body()
        data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
    except Exception:
        form_data = await request.form()
        data = dict(form_data)

    from_email = (data.get("from") or data.get("sender") or "").strip().lower()
    if "<" in from_email and ">" in from_email:
        from_email = from_email.split("<")[1].split(">")[0].strip().lower()

    subject = data.get("subject", "")
    reply_body = (data.get("text") or data.get("body") or data.get("html") or "").strip()

    if not from_email or not reply_body:
        return {"status": "skipped", "reason": "missing from_email or reply_body"}

    lead_res = await db.execute(select(Lead).where(Lead.email == from_email))
    lead = lead_res.scalar_one_or_none()

    message = None
    if lead:
        msg_res = await db.execute(
            select(EmailMessage)
            .where(EmailMessage.lead_id == lead.id)
            .order_by(EmailMessage.created_at.desc())
            .limit(1)
        )
        message = msg_res.scalar_one_or_none()
        lead.status = "replied"

    if message:
        message.status = "replied"

    classification, confidence, suggested_response = await classify_reply_text(
        reply_text=reply_body,
        original_subject=subject,
        lead_first_name=lead.first_name if lead else None,
        db=db,
    )

    if classification == "unsubscribe":
        sup_check = await db.execute(
            select(SuppressionList).where(SuppressionList.email_or_domain == from_email)
        )
        if not sup_check.scalar_one_or_none():
            db.add(
                SuppressionList(
                    email_or_domain=from_email,
                    reason="inbound_unsubscribe_request",
                    added_at=datetime.now(timezone.utc),
                )
            )
        if lead:
            lead.status = "unsubscribed"

    reply_record = Reply(
        message_id=message.id if message else uuid.uuid4(),
        body=reply_body[:10000],
        classification=classification,
        confidence=confidence,
        suggested_response=suggested_response,
        handled=False,
    )
    db.add(reply_record)
    await db.commit()
    await db.refresh(reply_record)

    logger.info(
        "Stored reply for %s: classification=%s confidence=%.2f",
        from_email, classification, confidence
    )

    return {
        "status": "processed",
        "reply_id": str(reply_record.id),
        "classification": classification,
        "confidence": confidence,
    }


async def classify_reply_text(
    reply_text: str,
    original_subject: str,
    lead_first_name: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> tuple[str, float, Optional[str]]:
    """Helper to classify reply text using Claude."""
    template_path = PROMPTS_DIR / "reply_classify.txt"
    if not template_path.exists():
        return "other", 0.5, None

    prompt_template = template_path.read_text(encoding="utf-8")
    first_name = lead_first_name or "there"
    prompt = (
        prompt_template.replace("{reply_text}", reply_text)
        .replace("{original_subject}", original_subject or "Outreach")
        .replace("{first_name}", first_name)
    )



    try:
        brand_dict = {}
        if db:
            brand_res = await db.execute(select(BrandProfile))
            brand = brand_res.scalar_one_or_none()
            if brand:
                brand_dict = {
                    "product_name": brand.product_name,
                    "one_liner": brand.one_liner,
                    "tone": brand.tone,
                }

        result = await generate(
            prompt=prompt,
            response_model=ReplyClassifyOutput,
            brand_context=brand_dict,
        )
        classification = result.classification.lower().strip()
        valid_classes = {"interested", "not_now", "not_interested", "unsubscribe", "out_of_office", "other"}
        if classification not in valid_classes:
            classification = "other"
        return classification, float(result.confidence or 0.8), result.suggested_response
    except Exception as exc:
        logger.warning("AI reply classification fallback: %s", exc)
        lower_body = reply_text.lower()
        if any(w in lower_body for w in ["unsubscribe", "remove me", "stop emailing", "take me off"]):
            return "unsubscribe", 0.95, None
        elif any(w in lower_body for w in ["interested", "call", "schedule", "demo", "send more info", "pricing"]):
            suggested = f"Hi {first_name}, thanks for getting back to me! I'd love to share more details. Would you be open to a quick 10-minute demo this week?"
            return "interested", 0.85, suggested
        elif any(w in lower_body for w in ["not now", "later", "next quarter", "busy right now"]):
            return "not_now", 0.80, None
        elif any(w in lower_body for w in ["not interested", "no thanks", "pass"]):
            return "not_interested", 0.90, None
        elif any(w in lower_body for w in ["out of the office", "on leave", "away from my desk", "auto-reply"]):
            return "out_of_office", 0.95, None
        return "other", 0.60, None


# ─── Inbox Endpoints (Authenticated) ──────────────────────────────────────────

@router.get("/inbox/replies", response_model=list[ReplyResponse])
async def list_replies(
    classification: Optional[str] = Query(None),
    handled: Optional[bool] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List replies with lead context and AI classification."""
    q = select(Reply).order_by(Reply.created_at.desc())
    if classification:
        q = q.where(Reply.classification == classification)
    if handled is not None:
        q = q.where(Reply.handled == handled)
    q = q.limit(limit).offset(offset)
    results = (await db.execute(q)).scalars().all()

    replies_response = []
    for r in results:
        lead_dict = None
        msg_res = await db.execute(select(EmailMessage).where(EmailMessage.id == r.message_id))
        msg = msg_res.scalar_one_or_none()
        if msg:
            lead_res = await db.execute(select(Lead).where(Lead.id == msg.lead_id))
            lead = lead_res.scalar_one_or_none()
            if lead:
                lead_dict = {
                    "id": str(lead.id),
                    "email": lead.email,
                    "first_name": lead.first_name,
                    "last_name": lead.last_name,
                    "company": lead.company,
                    "title": lead.title,
                }

        replies_response.append(
            ReplyResponse(
                id=str(r.id),
                message_id=str(r.message_id),
                body=r.body,
                classification=r.classification,
                confidence=r.confidence,
                handled=r.handled,
                suggested_response=r.suggested_response,
                lead=lead_dict,
                created_at=r.created_at,
            )
        )
    return replies_response


@router.post("/inbox/replies/{reply_id}/handle", response_model=ReplyResponse)
async def handle_reply(
    reply_id: str,
    body: ReplyHandleRequest = ReplyHandleRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a reply as handled or unhandled."""
    result = await db.execute(select(Reply).where(Reply.id == reply_id))
    reply = result.scalar_one_or_none()
    if not reply:
        raise HTTPException(status_code=404, detail="Reply not found.")
    reply.handled = body.handled
    await write_audit_log(
        db,
        "reply.handled" if body.handled else "reply.unhandled",
        user_id=current_user.id,
        entity="replies",
        entity_id=reply_id,
    )
    await db.commit()
    await db.refresh(reply)
    return ReplyResponse(
        id=str(reply.id),
        message_id=str(reply.message_id),
        body=reply.body,
        classification=reply.classification,
        confidence=reply.confidence,
        handled=reply.handled,
        suggested_response=reply.suggested_response,
        created_at=reply.created_at,
    )


@router.post("/inbox/replies/{reply_id}/suppress")
async def suppress_from_reply(
    reply_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """One-click add the lead associated with this reply to the suppression list."""
    result = await db.execute(select(Reply).where(Reply.id == reply_id))
    reply = result.scalar_one_or_none()
    if not reply:
        raise HTTPException(status_code=404, detail="Reply not found.")

    msg_res = await db.execute(select(EmailMessage).where(EmailMessage.id == reply.message_id))
    msg = msg_res.scalar_one_or_none()
    email_to_suppress = None
    if msg:
        lead_res = await db.execute(select(Lead).where(Lead.id == msg.lead_id))
        lead = lead_res.scalar_one_or_none()
        if lead:
            email_to_suppress = lead.email
            lead.status = "unsubscribed"

    if email_to_suppress:
        sup_check = await db.execute(
            select(SuppressionList).where(SuppressionList.email_or_domain == email_to_suppress.lower())
        )
        if not sup_check.scalar_one_or_none():
            db.add(
                SuppressionList(
                    email_or_domain=email_to_suppress.lower(),
                    reason="suppressed_from_inbox",
                    added_at=datetime.now(timezone.utc),
                )
            )
        reply.handled = True
        await write_audit_log(
            db, "suppression.added_from_inbox", user_id=current_user.id,
            entity="suppression_list", entity_id=str(reply.id),
            meta={"email": email_to_suppress}
        )
        await db.commit()
        return {"suppressed": email_to_suppress, "status": "ok"}

    reply.handled = True
    await db.commit()
    return {"status": "marked_handled_no_lead_found"}
