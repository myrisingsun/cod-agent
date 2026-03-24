from app.config import Settings
from app.rag.base import BaseRetriever


def get_retriever(settings: Settings) -> BaseRetriever:
    from app.rag.qdrant_retriever import QdrantRetriever
    return QdrantRetriever(
        qdrant_url=settings.qdrant_url,
        embedding_model=settings.embedding_model,
        embedding_device=settings.embedding_device,
    )
