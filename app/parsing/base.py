from typing import Protocol, runtime_checkable
from app.schemas.document import ParsedDocument


@runtime_checkable
class BaseParser(Protocol):
    async def parse(self, file_bytes: bytes, filename: str) -> ParsedDocument: ...
