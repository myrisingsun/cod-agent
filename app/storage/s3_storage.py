import io
import boto3
from botocore.exceptions import ClientError

from app.storage.base import BaseStorage


class S3Storage:
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str) -> None:
        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="us-east-1",
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self._bucket)

    async def save_file(self, file_id: str, content: bytes, filename: str) -> str:
        key = f"{file_id}/{filename}"
        self._client.put_object(Bucket=self._bucket, Key=key, Body=content)
        return key

    async def get_file(self, file_id: str, filename: str) -> bytes:
        key = f"{file_id}/{filename}"
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        return response["Body"].read()

    async def delete_file(self, file_id: str, filename: str) -> None:
        key = f"{file_id}/{filename}"
        self._client.delete_object(Bucket=self._bucket, Key=key)
