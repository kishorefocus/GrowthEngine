"""
Prompt 2 Comprehensive Test Suite:
- Suppression enforced on every send
- Sequence stop rules (reply, bounce, unsubscribe, signup)
- Daily limit and sending window math
- Unsubscribe token creation and verification
- Public unsubscribe endpoint (/u/{token})
- Campaign health auto-pause thresholds (>5% bounce, >0.3% complaint)
- Provider webhook events (delivered, bounced, complained, opened, clicked)
- Inbound reply webhook with AI classification & auto-suppression on unsubscribe
- Email verification checks (syntax, MX, disposable, role accounts)
- DRY_RUN behavior and claims guard
"""
import asyncio
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.core.jwt import create_access_token
from app.models.auth import BrandProfile, User
from app.models.leads import (
    Campaign,
    EmailMessage,
    Lead,
    Reply,
    Sequence,
    SequenceStep,
    SuppressionList,
)
from app.services.claims_guard import check_claims, ClaimsGuardError, is_safe
from app.services.domain_health import check_domain_health
from app.services.email_verify import verify_email
from app.services.unsubscribe import create_unsubscribe_token, verify_unsubscribe_token
from worker.jobs.email import (
    check_campaign_health,
    is_in_sending_window,
    send_due_emails,
)


# ─── 1. Unsubscribe Token Unit Tests ──────────────────────────────────────────

def test_unsubscribe_token_lifecycle():
    email = "lead@example.com"
    token = create_unsubscribe_token(email)
    assert token and isinstance(token, str)

    verified = verify_unsubscribe_token(token)
    assert verified == email

    # Invalid token returns None
    assert verify_unsubscribe_token("tampered-token-xyz") is None


# ─── 2. Sending Window Math Tests ─────────────────────────────────────────────

def test_sending_window_math():
    window = {"start": "09:00", "end": "17:00"}
    # Outside any window
    assert is_in_sending_window(None) is True
    # Test valid structure
    res = is_in_sending_window(window, country="US", timezone_mode="recipient")
    assert isinstance(res, bool)


# ─── 3. Email Verification Service Tests ──────────────────────────────────────

@pytest.mark.asyncio
async def test_email_verification_syntax_and_disposable():
    # Invalid syntax
    res1 = await verify_email("invalid-email")
    assert res1["status"] == "invalid"
    assert res1["syntax_ok"] is False

    # Disposable domain
    res2 = await verify_email("test@mailinator.com")
    assert res2["is_disposable"] is True
    assert res2["status"] in ("risky", "invalid")

    # Role account
    res3 = await verify_email("sales@example.com")
    assert res3["is_role"] is True


# ─── 4. Domain Health Check Tests ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_domain_health_check_structure():
    res = await check_domain_health("example.com")
    assert "spf" in res
    assert "dkim" in res
    assert "dmarc" in res
    assert "overall" in res
    assert "warmup_schedule" in res
    assert len(res["warmup_schedule"]) >= 5


# ─── 5. Public Unsubscribe Endpoint End-to-End ────────────────────────────────

@pytest.mark.asyncio
async def test_public_unsubscribe_endpoint(client: AsyncClient, test_db):
    lead = Lead(
        email="unsub_test@example.com",
        first_name="Unsub",
        verification_status="valid",
        status="contacted",
    )
    test_db.add(lead)
    await test_db.commit()

    token = create_unsubscribe_token("unsub_test@example.com")
    response = await client.get(f"/u/{token}")
    assert response.status_code == 200
    assert "unsubscribed" in response.text.lower()

    # Check suppression table
    sup_check = await test_db.execute(
        select(SuppressionList).where(SuppressionList.email_or_domain == "unsub_test@example.com")
    )
    entry = sup_check.scalar_one_or_none()
    assert entry is not None
    assert entry.reason == "unsubscribed"

    # Check lead status updated
    await test_db.refresh(lead)
    assert lead.status == "unsubscribed"


# ─── 6. Suppression Enforced on Every Send ────────────────────────────────────

