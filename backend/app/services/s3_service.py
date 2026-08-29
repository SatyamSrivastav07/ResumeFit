from functools import lru_cache
from typing import Any

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings


class S3ConfigurationError(RuntimeError):
    """Raised when required private S3 configuration is unavailable."""


class S3OperationError(RuntimeError):
    """Raised when an S3 operation fails."""


class S3ObjectNotFoundError(S3OperationError):
    """Raised when a requested private S3 object does not exist."""


@lru_cache(maxsize=1)
def get_s3_client() -> BaseClient:
    required_values = {
        "AWS_REGION": settings.aws_region,
        "AWS_S3_BUCKET": settings.aws_s3_bucket,
    }
    missing = [name for name, value in required_values.items() if not value]
    if missing:
        raise S3ConfigurationError(
            f"Missing required S3 configuration: {', '.join(missing)}"
        )

    credential_options = {}
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        credential_options = {
            "aws_access_key_id": settings.aws_access_key_id,
            "aws_secret_access_key": settings.aws_secret_access_key,
        }

    return boto3.client(
        "s3",
        **credential_options,
        region_name=settings.aws_region,
        config=Config(
            connect_timeout=settings.aws_connect_timeout_seconds,
            read_timeout=settings.aws_read_timeout_seconds,
            retries={"max_attempts": 3, "mode": "standard"},
            signature_version="s3v4",
        ),
    )


def _bucket_name() -> str:
    if not settings.aws_s3_bucket:
        raise S3ConfigurationError("AWS_S3_BUCKET is not configured.")
    return settings.aws_s3_bucket


def upload_file(file_bytes: bytes, key: str, content_type: str) -> None:
    """Upload a private object without applying any public ACL."""

    try:
        get_s3_client().put_object(
            Bucket=_bucket_name(),
            Key=key,
            Body=file_bytes,
            ContentType=content_type,
        )
    except S3ConfigurationError:
        raise
    except (BotoCoreError, ClientError) as exc:
        raise S3OperationError("S3 upload failed.") from exc


def download_file(key: str) -> bytes:
    """Download a private object and return its bytes."""

    try:
        response = get_s3_client().get_object(Bucket=_bucket_name(), Key=key)
        body = response["Body"]
        try:
            return body.read()
        finally:
            body.close()
    except S3ConfigurationError:
        raise
    except ClientError as exc:
        error = exc.response.get("Error", {})
        if str(error.get("Code")) in {"NoSuchKey", "404", "NotFound"}:
            raise S3ObjectNotFoundError("S3 object was not found.") from exc
        raise S3OperationError("S3 download failed.") from exc
    except (BotoCoreError, KeyError, OSError) as exc:
        raise S3OperationError("S3 download failed.") from exc


def delete_file(key: str) -> None:
    try:
        get_s3_client().delete_object(Bucket=_bucket_name(), Key=key)
    except S3ConfigurationError:
        raise
    except (BotoCoreError, ClientError) as exc:
        raise S3OperationError("S3 delete failed.") from exc


def generate_presigned_url(
    key: str,
    *,
    expires_in: int = 900,
    method: str = "get_object",
    response_content_disposition: str | None = None,
    response_content_type: str | None = None,
) -> str:
    try:
        client: Any = get_s3_client()
        params = {"Bucket": _bucket_name(), "Key": key}
        if response_content_disposition:
            params["ResponseContentDisposition"] = response_content_disposition
        if response_content_type:
            params["ResponseContentType"] = response_content_type
        return client.generate_presigned_url(
            method,
            Params=params,
            ExpiresIn=expires_in,
        )
    except S3ConfigurationError:
        raise
    except (BotoCoreError, ClientError) as exc:
        raise S3OperationError("S3 presigned URL generation failed.") from exc
