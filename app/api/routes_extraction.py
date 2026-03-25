import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.models.package import Package
from app.models.extraction_result import ExtractionResult as ExtractionResultModel
from app.schemas.extraction import PledgeFields, FieldConfidence
from app.pipeline.process_package import process_package

router = APIRouter(prefix="/packages", tags=["extraction"])


class ExtractionResponse(BaseModel):
    package_id: uuid.UUID
    fields: PledgeFields
    confidence: FieldConfidence
    accuracy: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


@router.get("/{package_id}/extraction", response_model=ExtractionResponse)
async def get_extraction(
    package_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExtractionResponse:
    package = await db.get(Package, package_id)
    if package is None or package.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Package not found")

    result = await db.execute(
        select(ExtractionResultModel).where(ExtractionResultModel.package_id == package_id)
    )
    extraction = result.scalar_one_or_none()
    if extraction is None:
        raise HTTPException(status_code=404, detail="Extraction result not found — package may still be processing")

    return ExtractionResponse(
        package_id=package_id,
        fields=PledgeFields(**extraction.fields),
        confidence=FieldConfidence(**extraction.confidence),
        accuracy=package.accuracy,
        created_at=extraction.created_at,
        updated_at=extraction.updated_at,
    )


@router.post("/{package_id}/extraction/retry", status_code=202)
async def retry_extraction(
    package_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    package = await db.get(Package, package_id)
    if package is None or package.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Package not found")

    if package.status == "processing":
        raise HTTPException(status_code=409, detail="Package is already being processed")

    # Remove previous extraction result if exists
    result = await db.execute(
        select(ExtractionResultModel).where(ExtractionResultModel.package_id == package_id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        await db.delete(existing)
        await db.commit()

    package.status = "received"
    package.updated_at = datetime.now(timezone.utc)
    await db.commit()

    background_tasks.add_task(process_package, package_id, db)
    return {"status": "accepted", "package_id": str(package_id)}