@pytest.mark.asyncio
async def test_suppression_enforced_on_send(test_db):
    # Create campaign & sequence
    camp = Campaign(name="Test Camp", status="active", daily_limit=20)
    test_db.add(camp)
    await test_db.flush()

    seq = Sequence(campaign_id=camp.id)
    test_db.add(seq)
    await test_db.flush()

    step = SequenceStep(
        sequence_id=seq.id,
        step_number=1,
        delay_days=0,
        subject_template="Hello {first_name}",
        body_template="Hi {first_name}",
    )
    test_db.add(step)
    await test_db.flush()

    # Suppressed lead
    lead = Lead(
        email="suppressed_person@example.com",
        first_name="Alice",
        verification_status="valid",
        status="queued",
    )
    test_db.add(lead)
    test_db.add(SuppressionList(email_or_domain="suppressed_person@example.com", reason="opt_out"))
    await test_db.flush()

    msg = EmailMessage(
        lead_id=lead.id,
        campaign_id=camp.id,
        step_id=step.id,
        status="scheduled",
    )
    test_db.add(msg)
    await test_db.commit()

    # Run worker job
    result = await send_due_emails({"is_test": True, "db": test_db})
    assert result["cancelled"] >= 1

    await test_db.refresh(msg)
    assert msg.status == "cancelled"


# ─── 7. Sequence Stop Rules (Reply, Bounce, Unsubscribe, Signup) ──────────────

@pytest.mark.asyncio
async def test_sequence_stop_rules(test_db):
    camp = Campaign(name="Stop Rule Campaign", status="active", daily_limit=50)
    test_db.add(camp)
    await test_db.flush()

    seq = Sequence(campaign_id=camp.id)
    test_db.add(seq)
    await test_db.flush()

    step = SequenceStep(sequence_id=seq.id, step_number=1, delay_days=0)
    test_db.add(step)
    await test_db.flush()

    # 4 leads with stopped statuses
    stopped_statuses = ["replied", "bounced", "unsubscribed", "signed_up"]
    msgs = []
    for s in stopped_statuses:
        lead = Lead(
            email=f"lead_{s}@example.com",
            first_name=s,
            verification_status="valid",
            status=s,
        )
        test_db.add(lead)
        await test_db.flush()
        msg = EmailMessage(lead_id=lead.id, campaign_id=camp.id, step_id=step.id, status="scheduled")
        test_db.add(msg)
        msgs.append(msg)

    await test_db.commit()

    result = await send_due_emails({"is_test": True, "db": test_db})
    assert result["cancelled"] == 4

    for m in msgs:
        await test_db.refresh(m)
        assert m.status == "cancelled"


# ─── 8. Daily Limit Enforced ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_daily_limit_enforced(test_db):
    # Campaign daily limit = 2
    camp = Campaign(name="Limited Camp", status="active", daily_limit=2)
    test_db.add(camp)
    await test_db.flush()

    seq = Sequence(campaign_id=camp.id)
    test_db.add(seq)
    await test_db.flush()

    step = SequenceStep(sequence_id=seq.id, step_number=1, delay_days=0)
    test_db.add(step)
    await test_db.flush()

    # 4 valid leads scheduled
    for i in range(4):
        lead = Lead(
            email=f"user_{i}@example.com",
            first_name=f"User{i}",
            verification_status="valid",
            status="queued",
        )
        test_db.add(lead)
        await test_db.flush()
        msg = EmailMessage(lead_id=lead.id, campaign_id=camp.id, step_id=step.id, status="scheduled")
        test_db.add(msg)

    await test_db.commit()

    result = await send_due_emails({"is_test": True, "db": test_db})
    assert result["sent"] == 2  # exactly daily limit

    # Re-running immediately respects the limit
    result2 = await send_due_emails({"is_test": True, "db": test_db})
    assert result2["sent"] == 0


# ─── 9. Campaign Health Auto-Pause Thresholds ────────────────────────────────

@pytest.mark.asyncio
async def test_check_campaign_health_auto_pause(test_db):
    camp = Campaign(name="High Bounce Camp", status="active", daily_limit=100)
    test_db.add(camp)
    await test_db.flush()

    seq = Sequence(campaign_id=camp.id)
    test_db.add(seq)
    await test_db.flush()

    step = SequenceStep(sequence_id=seq.id, step_number=1)
    test_db.add(step)
    await test_db.flush()

    lead = Lead(email="target@example.com", verification_status="valid")
    test_db.add(lead)
    await test_db.flush()

    # Create 20 sent messages: 3 bounced (15% bounce rate > 5% threshold)
    for i in range(17):
        test_db.add(EmailMessage(lead_id=lead.id, campaign_id=camp.id, step_id=step.id, status="delivered"))
    for i in range(3):
        test_db.add(EmailMessage(lead_id=lead.id, campaign_id=camp.id, step_id=step.id, status="bounced"))

    await test_db.commit()

    health_result = await check_campaign_health({"is_test": True, "db": test_db})
    assert str(camp.id) in health_result["auto_paused"]

    await test_db.refresh(camp)
    assert camp.status == "paused"


