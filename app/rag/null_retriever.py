from app.rag.base import RetrievedChunk


class NullRetriever:
    """No-op retriever stub used before Sprint 4 (RAG)."""

    async def index(self, chunks: list[str], collection: str, metadata: list[dict] | None = None) -> None:
        pass

    async def retrieve(self, query: str, collection: str, top_k: int = 5) -> list[RetrievedChunk]:
        return []
