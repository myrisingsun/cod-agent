"""Qdrant-backed retriever using BGE-M3 embeddings (sentence-transformers)."""
from __future__ import annotations

import asyncio
import uuid
from functools import lru_cache
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
)
from sentence_transformers import SentenceTransformer

from app.rag.base import RetrievedChunk

_VECTOR_SIZE = 1024  # BGE-M3 output dimension


@lru_cache(maxsize=1)
def _load_model(model_name: str, device: str) -> SentenceTransformer:
    return SentenceTransformer(model_name, device=device)


class QdrantRetriever:
    def __init__(self, qdrant_url: str, embedding_model: str, embedding_device: str) -> None:
        self._client = QdrantClient(url=qdrant_url)
        self._model_name = embedding_model
        self._device = embedding_device

    def _model(self) -> SentenceTransformer:
        return _load_model(self._model_name, self._device)

    def _embed(self, texts: list[str]) -> list[list[float]]:
        return self._model().encode(texts, normalize_embeddings=True).tolist()

    def _ensure_collection(self, collection: str) -> None:
        existing = {c.name for c in self._client.get_collections().collections}
        if collection not in existing:
            self._client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(size=_VECTOR_SIZE, distance=Distance.COSINE),
            )

    async def index(
        self,
        chunks: list[str],
        collection: str,
        metadata: list[dict] | None = None,
    ) -> None:
        if not chunks:
            return
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._index_sync, chunks, collection, metadata)

    def _index_sync(self, chunks: list[str], collection: str, metadata: list[dict] | None) -> None:
        self._ensure_collection(collection)
        vectors = self._embed(chunks)
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload={"text": chunk, **(metadata[i] if metadata else {})},
            )
            for i, (chunk, vec) in enumerate(zip(chunks, vectors))
        ]
        self._client.upsert(collection_name=collection, points=points)

    async def retrieve(
        self,
        query: str,
        collection: str,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._retrieve_sync, query, collection, top_k)

    def _retrieve_sync(self, query: str, collection: str, top_k: int) -> list[RetrievedChunk]:
        existing = {c.name for c in self._client.get_collections().collections}
        if collection not in existing:
            return []

        vector = self._embed([query])[0]
        response = self._client.query_points(
            collection_name=collection,
            query=vector,
            limit=top_k,
        )
        return [
            RetrievedChunk(
                text=hit.payload.get("text", ""),
                score=hit.score,
                metadata={k: v for k, v in hit.payload.items() if k != "text"},
            )
            for hit in response.points
        ]
