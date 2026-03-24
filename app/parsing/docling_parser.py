import asyncio
import io
import tempfile
import os

from app.schemas.document import ParsedDocument

_TIMEOUT = 30


class DoclingParser:
    async def parse(self, file_bytes: bytes, filename: str) -> ParsedDocument:
        return await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, self._parse_sync, file_bytes, filename),
            timeout=_TIMEOUT,
        )

    def _parse_sync(self, file_bytes: bytes, filename: str) -> ParsedDocument:
        from docling.document_converter import DocumentConverter

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            converter = DocumentConverter()
            result = converter.convert(tmp_path)
            text = result.document.export_to_markdown()
            # Count pages from metadata if available
            pages = getattr(result.document, "num_pages", None) or text.count("\f") + 1
        finally:
            os.unlink(tmp_path)

        return ParsedDocument(
            text=text,
            pages=pages,
            filename=filename,
            metadata={"parser": "docling"},
        )
