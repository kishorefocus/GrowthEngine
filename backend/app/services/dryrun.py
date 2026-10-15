"""
Dry-run service: wraps every outbound action.
When DRY_RUN=true, logs the action instead of executing it.
Every send/post must call this helper.
"""
import json
import logging
from typing import Any, Callable, Coroutine, TypeVar

from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def dry_run_guard(
    action_name: str,
    payload: dict,
    real_action: Callable[[], Coroutine[Any, Any, T]],
    dry_result: T | None = None,
) -> T:
    """
    Execute `real_action` unless DRY_RUN is True.

    Args:
        action_name: Human-readable label (e.g. "email.send", "post.publish").
        payload: Dict that describes what *would* be sent/posted.
        real_action: Async callable with the actual outbound call.
        dry_result: Value to return in dry-run mode (defaults to None).

    Returns:
        Result of real_action, or dry_result if DRY_RUN=True.
    """
    if settings.dry_run:
        logger.info(
            "[DRY_RUN] %s — would execute: %s",
            action_name,
            json.dumps(payload, default=str),
        )
        return dry_result  # type: ignore[return-value]

    return await real_action()


def is_dry_run() -> bool:
    return settings.dry_run
