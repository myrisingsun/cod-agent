"""Unit tests for Sprint 4: chunker, chat API."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.pipeline.chunker import chunk_text
from app.main import app
from app.auth.dependencies import get_current_user
from app.database import get_db
from app.auth.models import User
from app.auth.service import hash_password
from app.models.package import Package
from app.models.chat_message import ChatMessage
from app.rag.base import RetrievedChunk


# ---------------------------------------------------------------------------
# Chunker
# ---------------------------------------------------------------------------

def test_chunk_empty_text():
    assert chunk_text("") == []


def test_chunk_short_text_single_chunk():
    words = ["word"] * 10
    result = chunk_text(" ".join(words), chunk_size=400)
    assert len(result) == 1
    assert result[0] == " ".join(words)


def test_chunk_produces_multiple_chunks():
    words = ["w"] * 1000
    result = chunk_text(" ".join(words), chunk_size=400, overlap_ratio=0.15)
    assert len(result) > 1


def test_chunk_size_respected():
    words = ["w"] * 1000
    result = chunk_text(" ".join(words), chunk_size=400, overlap_ratio=0.15)
    for chunk in result:
        assert len(chunk.split()) <= 400


def test_chunk_overlap_present():
    """Last words of chunk N appear at start of chunk N+1."""
    words = [str(i) for i in range(1000)]
    result = chunk_text(" ".join(words), chunk_size=100, overlap_ratio=0.1)
    assert len(result) >= 2
    end_of_first = result[0].split()[-5:]
    start_of_second = result[1].split()[:10]
    # Overlap means some words from end of chunk 0 appear in start of chunk 1
    assert any(w in start_of_second for w in end_of_first)


def test_chunk_covers_all_words():
    """Union of all chunks contains all words (no data loss)."""
    words = [str(i) for i in range(500)]
    result = chunk_text(" ".join(words), chunk_size=100, overlap_ratio=0.15)
    all_words_in_chunks = set()
    for chunk in result:
        all_words_in_chunks.update(chunk.split())
    assert all_words_in_chunks == set(words)


# ---------------------------------------------------------------------------
# NullRetriever
# ---------------------------------------------------------------------------

async def test_null_retriever_index_is_noop():
    from app.rag.null_retriever import NullRetriever
    r = NullRetriever()
    await r.index(["chunk1", "chunk2"], collection="test")  # should not raise


async def test_null_retriever_retrieve_returns_empty():
    from app.rag.null_retriever import NullRetriever
    r = NullRetriever()
    result = await r.retrieve("query", collection="test")
    assert result == []


# ---------------------------------------------------------------------------
# Chat API helpers
# ---------------------------------------------------------------------------

def _make_user() -> User:
    user = User()
    user.id = uuid.uuid4()
    user.email = "chat@test.com"
    user.full_name = "Tester"
    user.role = "analyst"
    user.is_active = True
    user.hashed_password = hash_password("x")
    return user


def _make_package(user_id: uuid.UUID, status: str = "done") -> Package:
    pkg = Package()
    pkg.id = uuid.uuid4()
    pkg.filename = "doc.pdf"
    pkg.status = status
    pkg.user_id = user_id
    pkg.accuracy = 0.9
    pkg.document_type = None
    pkg.created_at = datetime.now(timezone.utc)
    pkg.updated_at = None
    return pkg


def _make_chat_msg(package_id: uuid.UUID, role: str, content: str) -> ChatMessage:
    msg = ChatMessage()
    msg.id = uuid.uuid4()
    msg.package_id = package_id
    msg.role = role
    msg.content = content
    msg.sources = None
    msg.created_at = datetime.now(timezone.utc)
    return msg


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# POST /packages/{id}/chat
# ---------------------------------------------------------------------------

def test_chat_ask_success(client):
    user = _make_user()
    pkg = _make_package(user.id, status="done")
    assistant_msg = _make_chat_msg(pkg.id, "assistant", "Ответ LLM")
    assistant_msg.sources = [{"text": "фрагмент", "score": 0.9}]

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=pkg)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "id", assistant_msg.id) or
                                setattr(obj, "created_at", assistant_msg.created_at))

    mock_retriever = AsyncMock()
    mock_retriever.retrieve = AsyncMock(return_value=[
        RetrievedChunk(text="фрагмент", score=0.9, metadata={"package_id": str(pkg.id)})
    ])

    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value="Ответ LLM")

    async def override_db():
        yield mock_db

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = override_db

    try:
        with patch("app.api.routes_chat.get_retriever", return_value=mock_retriever), \
             patch("app.api.routes_chat.get_llm_client", return_value=mock_llm):
            resp = client.post(f"/packages/{pkg.id}/chat", json={"question": "Кто залогодатель?"})
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"] == "Ответ LLM"
    assert len(data["sources"]) == 1
    assert data["sources"][0]["text"] == "фрагмент"


def test_chat_ask_package_not_ready(client):
    user = _make_user()
    pkg = _make_package(user.id, status="processing")
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=pkg)

    async def override_db():
        yield mock_db

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = override_db

    try:
        resp = client.post(f"/packages/{pkg.id}/chat", json={"question": "Вопрос?"})
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 409


def test_chat_ask_package_not_found(client):
    user = _make_user()
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=None)

    async def override_db():
        yield mock_db

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = override_db

    try:
        resp = client.post(f"/packages/{uuid.uuid4()}/chat", json={"question": "?"})
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 404


def test_chat_ask_no_token_returns_401(client):
    resp = client.post(f"/packages/{uuid.uuid4()}/chat", json={"question": "?"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /packages/{id}/chat/history
# ---------------------------------------------------------------------------

def test_chat_history_returns_messages(client):
    user = _make_user()
    pkg = _make_package(user.id)
    msgs = [
        _make_chat_msg(pkg.id, "user", "Вопрос"),
        _make_chat_msg(pkg.id, "assistant", "Ответ"),
    ]

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=pkg)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = msgs
    mock_db.execute = AsyncMock(return_value=mock_result)

    async def override_db():
        yield mock_db

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = override_db

    try:
        resp = client.get(f"/packages/{pkg.id}/chat/history")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["role"] == "user"
    assert data[1]["role"] == "assistant"


def test_chat_history_empty(client):
    user = _make_user()
    pkg = _make_package(user.id)
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=pkg)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    async def override_db():
        yield mock_db

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = override_db

    try:
        resp = client.get(f"/packages/{pkg.id}/chat/history")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json() == []


def test_chat_history_not_found(client):
    user = _make_user()
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=None)

    async def override_db():
        yield mock_db

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = override_db

    try:
        resp = client.get(f"/packages/{uuid.uuid4()}/chat/history")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 404
