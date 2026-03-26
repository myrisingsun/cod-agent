import asyncio
import logging
from typing import Optional

from openai import AsyncOpenAI, APIConnectionError, APITimeoutError, InternalServerError

logger = logging.getLogger(__name__)

_RETRYABLE = (APIConnectionError, APITimeoutError, InternalServerError)
_MAX_ATTEMPTS = 3
_BACKOFF_BASE = 2.0  # seconds


class OpenAICompatClient:
    """OpenAI-compatible async client (works with Ollama, vLLM, OpenAI)."""

    def __init__(self, base_url: str, model: str, timeout: int) -> None:
        self._client = AsyncOpenAI(
            base_url=base_url,
            api_key="ollama",  # required by openai SDK, ignored by Ollama/vLLM
            timeout=float(timeout),
        )
        self._model = model

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: Optional[dict] = None,
    ) -> str:
        kwargs: dict = {}
        if json_schema is not None:
            kwargs["response_format"] = {"type": "json_object"}

        last_exc: Exception | None = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    **kwargs,
                )
                return response.choices[0].message.content or ""
            except _RETRYABLE as exc:
                last_exc = exc
                if attempt < _MAX_ATTEMPTS:
                    wait = _BACKOFF_BASE ** attempt
                    logger.warning(
                        "LLM request failed (attempt %d/%d): %s — retrying in %.1fs",
                        attempt, _MAX_ATTEMPTS, exc, wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error("LLM request failed after %d attempts: %s", _MAX_ATTEMPTS, exc)
        raise last_exc  # type: ignore[misc]
