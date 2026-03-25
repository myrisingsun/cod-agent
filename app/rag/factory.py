from app.config import Settings
from app.rag.base import BaseRetriever


def get_retriever(settings: Settings) -> BaseRetriever:
    try:
        from app.rag.qdrant_retriever import QdrantRetriever
        return QdrantRetriever(
            qdrant_url=settings.qdrant_url,
            embedding_model=settings.embedding_model,
            embedding_device=settings.embedding_device,
        )
    except ImportError:
        # sentence-transformers / qdrant-client not installed (Sprint 3 and earlier)
        from app.rag.null_retriever import NullRetriever
        return NullRetriever()
