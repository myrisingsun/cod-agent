from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://cod:cod@postgres:5432/cod_agent"
    s3_endpoint: str = "http://minio:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "cod-documents"
    llm_base_url: str = "http://ollama:11434/v1"
    llm_model: str = "qwen2.5:7b"
    llm_timeout: int = 120
    embedding_model: str = "BAAI/bge-m3"
    embedding_device: str = "cpu"
    qdrant_url: str = "http://qdrant:6333"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    parser_backend: str = "docling"
    pii_filter: str = "noop"
    queue_backend: str = "background_tasks"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
