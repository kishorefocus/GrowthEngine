"""
Email provider interface + stub implementations.
Later prompts fill in Resend, Postmark, SES implementations.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import logging

from app.core.config import settings
from app.services.dryrun import dry_run_guard

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    to: str
    subject: str
    html_body: str
    from_name: str = "GlobalReach"
    reply_to: Optional[str] = None
    tracking_token: Optional[str] = None
    headers: Optional[dict[str, str]] = None


@dataclass
class SendResult:
    provider_message_id: str
    success: bool
    error: Optional[str] = None


class EmailProvider(ABC):
    """Abstract interface for all email sending providers."""

    @abstractmethod
    async def send(self, message: EmailMessage) -> SendResult:
        """Send an email. Raises on hard failure."""
        ...

    @abstractmethod
    async def check_bounces(self) -> list[str]:
        """Return list of email addresses that bounced recently."""
        ...


class StubEmailProvider(EmailProvider):
    """Stub — logs emails instead of sending them. Used in DRY_RUN and testing."""

    async def send(self, message: EmailMessage) -> SendResult:
        logger.info(
            "[EmailProvider:STUB] Would send email to=%s subject=%s token=%s",
            message.to, message.subject, message.tracking_token,
        )
        return SendResult(provider_message_id="stub-" + (message.tracking_token or "no-token"), success=True)

    async def check_bounces(self) -> list[str]:
        return []


class ResendEmailProvider(EmailProvider):
    """Resend.com email provider. Requires RESEND_API_KEY."""

    async def send(self, message: EmailMessage) -> SendResult:
        import resend
        resend.api_key = settings.resend_api_key

        async def _send():
            try:
                params: resend.Emails.SendParams = {
                    "from": f"{message.from_name} <noreply@{settings.sending_domain}>",
                    "to": [message.to],
                    "subject": message.subject,
                    "html": message.html_body,
                }
                if message.reply_to:
                    params["reply_to"] = message.reply_to
                result = resend.Emails.send(params)
                return SendResult(provider_message_id=result["id"], success=True)
            except Exception as exc:
                return SendResult(provider_message_id="", success=False, error=str(exc))

        return await dry_run_guard(
            "email.send",
            {"to": message.to, "subject": message.subject},
            _send,
            dry_result=SendResult(provider_message_id="dry-run", success=True),
        )

    async def check_bounces(self) -> list[str]:
        # Resend bounce webhook handling — stub for now
        return []


def get_email_provider() -> EmailProvider:
    """Factory: returns the configured email provider."""
    if settings.dry_run or not settings.resend_api_key:
        return StubEmailProvider()
    if settings.email_provider == "resend":
        return ResendEmailProvider()
    return StubEmailProvider()
