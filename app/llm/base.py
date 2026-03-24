from typing import Protocol, runtime_checkable, Optional


@runtime_checkable
class BaseLLMClient(Protocol):
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: Optional[dict] = None,
    ) -> str: ...
