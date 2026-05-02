import boto3
from botocore.config import Config

from app.settings import settings


def _client():
    return boto3.client(
        "s3",
        endpoint_url=settings.bucket_endpoint_url or None,
        aws_access_key_id=settings.bucket_access_key_id,
        aws_secret_access_key=settings.bucket_secret_access_key,
        region_name=settings.bucket_region,
        config=Config(signature_version="s3v4"),
    )


def generate_signed_get_url(key: str, expires_seconds: int = 300) -> str:
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.bucket_name, "Key": key},
        ExpiresIn=expires_seconds,
    )


def put_release_artifact(key: str, body: bytes, content_type: str = "application/octet-stream") -> None:
    _client().put_object(
        Bucket=settings.bucket_name,
        Key=key,
        Body=body,
        ContentType=content_type,
    )
