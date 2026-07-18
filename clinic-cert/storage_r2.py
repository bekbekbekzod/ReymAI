"""
Cloudflare R2 (S3-compatible) bilan ishlash uchun yordamchi modul.

Kerakli environment o'zgaruvchilari (Render "Environment" bo'limida):
  R2_ACCOUNT_ID        - Cloudflare account ID
  R2_ACCESS_KEY_ID     - R2 API token access key
  R2_SECRET_ACCESS_KEY - R2 API token secret key
  R2_BUCKET_NAME       - R2 bucket nomi (masalan: clinic-certs)
"""
import os
import boto3
from botocore.client import Config

_R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID")
_R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID")
_R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
_R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME")

_client = None


def r2_enabled() -> bool:
    return all([_R2_ACCOUNT_ID, _R2_ACCESS_KEY_ID, _R2_SECRET_ACCESS_KEY, _R2_BUCKET_NAME])


def get_client():
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=f"https://{_R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=_R2_ACCESS_KEY_ID,
            aws_secret_access_key=_R2_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )
    return _client


def upload_pdf(local_path: str, key: str):
    """Local PDF faylni R2 bucket'ga yuklaydi (key masalan: 'certs/<uuid>.pdf')."""
    client = get_client()
    client.upload_file(
        local_path, _R2_BUCKET_NAME, key,
        ExtraArgs={"ContentType": "application/pdf"},
    )


def get_presigned_url(key: str, expires_seconds: int = 3600) -> str:
    """Faylni vaqtinchalik (default 1 soat) ochish/yuklab olish uchun havola."""
    client = get_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": _R2_BUCKET_NAME, "Key": key},
        ExpiresIn=expires_seconds,
    )


def delete_pdf(key: str):
    client = get_client()
    client.delete_object(Bucket=_R2_BUCKET_NAME, Key=key)
