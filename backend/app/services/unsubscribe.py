"""
Unsubscribe token service.
Creates and verifies signed tokens using itsdangerous (HMAC-SHA1).
The token encodes the lead's email. GET /u/{token} verifies and suppresses.
"""
import logging
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from app.core.config import settings

logger = logging.getLogger(__name__)

_MAX_AGE_SECONDS = 60 * 60 * 24 * 365  # 1 year


def _get_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.unsubscribe_secret, salt="unsub")


def create_unsubscribe_token(email: str) -> str:
    """Create a signed, URL-safe token encoding the lead's email."""
    s = _get_serializer()
    return s.dumps({"email": email})


def verify_unsubscribe_token(token: str) -> str | None:
    """
    Verify the token and return the email if valid, else None.
    Tokens are valid for up to 1 year.
    """
    s = _get_serializer()
    try:
        data = s.loads(token, max_age=_MAX_AGE_SECONDS)
        return data.get("email")
    except SignatureExpired:
        logger.warning("Unsubscribe token expired: %s", token[:20])
        return None
    except BadSignature:
        logger.warning("Unsubscribe token bad signature: %s", token[:20])
        return None
    except Exception as exc:
        logger.error("Unsubscribe token error: %s", exc)
        return None
