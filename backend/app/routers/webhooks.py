"""
Webhooks router:
- POST /webhooks/signup  (public, HMAC-signed with SIGNUP_WEBHOOK_SECRET)
  Receives signup events from the main GlobalReach product.
  Writes signup_attributions table.
"""
import hashlib
import hmac
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.analytics import SignupAttribution

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class SignupPayload(BaseModel):
    user_email: str
    signed_up_at: str           # ISO 8601
    first_touch: dict | None = None
    last_touch: dict | None = None


def _verify_signature(body: bytes, signature: str) -> bool:
    """Verify HMAC-SHA256 signature from the main product webhook."""
    expected = hmac.new(
        settings.signup_webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature.removeprefix("sha256="))


@router.post("/signup", status_code=status.HTTP_204_NO_CONTENT)
async def signup_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_signature: str = Header(alias="X-Signature", default=""),
):
    """
    Receive signup events from the GlobalReach main product.
    HMAC-signed with SIGNUP_WEBHOOK_SECRET.
    Writes signup_attributions for dashboard attribution.
    """
    body = await request.body()

    if not _verify_signature(body, x_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature.",
        )

    try:
        data = json.loads(body)
        payload = SignupPayload(**data)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid payload: {exc}")

    try:
        signed_up_at = datetime.fromisoformat(payload.signed_up_at.replace("Z", "+00:00"))
    except ValueError:
        signed_up_at = datetime.now(timezone.utc)

    attribution = SignupAttribution(
        user_email=payload.user_email,
        first_touch=payload.first_touch,
        last_touch=payload.last_touch,
        signed_up_at=signed_up_at,
    )
    db.add(attribution)
    await db.commit()
