from app.rag.base import RetrievedChunk


class NullRetriever:
    """No-op retriever stub used before Sprint 4 (RAG)."""

    async def index(self, chunks: list[str], collection: str, metadata: list[dict] | None = None) -> None:
        pass

    async def retrieve(
        self, query: str, collection: str, top_k: int = 5, filter_metadata: dict | None = None
    ) -> list[RetrievedChunk]:
        return []

    async def delete_by_filter(self, collection: str, package_id: str) -> None:
        pass
