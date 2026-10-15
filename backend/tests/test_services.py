"""Tests for UTM builder, claims guard, and HMAC webhook."""
import hashlib
import hmac
import json

import pytest

from app.services.utm import build_utm_url, utm_dict
from app.services.claims_guard import check_claims, ClaimsGuardError, is_safe


# ─── UTM builder tests ────────────────────────────────────────────────────────

def test_utm_url_appends_params():
    url = build_utm_url("https://getyourclientsb2b.com", "email", "cold_outreach", "q4_campaign")
    assert "utm_source=email" in url
    assert "utm_medium=cold_outreach" in url
    assert "utm_campaign=q4_campaign" in url


def test_utm_url_preserves_existing_params():
    url = build_utm_url("https://example.com?ref=partner", "x", "social", "test")
    assert "ref=partner" in url
    assert "utm_source=x" in url


def test_utm_url_with_content():
    url = build_utm_url("https://example.com", "linkedin", "social", "campaign", content="post_abc")
    assert "utm_content=post_abc" in url


def test_utm_dict():
    d = utm_dict("email", "cold_outreach", "campaign_1", content="step_2")
    assert d["utm_source"] == "email"
    assert d["utm_medium"] == "cold_outreach"
    assert d["utm_content"] == "step_2"


# ─── Claims guard tests ───────────────────────────────────────────────────────

def test_claims_guard_passes_clean_text():
    """Clean, honest marketing copy should pass."""
    check_claims("GlobalReach helps B2B founders find international clients through cold email and content.")


def test_claims_guard_rejects_guarantee():
    """'guaranteed' must be rejected."""
    with pytest.raises(ClaimsGuardError):
        check_claims("Get guaranteed results with our system.")


def test_claims_guard_rejects_10x():
    """'10x leads' must be rejected."""
    with pytest.raises(ClaimsGuardError):
        check_claims("We help you get 10x leads in 30 days.")


def test_claims_guard_is_safe_returns_tuple():
    safe, violations = is_safe("Honest copy about our product.")
    assert safe is True
    assert violations == []

    safe2, violations2 = is_safe("Guaranteed 100% success with our platform.")
    assert safe2 is False
    assert len(violations2) > 0


# ─── HMAC webhook tests ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_webhook_valid_signature(client):
    """Valid HMAC signature must be accepted."""
    from app.core.config import settings

    payload = json.dumps({
        "user_email": "user@example.com",
        "signed_up_at": "2026-10-15T12:00:00Z",
        "first_touch": {"utm_source": "email"},
        "last_touch": {"utm_source": "google"},
    }).encode()

    sig = "sha256=" + hmac.new(
        settings.signup_webhook_secret.encode(), payload, hashlib.sha256
    ).hexdigest()

    response = await client.post(
        "/api/v1/webhooks/signup",
        content=payload,
        headers={"X-Signature": sig, "Content-Type": "application/json"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_webhook_invalid_signature(client):
    """Invalid HMAC signature must be rejected with 401."""
    payload = json.dumps({"user_email": "user@example.com", "signed_up_at": "2026-10-15T12:00:00Z"}).encode()
    response = await client.post(
        "/api/v1/webhooks/signup",
        content=payload,
        headers={"X-Signature": "sha256=bad_signature", "Content-Type": "application/json"},
    )
    assert response.status_code == 401
