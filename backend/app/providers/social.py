"""
Social publisher interface + stub implementations.
Official APIs only: X, LinkedIn, Meta (Instagram/Facebook), YouTube.
All posts go through a human approval queue (status=pending_approval) before publishing.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import logging

from app.services.dryrun import dry_run_guard

logger = logging.getLogger(__name__)


@dataclass
class PostPayload:
    platform: str       # x|linkedin|instagram|facebook|youtube
    body: str
    media_urls: list[str] = None
    link_url: Optional[str] = None


@dataclass
class PublishResult:
    external_post_id: str
    success: bool
    error: Optional[str] = None


class SocialPublisher(ABC):
    """Abstract interface for social publishing."""

    @abstractmethod
    async def publish(self, post: PostPayload) -> PublishResult:
        """Publish a post. Returns external post ID on success."""
        ...


class StubSocialPublisher(SocialPublisher):
    """Stub — logs posts instead of publishing them."""

    async def publish(self, post: PostPayload) -> PublishResult:
        logger.info(
            "[SocialPublisher:STUB] Would publish to %s: %s...",
            post.platform, post.body[:80],
        )
        return PublishResult(external_post_id=f"stub-{post.platform}-000", success=True)


class XPublisher(SocialPublisher):
    """X (Twitter) API v2 publisher. Stub — Prompt 3 implements fully."""

    async def publish(self, post: PostPayload) -> PublishResult:
        async def _publish():
            # TODO: Prompt 3 — implement X API v2 create_tweet
            logger.warning("[XPublisher] Not yet implemented. Use stub.")
            return PublishResult(external_post_id="", success=False, error="Not implemented")

        return await dry_run_guard(
            "social.publish.x",
            {"body": post.body[:80]},
            _publish,
            dry_result=PublishResult(external_post_id="dry-run", success=True),
        )


class LinkedInPublisher(SocialPublisher):
    """LinkedIn Posts API publisher. Stub — Prompt 3 implements fully."""

    async def publish(self, post: PostPayload) -> PublishResult:
        async def _publish():
            logger.warning("[LinkedInPublisher] Not yet implemented. Use stub.")
            return PublishResult(external_post_id="", success=False, error="Not implemented")

        return await dry_run_guard(
            "social.publish.linkedin",
            {"body": post.body[:80]},
            _publish,
            dry_result=PublishResult(external_post_id="dry-run", success=True),
        )


def get_social_publisher(platform: str) -> SocialPublisher:
    """Factory: returns the publisher for the given platform."""
    from app.core.config import settings
    if settings.dry_run:
        return StubSocialPublisher()
    publishers = {
        "x": XPublisher(),
        "linkedin": LinkedInPublisher(),
    }
    return publishers.get(platform, StubSocialPublisher())
