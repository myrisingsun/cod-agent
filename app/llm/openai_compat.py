from openai import AsyncOpenAI
from typing import Optional


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

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            **kwargs,
        )
        return response.choices[0].message.content or ""
