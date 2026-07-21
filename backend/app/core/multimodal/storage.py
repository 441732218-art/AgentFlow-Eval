# (c) 2026 AgentFlow-Eval
"""Object storage backends: local filesystem and S3/MinIO-compatible."""

from __future__ import annotations

import hashlib
import logging
import mimetypes
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.multimodal.types import StoredObject

logger = logging.getLogger(__name__)


class ObjectStorage(ABC):
    """Abstract blob storage."""

    backend_name: str = "abstract"

    @abstractmethod
    async def put(
        self,
        data: bytes,
        *,
        filename: str,
        content_type: str | None = None,
        prefix: str = "uploads",
    ) -> StoredObject:
        """Store bytes and return a storage reference."""

    @abstractmethod
    async def get(self, key: str) -> bytes:
        """Fetch object bytes by key."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete object if present."""

    @abstractmethod
    async def exists(self, key: str) -> bool:
        ...

    def make_key(self, filename: str, prefix: str = "uploads") -> str:
        safe = Path(filename).name.replace(" ", "_")
        return f"{prefix.strip('/')}/{uuid.uuid4().hex}_{safe}"


class LocalStorage(ObjectStorage):
    """Store files under a local directory (dev / single-node)."""

    backend_name = "local"

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # Prevent path traversal
        path = (self.root / key).resolve()
        if not str(path).startswith(str(self.root.resolve())):
            raise ValueError("Invalid storage key")
        return path

    async def put(
        self,
        data: bytes,
        *,
        filename: str,
        content_type: str | None = None,
        prefix: str = "uploads",
    ) -> StoredObject:
        key = self.make_key(filename, prefix=prefix)
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        ct = content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        return StoredObject(
            key=key,
            backend=self.backend_name,
            size_bytes=len(data),
            content_type=ct,
            etag=hashlib.sha256(data).hexdigest()[:16],
            url=f"file://{path}",
        )

    async def get(self, key: str) -> bytes:
        path = self._path(key)
        if not path.is_file():
            raise FileNotFoundError(key)
        return path.read_bytes()

    async def delete(self, key: str) -> None:
        path = self._path(key)
        if path.is_file():
            path.unlink()

    async def exists(self, key: str) -> bool:
        return self._path(key).is_file()


class S3Storage(ObjectStorage):
    """S3 / MinIO compatible storage via boto3 (optional dependency)."""

    backend_name = "s3"

    def __init__(
        self,
        *,
        bucket: str,
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        region: str = "us-east-1",
        prefix: str = "",
    ) -> None:
        try:
            import boto3
            from botocore.client import Config
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "boto3 is required for S3/MinIO storage. pip install boto3"
            ) from exc

        self.bucket = bucket
        self.key_prefix = prefix.strip("/")
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url or None,
            aws_access_key_id=access_key or None,
            aws_secret_access_key=secret_key or None,
            region_name=region,
            config=Config(signature_version="s3v4"),
        )

    def _full_key(self, key: str) -> str:
        if self.key_prefix:
            return f"{self.key_prefix}/{key}"
        return key

    async def put(
        self,
        data: bytes,
        *,
        filename: str,
        content_type: str | None = None,
        prefix: str = "uploads",
    ) -> StoredObject:
        import asyncio

        key = self.make_key(filename, prefix=prefix)
        full = self._full_key(key)
        ct = content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"

        def _upload() -> None:
            self._client.put_object(
                Bucket=self.bucket,
                Key=full,
                Body=data,
                ContentType=ct,
            )

        await asyncio.to_thread(_upload)
        return StoredObject(
            key=key,
            backend=self.backend_name,
            size_bytes=len(data),
            content_type=ct,
            etag=hashlib.sha256(data).hexdigest()[:16],
            url=f"s3://{self.bucket}/{full}",
        )

    async def get(self, key: str) -> bytes:
        import asyncio

        full = self._full_key(key)

        def _download() -> bytes:
            obj = self._client.get_object(Bucket=self.bucket, Key=full)
            return obj["Body"].read()

        return await asyncio.to_thread(_download)

    async def delete(self, key: str) -> None:
        import asyncio

        full = self._full_key(key)
        await asyncio.to_thread(
            self._client.delete_object, Bucket=self.bucket, Key=full
        )

    async def exists(self, key: str) -> bool:
        import asyncio
        from botocore.exceptions import ClientError

        full = self._full_key(key)

        def _head() -> bool:
            try:
                self._client.head_object(Bucket=self.bucket, Key=full)
                return True
            except ClientError:
                return False

        return await asyncio.to_thread(_head)


def get_storage() -> ObjectStorage:
    """Factory from application settings."""
    from app.config import settings

    backend = str(getattr(settings, "STORAGE_BACKEND", "local") or "local").lower()
    if backend in {"s3", "minio"}:
        return S3Storage(
            bucket=getattr(settings, "S3_BUCKET", "agentflow") or "agentflow",
            endpoint_url=getattr(settings, "S3_ENDPOINT_URL", None) or None,
            access_key=getattr(settings, "S3_ACCESS_KEY", None) or None,
            secret_key=getattr(settings, "S3_SECRET_KEY", None) or None,
            region=getattr(settings, "S3_REGION", "us-east-1") or "us-east-1",
            prefix=getattr(settings, "S3_PREFIX", "") or "",
        )
    root = getattr(settings, "LOCAL_STORAGE_PATH", "data/uploads") or "data/uploads"
    return LocalStorage(root)
