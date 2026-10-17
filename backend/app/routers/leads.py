"""
Leads router:
- GET/POST /leads — list and create leads
- POST /leads/import/globalreach — dogfooding import
- POST /leads/import/csv — manual CSV import
- POST /leads/{id}/verify — email verification
- DELETE /leads/{id} — erasure request (keeps email in suppression)
- GET/POST /suppression — suppression list management
- GET /u/{token} — (public) unsubscribe handler
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import User
from app.models.leads import ICP, Lead, SuppressionList
from app.schemas.leads import (
    CSVImportRequest,
    ErasureRequest,
    GlobalReachImportRequest,
    LeadCreate,
    LeadResponse,
    LeadVerificationResult,
    SuppressionCreate,
    SuppressionResponse,
)
from app.services.audit import write_audit_log
from app.services.email_verify import verify_email
from app.services.unsubscribe import verify_unsubscribe_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["leads"])


# ─── Suppression helpers ──────────────────────────────────────────────────────

async def is_suppressed(db: AsyncSession, email: str) -> bool:
    """Check if the email or its domain is in the suppression list."""
    domain = email.split("@")[-1].lower() if "@" in email else ""
    result = await db.execute(
        select(SuppressionList).where(
            or_(
                SuppressionList.email_or_domain == email.lower(),
                SuppressionList.email_or_domain == domain,
            )
        )
    )
    return result.scalar_one_or_none() is not None


async def add_to_suppression(db: AsyncSession, email: str, reason: str) -> None:
    """Add an email to the suppression list (idempotent)."""
    existing = await db.execute(
        select(SuppressionList).where(SuppressionList.email_or_domain == email.lower())
    )
    if existing.scalar_one_or_none():
        return
    entry = SuppressionList(
        email_or_domain=email.lower(),
        reason=reason,
        added_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    await db.flush()


# ─── Lead helpers ─────────────────────────────────────────────────────────────

def _lead_to_response(lead: Lead) -> LeadResponse:
    return LeadResponse(
        id=str(lead.id),
        email=lead.email,
        first_name=lead.first_name,
        last_name=lead.last_name,
        company=lead.company,
        title=lead.title,
        website=lead.website,
        country=lead.country,
        industry=lead.industry,
        source=lead.source,
        verification_status=lead.verification_status,
        icp_id=str(lead.icp_id) if lead.icp_id else None,
        status=lead.status,
        lawful_basis=lead.lawful_basis,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
    )


# ─── CRUD ─────────────────────────────────────────────────────────────────────

@router.get("/leads", response_model=list[LeadResponse])
async def list_leads(
    icp_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    country: Optional[str] = Query(None),
    verification_status: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List leads with optional filters."""
    q = select(Lead)
    if icp_id:
        q = q.where(Lead.icp_id == icp_id)
    if status_filter:
        q = q.where(Lead.status == status_filter)
    if country:
        q = q.where(Lead.country == country)
    if verification_status:
        q = q.where(Lead.verification_status == verification_status)
    q = q.order_by(Lead.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    return [_lead_to_response(lead) for lead in result.scalars()]


@router.post("/leads", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    body: LeadCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a single lead. Deduplicates by email."""
    email = str(body.email).lower()
    existing = await db.execute(select(Lead).where(Lead.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Lead with email {email} already exists.")
    lead = Lead(
        email=email,
        first_name=body.first_name,
        last_name=body.last_name,
        company=body.company,
        title=body.title,
        website=body.website,
        country=body.country,
        industry=body.industry,
        source=body.source,
        icp_id=uuid.UUID(body.icp_id) if body.icp_id else None,
        lawful_basis=body.lawful_basis,
    )
    db.add(lead)
    await db.flush()
    await write_audit_log(db, "lead.created", user_id=current_user.id, entity="leads", entity_id=str(lead.id))
    await db.commit()
    await db.refresh(lead)
    return _lead_to_response(lead)


@router.get("/leads/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return _lead_to_response(lead)


@router.delete("/leads/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def erase_lead(
    lead_id: str,
    body: ErasureRequest = ErasureRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    GDPR/CASL erasure: deletes the lead record but keeps email in suppression list
    so they are never contacted again.
    """
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")
    email = lead.email
    await add_to_suppression(db, email, reason=body.reason or "erasure_request")
    await write_audit_log(
        db, "lead.erased", user_id=current_user.id, entity="leads", entity_id=lead_id,
        meta={"email_suppressed": email, "reason": body.reason}
    )
    await db.delete(lead)
    await db.commit()


# ─── Email Verification ───────────────────────────────────────────────────────

@router.post("/leads/{lead_id}/verify", response_model=LeadVerificationResult)
async def verify_lead(
    lead_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Run syntax, MX, disposable domain, and role-account checks.
    Updates verification_status on the lead.
    Auto-adds known bounces/complaints (risky/invalid) to suppression.
    """
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    checks = await verify_email(lead.email)
    lead.verification_status = checks["status"]  # valid | invalid | risky

    # Auto-suppress invalid emails
    if checks["status"] == "invalid":
        await add_to_suppression(db, lead.email, reason="verification_invalid")

    await write_audit_log(
        db, "lead.verified", user_id=current_user.id, entity="leads", entity_id=lead_id,
        meta={"verification_status": checks["status"], "checks": checks}
    )
    await db.commit()

    return LeadVerificationResult(
        id=lead_id,
        email=lead.email,
        verification_status=checks["status"],
        checks=checks,
    )


# ─── GlobalReach API Import ───────────────────────────────────────────────────

@router.post("/leads/import/globalreach")
async def import_from_globalreach(
    body: GlobalReachImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Dogfooding: pull leads from the GlobalReach API for a given ICP.
    GLOBALREACH_API_URL and GLOBALREACH_API_KEY must be configured.
    """
    if not settings.globalreach_api_url or not settings.globalreach_api_key:
        raise HTTPException(status_code=503, detail="GlobalReach API not configured.")

    icp_result = await db.execute(select(ICP).where(ICP.id == body.icp_id))
    icp = icp_result.scalar_one_or_none()
    if not icp:
        raise HTTPException(status_code=404, detail="ICP not found.")

    # Build the search payload from ICP fields
    search_payload = {
        "industry": icp.industry,
        "geography": icp.geography,
        "company_size": icp.company_size,
        "titles": icp.titles,
        "keywords": icp.keywords,
        "limit": body.max_results,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{settings.globalreach_api_url}/leads",
                headers={
                    "Authorization": f"Bearer {settings.globalreach_api_key}",
                    "Content-Type": "application/json",
                },
                json=search_payload,
            )
            response.raise_for_status()
            api_data = response.json()
    except httpx.HTTPError as exc:
        logger.error("GlobalReach API error: %s", exc)
        raise HTTPException(status_code=502, detail=f"GlobalReach API error: {exc}")

    leads_data = api_data.get("leads", api_data.get("results", []))
    imported = 0
    dupes = 0

    for record in leads_data:
        email = (record.get("email") or "").lower().strip()
        if not email:
            continue

        # Dedupe
        existing = await db.execute(select(Lead).where(Lead.email == email))
        if existing.scalar_one_or_none():
            dupes += 1
            continue

        lead = Lead(
            email=email,
            first_name=record.get("first_name"),
            last_name=record.get("last_name"),
            company=record.get("company"),
            title=record.get("title"),
            website=record.get("website"),
            country=record.get("country"),
            industry=record.get("industry") or icp.industry,
            source="globalreach",
            icp_id=icp.id,
            lawful_basis="legitimate_interest_b2b",
        )
        db.add(lead)
        imported += 1

    await write_audit_log(
        db, "leads.imported.globalreach", user_id=current_user.id,
        meta={"icp_id": body.icp_id, "imported": imported, "dupes": dupes}
    )
    await db.commit()

    return {"imported": imported, "duplicates_skipped": dupes, "icp_id": body.icp_id}


# ─── CSV Import ───────────────────────────────────────────────────────────────

@router.post("/leads/import/csv")
async def import_from_csv(
    body: CSVImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Import leads from CSV rows with column mapping.
    Deduplicates by email. Returns count of imported and skipped rows.
    """
    mapping = body.column_mapping
    imported = 0
    dupes = 0
    errors = 0

    for row in body.rows:
        raw_email = row.get(mapping.email, "").strip().lower()
        if not raw_email:
            errors += 1
            continue

        # Dedupe
        existing = await db.execute(select(Lead).where(Lead.email == raw_email))
        if existing.scalar_one_or_none():
            dupes += 1
            continue

        lead = Lead(
            email=raw_email,
            first_name=row.get(mapping.first_name or "", "").strip() or None,
            last_name=row.get(mapping.last_name or "", "").strip() or None,
            company=row.get(mapping.company or "", "").strip() or None,
            title=row.get(mapping.title or "", "").strip() or None,
            website=row.get(mapping.website or "", "").strip() or None,
            country=row.get(mapping.country or "", "").strip() or None,
            industry=row.get(mapping.industry or "", "").strip() or None,
            source="csv",
            icp_id=uuid.UUID(body.icp_id) if body.icp_id else None,
            lawful_basis="legitimate_interest_b2b",
        )
        db.add(lead)
        imported += 1

    await write_audit_log(
        db, "leads.imported.csv", user_id=current_user.id,
        meta={"imported": imported, "dupes": dupes, "errors": errors}
    )
    await db.commit()

    return {"imported": imported, "duplicates_skipped": dupes, "errors": errors}


# ─── Suppression List ─────────────────────────────────────────────────────────

@router.get("/suppression", response_model=list[SuppressionResponse])
async def list_suppression(
    search: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List suppression list entries."""
    q = select(SuppressionList).order_by(SuppressionList.added_at.desc())
    if search:
        q = q.where(SuppressionList.email_or_domain.ilike(f"%{search}%"))
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    return [
        SuppressionResponse(
            id=str(s.id),
            email_or_domain=s.email_or_domain,
            reason=s.reason,
            added_at=s.added_at,
        )
        for s in result.scalars()
    ]


@router.post("/suppression", response_model=SuppressionResponse, status_code=status.HTTP_201_CREATED)
async def add_suppression(
    body: SuppressionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually add an email or domain to the suppression list."""
    existing = await db.execute(
        select(SuppressionList).where(SuppressionList.email_or_domain == body.email_or_domain.lower())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already in suppression list.")

    entry = SuppressionList(
        email_or_domain=body.email_or_domain.lower(),
        reason=body.reason,
        added_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    await db.flush()
    await write_audit_log(
        db, "suppression.added", user_id=current_user.id,
        entity="suppression_list", entity_id=str(entry.id),
        meta={"email_or_domain": body.email_or_domain, "reason": body.reason}
    )
    await db.commit()
    await db.refresh(entry)
    return SuppressionResponse(
        id=str(entry.id), email_or_domain=entry.email_or_domain,
        reason=entry.reason, added_at=entry.added_at
    )


@router.delete("/suppression/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_suppression(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove an entry from the suppression list (with audit log)."""
    result = await db.execute(select(SuppressionList).where(SuppressionList.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Suppression entry not found.")
    await write_audit_log(
        db, "suppression.removed", user_id=current_user.id,
        entity="suppression_list", entity_id=entry_id,
        meta={"email_or_domain": entry.email_or_domain}
    )
    await db.delete(entry)
    await db.commit()


# ─── Unsubscribe Handler (public) ────────────────────────────────────────────

@router.get("/u/{token}", response_class=HTMLResponse, include_in_schema=False)
async def unsubscribe_handler(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Public unsubscribe link. Verifies the signed token, adds email to
    suppression_list, and returns a confirmation page.
    """
    email = verify_unsubscribe_token(token)
    if not email:
        return HTMLResponse(content=_unsub_page("Invalid or expired unsubscribe link.", error=True), status_code=400)

    await add_to_suppression(db, email, reason="unsubscribed")

    # Update lead status
    lead_result = await db.execute(select(Lead).where(Lead.email == email.lower()))
    lead = lead_result.scalar_one_or_none()
    if lead:
        lead.status = "unsubscribed"

    await db.commit()
    logger.info("Unsubscribed: %s", email)
    return HTMLResponse(content=_unsub_page(email))


def _unsub_page(email: str, error: bool = False) -> str:
    if error:
        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Unsubscribe Error</title>
<style>body{{font-family:system-ui;background:#0d0d14;color:#e2e8f0;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}}
.card{{background:#1a1a2e;border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:48px;max-width:400px;text-align:center}}
h1{{color:#f87171;margin-bottom:16px}}p{{color:#94a3b8}}</style></head>
<body><div class="card"><h1>⚠️ Error</h1><p>{email}</p></div></body></html>"""
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Unsubscribed</title>
<style>body{{font-family:system-ui;background:#0d0d14;color:#e2e8f0;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}}
.card{{background:#1a1a2e;border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:48px;max-width:480px;text-align:center}}
h1{{color:#34d399;margin-bottom:16px;font-size:24px}}p{{color:#94a3b8;line-height:1.6}}
.email{{font-family:monospace;background:rgba(255,255,255,.05);padding:4px 12px;border-radius:6px;display:inline-block;margin:12px 0}}</style></head>
<body><div class="card">
<h1>✅ You've been unsubscribed</h1>
<div class="email">{email}</div>
<p>You've been removed from our mailing list and won't receive any further emails from us.</p>
<p style="font-size:13px;margin-top:24px;color:#64748b">If this was a mistake, please reply to our last email.</p>
</div></body></html>"""
