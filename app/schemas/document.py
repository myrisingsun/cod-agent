from pydantic import BaseModel


class ParsedDocument(BaseModel):
    """Output contract of the parsing module."""
    text: str
    pages: int
    filename: str
    metadata: dict = {}
