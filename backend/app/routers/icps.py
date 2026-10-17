"""
ICP (Ideal Customer Profile) router.
POST /icps, GET /icps, GET /icps/{id}, PUT /icps/{id}, DELETE /icps/{id}
All routes require authentication.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import User
from app.models.leads import ICP
from app.schemas.leads import ICPCreate, ICPResponse, ICPUpdate
from app.services.audit import write_audit_log

router = APIRouter(prefix="/icps", tags=["icps"])


def _to_response(icp: ICP) -> ICPResponse:
    return ICPResponse(
        id=str(icp.id),
        name=icp.name,
        industry=icp.industry,
        geography=icp.geography,
        company_size=icp.company_size,
        titles=icp.titles if isinstance(icp.titles, list) else None,
        keywords=icp.keywords if isinstance(icp.keywords, list) else None,
        created_at=icp.created_at,
        updated_at=icp.updated_at,
    )


@router.post("", response_model=ICPResponse, status_code=status.HTTP_201_CREATED)
async def create_icp(
    body: ICPCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new ICP."""
    icp = ICP(
        name=body.name,
        industry=body.industry,
        geography=body.geography,
        company_size=body.company_size,
        titles=body.titles,
        keywords=body.keywords,
    )
    db.add(icp)
    await db.flush()
    await write_audit_log(db, "icp.created", user_id=current_user.id, entity="icps", entity_id=str(icp.id))
    await db.commit()
    await db.refresh(icp)
    return _to_response(icp)


@router.get("", response_model=list[ICPResponse])
async def list_icps(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List all ICPs."""
    result = await db.execute(select(ICP).order_by(ICP.created_at.desc()))
    return [_to_response(i) for i in result.scalars()]


@router.get("/{icp_id}", response_model=ICPResponse)
async def get_icp(
    icp_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get a single ICP by ID."""
    result = await db.execute(select(ICP).where(ICP.id == icp_id))
    icp = result.scalar_one_or_none()
    if not icp:
        raise HTTPException(status_code=404, detail="ICP not found.")
    return _to_response(icp)


@router.put("/{icp_id}", response_model=ICPResponse)
async def update_icp(
    icp_id: str,
    body: ICPUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an ICP."""
    result = await db.execute(select(ICP).where(ICP.id == icp_id))
    icp = result.scalar_one_or_none()
    if not icp:
        raise HTTPException(status_code=404, detail="ICP not found.")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(icp, field, value)
    await write_audit_log(db, "icp.updated", user_id=current_user.id, entity="icps", entity_id=icp_id)
    await db.commit()
    await db.refresh(icp)
    return _to_response(icp)


@router.delete("/{icp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_icp(
    icp_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an ICP."""
    result = await db.execute(select(ICP).where(ICP.id == icp_id))
    icp = result.scalar_one_or_none()
    if not icp:
        raise HTTPException(status_code=404, detail="ICP not found.")
    await write_audit_log(db, "icp.deleted", user_id=current_user.id, entity="icps", entity_id=icp_id)
    await db.delete(icp)
    await db.commit()
