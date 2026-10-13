from typing import Any

from botocore.exceptions import BotoCoreError, ClientError

from common.errors import NotFound, StorageError


class S3Storage:
    def __init__(self, bucket: str, client: Any) -> None:
        self._bucket = bucket
        self._client = client

    def put(self, key: str, body: bytes, content_type: str) -> None:
        try:
            self._client.put_object(Bucket=self._bucket, Key=key, Body=body, ContentType=content_type)
        except (ClientError, BotoCoreError) as e:
            raise StorageError(f"put failed: key={key}") from e

    def get(self, key: str) -> bytes:
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
        except ClientError as e:
            if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
                raise NotFound(f"object not found: key={key}") from e
            raise StorageError(f"get failed: key={key}") from e
        except BotoCoreError as e:
            raise StorageError(f"get failed: key={key}") from e
        body: bytes = response["Body"].read()
        return body

    def delete(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except (ClientError, BotoCoreError) as e:
            raise StorageError(f"delete failed: key={key}") from e

    def presigned_url(self, key: str, expires_in: int = 3600) -> str:
        try:
            url: str = self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        except (ClientError, BotoCoreError) as e:
            raise StorageError(f"presigned_url failed: key={key}") from e
        return url
