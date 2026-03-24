from app.config import Settings
from app.llm.base import BaseLLMClient


def get_llm_client(settings: Settings) -> BaseLLMClient:
    from app.llm.openai_compat import OpenAICompatClient
    return OpenAICompatClient(
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        timeout=settings.llm_timeout,
    )
