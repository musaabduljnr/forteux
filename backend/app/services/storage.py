from typing import Any
from functools import lru_cache

import boto3
from botocore.config import Config

from app.core.config import Settings, get_settings


class StorageNotConfigured(RuntimeError):
    pass


class S3Storage:
    def __init__(self, settings: Settings | None = None, client: Any | None = None) -> None:
        self.settings = settings or get_settings()
        if client is not None:
            self.client = client
            self.bucket = self.settings.s3_bucket
            return
        try:
            region, bucket = self.settings.require_storage()
        except RuntimeError as error:
            raise StorageNotConfigured(str(error)) from error
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            region_name=region,
            endpoint_url=self.settings.s3_endpoint_url,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path" if self.settings.s3_endpoint_url else "virtual"}),
        )

    def presign_upload(self, key: str, content_type: str, size: int) -> str:
        return self.client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.bucket,
                "Key": key,
                "ContentType": content_type,
                "ContentLength": size,
            },
            ExpiresIn=self.settings.s3_upload_ttl_seconds,
            HttpMethod="PUT",
        )

    def head(self, key: str) -> dict[str, Any]:
        return self.client.head_object(Bucket=self.bucket, Key=key)

    def get_object(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()

    def put_object(self, key: str, data: bytes, content_type: str) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    def presign_download(self, key: str, filename: str) -> str:
        safe_name = filename.replace('"', "").replace("\r", "").replace("\n", "")[:200]
        return self.client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket,
                "Key": key,
                "ResponseContentType": "application/octet-stream",
                "ResponseContentDisposition": f'attachment; filename="{safe_name}"',
            },
            ExpiresIn=self.settings.s3_download_ttl_seconds,
        )

    def delete(self, key: str) -> None:
        paginator = self.client.get_paginator("list_object_versions")
        found_versions = False
        for page in paginator.paginate(Bucket=self.bucket, Prefix=key):
            objects = [
                {"Key": item["Key"], "VersionId": item["VersionId"]}
                for item in [*page.get("Versions", []), *page.get("DeleteMarkers", [])]
                if item.get("Key") == key
            ]
            if objects:
                found_versions = True
                result = self.client.delete_objects(
                    Bucket=self.bucket,
                    Delete={"Objects": objects, "Quiet": True},
                )
                if result.get("Errors"):
                    raise RuntimeError("One or more object versions could not be deleted")
        if not found_versions:
            self.client.delete_object(Bucket=self.bucket, Key=key)

    def healthcheck(self) -> None:
        self.client.head_bucket(Bucket=self.bucket)


@lru_cache
def get_storage() -> S3Storage:
    try:
        return S3Storage()
    except StorageNotConfigured as error:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=503,
            detail={"code": "storage_not_configured", "message": "Object storage is not configured"},
        ) from error
