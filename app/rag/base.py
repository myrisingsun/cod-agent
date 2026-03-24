from typing import Protocol, runtime_checkable
from pydantic import BaseModel


class RetrievedChunk(BaseModel):
    text: str
    score: float
    metadata: dict = {}


@runtime_checkable
class BaseRetriever(Protocol):
    async def retrieve(self, query: str, collection: str, top_k: int = 5) -> list[RetrievedChunk]: ...