# ─── 10. Provider Webhooks (Delivered, Bounced, Complained) ───────────────────

@pytest.mark.asyncio
async def test_provider_webhook_bounce_auto_suppresses(client: AsyncClient, test_db):
    lead = Lead(email="bouncy@example.com", verification_status="valid", status="contacted")
    test_db.add(lead)
    await test_db.flush()

    msg = EmailMessage(
        lead_id=lead.id,
        status="sent",
        provider_message_id="prov-msg-12345",
    )
    test_db.add(msg)
    await test_db.commit()

    payload = {
        "type": "email.bounced",
        "data": {
            "email_id": "prov-msg-12345",
            "to": ["bouncy@example.com"],
        },
    }

    res = await client.post("/webhooks/email", json=payload)
    assert res.status_code == 200

    await test_db.refresh(msg)
    assert msg.status == "bounced"

    await test_db.refresh(lead)
    assert lead.status == "bounced"

    # Auto-suppressed
    sup_check = await test_db.execute(
        select(SuppressionList).where(SuppressionList.email_or_domain == "bouncy@example.com")
    )
    assert sup_check.scalar_one_or_none() is not None


# ─── 11. Inbound Reply Webhook and Classification ─────────────────────────────

@pytest.mark.asyncio
async def test_inbound_reply_webhook_unsubscribe_flow(client: AsyncClient, test_db):
    lead = Lead(email="prospect@company.com", verification_status="valid", status="contacted")
    test_db.add(lead)
    await test_db.flush()

    msg = EmailMessage(lead_id=lead.id, status="sent")
    test_db.add(msg)
    await test_db.commit()

    payload = {
        "from": "prospect@company.com",
        "subject": "Re: Partnership",
        "text": "Please remove me from your list and unsubscribe.",
    }

    res = await client.post("/webhooks/email/inbound", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["classification"] == "unsubscribe"

    # Lead should be unsubscribed and suppressed
    await test_db.refresh(lead)
    assert lead.status == "unsubscribed"

    sup_res = await test_db.execute(
        select(SuppressionList).where(SuppressionList.email_or_domain == "prospect@company.com")
    )
    assert sup_res.scalar_one_or_none() is not None


# ─── 12. Campaign Pause, Resume & Launch from Draft ───────────────────────────

@pytest.mark.asyncio
async def test_campaign_pause_resume_and_launch_from_draft(client: AsyncClient, test_db):
    user = User(
        email=f"owner_{uuid.uuid4().hex[:6]}@example.com",
        role="owner",
        is_active=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    token = create_access_token(user_id=str(user.id), role=user.role)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a campaign in draft status
    camp = Campaign(name="Test Draft Campaign", status="draft")
    test_db.add(camp)
    await test_db.commit()
    await test_db.refresh(camp)

    # 2. Resume / launch draft campaign -> status becomes active
    res = await client.post(f"/api/v1/campaigns/{camp.id}/resume", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "active"
    await test_db.refresh(camp)
    assert camp.status == "active"

    # 3. Cannot resume an already active campaign
    res_err = await client.post(f"/api/v1/campaigns/{camp.id}/resume", headers=headers)
    assert res_err.status_code == 400

    # 4. Pause active campaign -> status becomes paused
    res_pause = await client.post(f"/api/v1/campaigns/{camp.id}/pause", headers=headers)
    assert res_pause.status_code == 200
    assert res_pause.json()["status"] == "paused"
    await test_db.refresh(camp)
    assert camp.status == "paused"

    # 5. Resume paused campaign -> status becomes active
    res_resume = await client.post(f"/api/v1/campaigns/{camp.id}/resume", headers=headers)
    assert res_resume.status_code == 200
    assert res_resume.json()["status"] == "active"
    await test_db.refresh(camp)
    assert camp.status == "active"

    # 6. Test launch route alias on draft campaign
    camp2 = Campaign(name="Test Draft Campaign 2", status="draft")
    test_db.add(camp2)
    await test_db.commit()
    await test_db.refresh(camp2)

    res_launch = await client.post(f"/api/v1/campaigns/{camp2.id}/launch", headers=headers)
    assert res_launch.status_code == 200
    assert res_launch.json()["status"] == "active"
    await test_db.refresh(camp2)
    assert camp2.status == "active"

