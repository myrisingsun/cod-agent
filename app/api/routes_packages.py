import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.models.package import Package
from app.schemas.package import PackageResponse
from app.storage.factory import get_storage
from app.config import settings
from app.pipeline.process_package import process_package

router = APIRouter(prefix="/packages", tags=["packages"])

_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("", response_model=PackageResponse, status_code=status.HTTP_201_CREATED)
async def upload_package(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PackageResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    content = await file.read()
    if len(content) > _MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 50 MB limit")

    package = Package(
        id=uuid.uuid4(),
        filename=file.filename,
        status="received",
        user_id=current_user.id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(package)
    await db.commit()
    await db.refresh(package)

    storage = get_storage(settings)
    await storage.save_file(str(package.id), content, file.filename)

    background_tasks.add_task(process_package, package.id)

    return PackageResponse.model_validate(package)


@router.get("", response_model=list[PackageResponse])
async def list_packages(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PackageResponse]:
    result = await db.execute(
        select(Package).where(Package.user_id == current_user.id).order_by(Package.created_at.desc())
    )
    packages = result.scalars().all()
    return [PackageResponse.model_validate(p) for p in packages]


@router.get("/{package_id}", response_model=PackageResponse)
async def get_package(
    package_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PackageResponse:
    package = await db.get(Package, package_id)
    if package is None or package.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Package not found")
    return PackageResponse.model_validate(package)


@router.delete("/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_package(
    package_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    package = await db.get(Package, package_id)
    if package is None or package.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Package not found")
    if package.status == "processing":
        raise HTTPException(status_code=409, detail="Cannot delete a package that is currently being processed")

    try:
        storage = get_storage(settings)
        await storage.delete_file(str(package_id), package.filename)
    except Exception:  # noqa: BLE001
        pass  # File may not exist in storage; proceed with DB deletion

    await db.delete(package)
    await db.commit()
