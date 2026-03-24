import io
import pdfplumber

from app.schemas.document import ParsedDocument


class PdfPlumberParser:
    async def parse(self, file_bytes: bytes, filename: str) -> ParsedDocument:
        pages_text: list[str] = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages_text.append(text)
        return ParsedDocument(
            text="\n\n".join(pages_text),
            pages=len(pages_text),
            filename=filename,
            metadata={"parser": "pdfplumber"},
        )
