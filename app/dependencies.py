from app.config import settings
from app.parsing.factory import get_parser
from app.llm.factory import get_llm_client
from app.extraction.factory import get_extractor
from app.pii.factory import get_pii_filter
from app.rag.factory import get_retriever
from app.storage.factory import get_storage


def build_pipeline():
    """Assemble all modules based on .env settings."""
    storage = get_storage(settings)
    parser = get_parser(settings)
    pii_filter = get_pii_filter(settings)
    llm_client = get_llm_client(settings)
    retriever = get_retriever(settings)
    extractor = get_extractor(settings, llm_client, retriever)
    return storage, parser, pii_filter, extractor, retriever
