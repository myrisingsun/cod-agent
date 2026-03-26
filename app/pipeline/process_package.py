"""Background task: runs full processing pipeline for a package."""
import logging
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

logger = logging.getLogger(__name__)


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
    logger.info("pipeline start package_id=%s filename=%s", package_id, package.filename)

    try:
        # Step 1: fetch file bytes from storage
        storage = get_storage(settings)
        file_bytes = await storage.get_file(str(package_id), package.filename)
        logger.info("pipeline step=fetch bytes=%d package_id=%s", len(file_bytes), package_id)

        # Step 2: parse PDF → text
        parser = get_parser(settings)
        parsed = await parser.parse(file_bytes, package.filename)
        logger.info("pipeline step=parse chars=%d pages=%d package_id=%s", len(parsed.text), parsed.pages, package_id)

        # Step 3: PII filter (noop in dev)
        pii_filter = get_pii_filter(settings)
        clean_text = pii_filter.filter(parsed.text)
        parsed_clean = ParsedDocument(
            text=clean_text,
            pages=parsed.pages,
            filename=parsed.filename,
            metadata=parsed.metadata,
        )

        # Step 4: RAG indexing — delete old vectors first (safe on first run too), then re-index
        retriever = get_retriever(settings)
        await retriever.delete_by_filter("current_packages", str(package_id))
        chunks = chunk_text(clean_text)
        chunk_meta = [{"package_id": str(package_id), "filename": package.filename} for _ in chunks]
        await retriever.index(chunks, collection="current_packages", metadata=chunk_meta)
        logger.info("pipeline step=rag_index chunks=%d package_id=%s", len(chunks), package_id)

        # Step 5: LLM extraction (retriever supplies few-shot from reference_templates)
        llm_client = get_llm_client(settings)
        extractor = get_extractor(settings, llm_client, retriever)
        logger.info("pipeline step=llm_extract start package_id=%s", package_id)
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
        logger.info(
            "pipeline done package_id=%s document_type=%s accuracy=%s",
            package_id, package.document_type, package.accuracy,
        )

    except Exception:  # noqa: BLE001
        package.status = "error"
        package.updated_at = datetime.now(timezone.utc)
        await db.commit()
        logger.exception("pipeline error package_id=%s", package_id)
        raise
