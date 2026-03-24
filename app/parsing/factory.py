from app.config import Settings
from app.parsing.base import BaseParser


def get_parser(settings: Settings) -> BaseParser:
    if settings.parser_backend == "docling":
        from app.parsing.docling_parser import DoclingParser
        return DoclingParser()
    from app.parsing.pdfplumber_parser import PdfPlumberParser
    return PdfPlumberParser()
