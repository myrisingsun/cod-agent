"""Background task: runs full processing pipeline for a package."""
import uuid
from datetime import datetime, timezone

from app.models.package import Package
from app.models.extraction_result import ExtractionResult as ExtractionResultModel
from app.storage.factory import get_storage
from app.parsing.factory import get_parser
from app.pii.factory import get_pii_filter
from app.llm.factory import get_llm_client
from app.rag.factory import get_retriever
from app.extraction.factory import get_extractor
from app.pipeline.chunker import chunk_text
from app.schemas.document import ParsedDocument
from app.config import settings
from app.database import async_session


async def process_package(package_id: uuid.UUID) -> None:
    async with async_session() as db:
        await _run(package_id, db)


async def _run(package_id: uuid.UUID, db) -> None:
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
        clean_text = pii_filter.filter(parsed.text)
        parsed_clean = ParsedDocument(
            text=clean_text,
            pages=parsed.pages,
            filename=parsed.filename,
            metadata=parsed.metadata,
        )

        # Step 4: RAG indexing — chunk and store in current_packages collection
        retriever = get_retriever(settings)
        chunks = chunk_text(clean_text)
        chunk_meta = [{"package_id": str(package_id), "filename": package.filename} for _ in chunks]
        await retriever.index(chunks, collection="current_packages", metadata=chunk_meta)

        # Step 5: LLM extraction (retriever supplies few-shot from reference_templates)
        llm_client = get_llm_client(settings)
        extractor = get_extractor(settings, llm_client, retriever)
        result = await extractor.extract(parsed_clean)

        # Step 6: persist ExtractionResult
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

        # Determine document type: if all confidences are 0 → not a pledge contract
        conf_values = [
            v for field, v in result.confidence.model_dump().items()
            if getattr(result.fields, field) is not None
        ]
        all_conf = list(result.confidence.model_dump().values())
        mean_conf = sum(all_conf) / len(all_conf) if all_conf else 0.0
        if mean_conf < 0.1:
            package.document_type = "not_pledge"
            package.accuracy = None
        else:
            package.document_type = "pledge"
            package.accuracy = round(sum(conf_values) / len(conf_values), 4) if conf_values else None
        package.status = "done"
        package.updated_at = now
        await db.commit()

    except Exception:  # noqa: BLE001
        package.status = "error"
        package.updated_at = datetime.now(timezone.utc)
        await db.commit()
        raise
