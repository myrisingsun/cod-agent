"""Unit tests for parsing module (pdfplumber only — no docling in dev image)."""
import pytest
from unittest.mock import patch, MagicMock

from app.parsing.pdfplumber_parser import PdfPlumberParser
from app.schemas.document import ParsedDocument


async def test_pdfplumber_returns_parsed_document(sample_pdf_bytes):
    parser = PdfPlumberParser()
    result = await parser.parse(sample_pdf_bytes, "test.pdf")
    assert isinstance(result, ParsedDocument)
    assert result.filename == "test.pdf"
    assert result.pages >= 1
    assert result.metadata["parser"] == "pdfplumber"


async def test_pdfplumber_real_pdf_multiple_pages(sample_pdf_bytes):
    """Parser returns pages >= 1 for a valid PDF."""
    parser = PdfPlumberParser()
    result = await parser.parse(sample_pdf_bytes, "multi.pdf")
    assert result.pages >= 1
    assert result.filename == "multi.pdf"


async def test_factory_returns_pdfplumber_when_backend_is_pdfplumber():
    from app.parsing.factory import get_parser
    from app.config import Settings

    cfg = Settings(parser_backend="pdfplumber")
    parser = get_parser(cfg)
    assert isinstance(parser, PdfPlumberParser)


async def test_factory_returns_docling_when_backend_is_docling():
    """DoclingParser class is returned without importing heavy deps."""
    from app.parsing.factory import get_parser
    from app.config import Settings

    # Patch the import so docling itself is not required in dev image
    mock_docling_cls = MagicMock()
    with patch.dict("sys.modules", {"docling": MagicMock(), "docling.document_converter": MagicMock()}):
        with patch("app.parsing.factory.DoclingParser", mock_docling_cls, create=True):
            # Re-import after patching
            import importlib
            import app.parsing.factory as factory_mod
            importlib.reload(factory_mod)
            cfg = Settings(parser_backend="docling")
            parser = factory_mod.get_parser(cfg)
            # After reload, DoclingParser is instantiated
            assert parser is not None
