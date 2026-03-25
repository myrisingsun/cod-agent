"""Q&A chat API: RAG-powered question answering over uploaded documents."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.models.package import Package
from app.models.chat_message import ChatMessage
from app.rag.factory import get_retriever
from app.llm.factory import get_llm_client
from app.config import settings

router = APIRouter(prefix="/packages", tags=["chat"])

_CHAT_SYSTEM_PROMPT = """\
Ты — ассистент, который отвечает на вопросы по залоговому договору.
Отвечай строго на основе предоставленных фрагментов документа.
Если ответ не найден в документе — честно скажи об этом.
Приводи дословные цитаты из документа в квадратных скобках [«цитата»].
"""

_TOP_K = 5


class ChatRequest(BaseModel):
    question: str


class SourceChunk(BaseModel):
    text: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    message_id: uuid.UUID
    created_at: datetime


class ChatHistoryItem(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    sources: list[SourceChunk] | None
    created_at: datetime


@router.post("/{package_id}/chat", response_model=ChatResponse)
async def ask(
    package_id: uuid.UUID,
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    package = await db.get(Package, package_id)
    if package is None or package.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Package not found")

    if package.status not in ("done", "parsed"):
        raise HTTPException(
            status_code=409,
            detail=f"Package is not ready for Q&A (status={package.status})",
        )

    # Retrieve relevant chunks
    retriever = get_retriever(settings)
    chunks = await retriever.retrieve(
        query=body.question,
        collection="current_packages",
        top_k=_TOP_K,
    )

    # Filter chunks belonging to this package
    pkg_chunks = [c for c in chunks if c.metadata.get("package_id") == str(package_id)]
    if not pkg_chunks:
        pkg_chunks = chunks  # fallback: use all top-k results

    context_text = "\n\n---\n\n".join(c.text for c in pkg_chunks)
    user_prompt = f"Фрагменты документа:\n{context_text}\n\nВопрос: {body.question}"

    llm = get_llm_client(settings)
    answer = await llm.complete(system_prompt=_CHAT_SYSTEM_PROMPT, user_prompt=user_prompt)

    now = datetime.now(timezone.utc)
    sources_payload = [{"text": c.text, "score": c.score} for c in pkg_chunks]

    # Persist user message
    user_msg = ChatMessage(
        package_id=package_id,
        role="user",
        content=body.question,
        sources=None,
        created_at=now,
    )
    db.add(user_msg)

    # Persist assistant message
    assistant_msg = ChatMessage(
        package_id=package_id,
        role="assistant",
        content=answer,
        sources=sources_payload,
        created_at=now,
    )
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)

    return ChatResponse(
        answer=answer,
        sources=[SourceChunk(text=c.text, score=c.score) for c in pkg_chunks],
        message_id=assistant_msg.id,
        created_at=assistant_msg.created_at,
    )


@router.get("/{package_id}/chat/history", response_model=list[ChatHistoryItem])
async def chat_history(
    package_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ChatHistoryItem]:
    package = await db.get(Package, package_id)
    if package is None or package.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Package not found")

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.package_id == package_id)
        .order_by(ChatMessage.created_at)
    )
    messages = result.scalars().all()

    return [
        ChatHistoryItem(
            id=m.id,
            role=m.role,
            content=m.content,
            sources=[SourceChunk(**s) for s in m.sources] if m.sources else None,
            created_at=m.created_at,
        )
        for m in messages
    ]
