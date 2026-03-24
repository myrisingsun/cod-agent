from typing import Protocol, runtime_checkable
from app.schemas.document import ParsedDocument
from app.schemas.extraction import ExtractionResult


@runtime_checkable
class BaseExtractor(Protocol):
    async def extract(self, parsed_doc: ParsedDocument, doc_type: str = "pledge") -> ExtractionResult: ...
