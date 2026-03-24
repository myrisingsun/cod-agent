"""Background task: runs parsing pipeline for a package (Sprint 2: steps 1-3)."""
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.package import Package
from app.storage.factory import get_storage
from app.parsing.factory import get_parser
from app.config import settings


async def process_package(package_id: uuid.UUID, db: AsyncSession) -> None:
    package = await db.get(Package, package_id)
    if package is None:
        return

    package.status = "processing"
    package.updated_at = datetime.now(timezone.utc)
    await db.commit()

    try:
        storage = get_storage(settings)
        parser = get_parser(settings)

        file_bytes = await storage.get_file(str(package_id), package.filename)
        parsed = await parser.parse(file_bytes, package.filename)

        # TODO Sprint 3: PII filter + LLM extraction
        # TODO Sprint 4: RAG indexing

        package.status = "parsed"
        package.updated_at = datetime.now(timezone.utc)
        await db.commit()

    except Exception as exc:  # noqa: BLE001
        package.status = "error"
        package.updated_at = datetime.now(timezone.utc)
        await db.commit()
        raise
