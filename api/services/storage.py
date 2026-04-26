"""
Cloudflare R2 storage service (S3-compatible via boto3).
Falls back gracefully when credentials are not configured.
"""
import logging
import mimetypes
import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from api.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_s3_client = None


def _get_client():
    global _s3_client
    if _s3_client is not None:
        return _s3_client
    if not settings.r2_account_id or not settings.r2_access_key_id:
        return None
    try:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            region_name="auto",
        )
        return _s3_client
    except Exception as e:
        logger.error(f"R2 client init failed: {e}")
        return None


def upload_file(local_path: str | Path, object_key: str) -> str | None:
    """Upload file to R2. Returns public URL or None if R2 not configured."""
    client = _get_client()
    if client is None:
        return None

    local_path = str(local_path)
    content_type, _ = mimetypes.guess_type(local_path)
    content_type = content_type or "application/octet-stream"

    try:
        client.upload_file(
            local_path,
            settings.r2_bucket_name,
            object_key,
            ExtraArgs={"ContentType": content_type},
        )
        if settings.r2_public_url:
            return f"{settings.r2_public_url.rstrip('/')}/{object_key}"
        return object_key  # Return key if no public URL configured
    except (ClientError, NoCredentialsError) as e:
        logger.error(f"R2 upload failed for {object_key}: {e}")
        return None


def upload_bytes(data: bytes, object_key: str, content_type: str = "application/octet-stream") -> str | None:
    """Upload raw bytes to R2."""
    client = _get_client()
    if client is None:
        return None
    try:
        client.put_object(
            Bucket=settings.r2_bucket_name,
            Key=object_key,
            Body=data,
            ContentType=content_type,
        )
        if settings.r2_public_url:
            return f"{settings.r2_public_url.rstrip('/')}/{object_key}"
        return object_key
    except (ClientError, NoCredentialsError) as e:
        logger.error(f"R2 put_object failed for {object_key}: {e}")
        return None


def delete_file(object_key: str) -> bool:
    client = _get_client()
    if client is None:
        return False
    try:
        client.delete_object(Bucket=settings.r2_bucket_name, Key=object_key)
        return True
    except ClientError as e:
        logger.error(f"R2 delete failed for {object_key}: {e}")
        return False


def get_presigned_url(object_key: str, expires_in: int = 3600) -> str | None:
    client = _get_client()
    if client is None:
        return None
    try:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.r2_bucket_name, "Key": object_key},
            ExpiresIn=expires_in,
        )
    except ClientError as e:
        logger.error(f"R2 presigned URL failed for {object_key}: {e}")
        return None
