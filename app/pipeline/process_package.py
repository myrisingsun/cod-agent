"""Background task: runs full processing pipeline for a package."""
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.package import Package
from app.models.extraction_result import ExtractionResult as ExtractionResultModel
from app.storage.factory import get_storage
from app.parsing.factory import get_parser
from app.pii.factory import get_pii_filter
from app.llm.factory import get_llm_client
from app.rag.factory import get_retriever
from app.extraction.factory import get_extractor
from app.config import settings


async def process_package(package_id: uuid.UUID, db: AsyncSession) -> None:
    package = await db.get(Package, package_id)
    if package is None:
        return

    package.status = "processing"
    package.updated_at = datetime.now(timezone.utc)
    await db.commit()

    try:
        # Step 1: fetch file bytes from storage
        storage = get_storage(settings)
        file_bytes = await storage.get_file(str(package_id), package.filename)

        # Step 2: parse PDF → text
        parser = get_parser(settings)
        parsed = await parser.parse(file_bytes, package.filename)

        # Step 3: PII filter (noop in dev)
        pii_filter = get_pii_filter(settings)
        from app.schemas.document import ParsedDocument
        clean_text = pii_filter.filter(parsed.text)
        parsed_clean = ParsedDocument(
            text=clean_text,
            pages=parsed.pages,
            filename=parsed.filename,
            metadata=parsed.metadata,
        )

        # Step 4: LLM extraction (Sprint 3)
        llm_client = get_llm_client(settings)
        retriever = get_retriever(settings)  # NullRetriever until Sprint 4
        extractor = get_extractor(settings, llm_client, retriever)
        result = await extractor.extract(parsed_clean)

        # Step 5: persist ExtractionResult
        now = datetime.now(timezone.utc)
        db_result = ExtractionResultModel(
            package_id=package_id,
            fields=result.fields.model_dump(),
            confidence=result.confidence.model_dump(),
            raw_llm_response=result.raw_llm_response,
            created_at=now,
            updated_at=now,
        )
        db.add(db_result)

        # Compute overall accuracy = mean confidence of non-null fields
        conf_values = [
            v for field, v in result.confidence.model_dump().items()
            if getattr(result.fields, field) is not None
        ]
        package.accuracy = round(sum(conf_values) / len(conf_values), 4) if conf_values else None
        package.status = "done"
        package.updated_at = now
        await db.commit()

    except Exception:  # noqa: BLE001
        package.status = "error"
        package.updated_at = datetime.now(timezone.utc)
        await db.commit()
        raise
