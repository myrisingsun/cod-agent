from app.config import Settings
from app.storage.base import BaseStorage


def get_storage(settings: Settings) -> BaseStorage:
    from app.storage.s3_storage import S3Storage
    return S3Storage(
        endpoint=settings.s3_endpoint,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        bucket=settings.s3_bucket,
    )
