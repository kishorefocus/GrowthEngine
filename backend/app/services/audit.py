"""
Audit log service: writes immutable audit trail entries.
Called on approvals, sends, deletions, and other sensitive operations.
"""
import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import AuditLog


async def write_audit_log(
    db: AsyncSession,
    action: str,
    user_id: Optional[uuid.UUID] = None,
    entity: Optional[str] = None,
    entity_id: Optional[str] = None,
    meta: Optional[dict] = None,
) -> AuditLog:
    """
    Write a single audit log entry.

    Args:
        db: Database session.
        action: Action string, e.g. "post.approved", "email.sent", "user.deleted".
        user_id: UUID of the acting user (None for system actions).
        entity: Table/entity name, e.g. "posts", "email_messages".
        entity_id: ID of the affected entity as string.
        meta: Arbitrary JSONB metadata.

    Returns:
        The created AuditLog instance.
    """
    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        meta=meta or {},
    )
    db.add(entry)
    await db.flush()  # Get ID without committing — caller commits
    return entry
