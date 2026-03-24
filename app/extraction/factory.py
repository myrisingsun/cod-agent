from app.config import Settings
from app.extraction.base import BaseExtractor
from app.llm.base import BaseLLMClient
from app.rag.base import BaseRetriever


def get_extractor(settings: Settings, llm_client: BaseLLMClient, retriever: BaseRetriever) -> BaseExtractor:
    from app.extraction.llm_extractor import LLMExtractor
    return LLMExtractor(llm_client=llm_client, retriever=retriever)
