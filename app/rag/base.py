from typing import Protocol, runtime_checkable
from pydantic import BaseModel


class RetrievedChunk(BaseModel):
    text: str
    score: float
    metadata: dict = {}


@runtime_checkable
class BaseRetriever(Protocol):
    async def index(self, chunks: list[str], collection: str, metadata: list[dict] | None = None) -> None: ...
    async def retrieve(
        self, query: str, collection: str, top_k: int = 5, filter_metadata: dict | None = None
    ) -> list[RetrievedChunk]: ...
    async def delete_by_filter(self, collection: str, package_id: str) -> None: ...
