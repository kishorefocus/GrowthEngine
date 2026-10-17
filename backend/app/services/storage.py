"""
Storage service for Cloudflare R2 / S3-compatible asset storage.
Generates presigned upload URLs for video and image assets.
"""
import logging
import uuid
from typing import Optional

import boto3
from botocore.config import Config

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_s3_client():
    """Return configured boto3 S3 client for R2 or AWS S3."""
    if not (settings.s3_key and settings.s3_secret):
        return None

    endpoint = settings.s3_endpoint or None
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.s3_key,
        aws_secret_access_key=settings.s3_secret,
        config=Config(signature_version="s3v4"),
        region_name="auto" if "r2.cloudflarestorage" in (endpoint or "") else "us-east-1",
    )


def generate_presigned_upload_url(
    filename: str,
    content_type: str = "video/mp4",
    folder: str = "videos",
    expires_in: int = 3600,
) -> dict:
    """
    Generate a presigned PUT URL for client-side asset upload.
    Returns:
        {
            "upload_url": str,
            "public_url": str,
            "key": str
        }
    """
    key = f"{folder}/{uuid.uuid4().hex[:12]}_{filename}"
    s3_client = _get_s3_client()
    bucket = settings.s3_bucket or "growthengine-assets"

    if s3_client:
        try:
            upload_url = s3_client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": bucket,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
            )
            # If endpoint is R2, public URL depends on custom domain or endpoint
            endpoint_clean = (settings.s3_endpoint or "").rstrip("/")
            if endpoint_clean:
                public_url = f"{endpoint_clean}/{bucket}/{key}"
            else:
                public_url = f"https://{bucket}.s3.amazonaws.com/{key}"

            return {
                "upload_url": upload_url,
                "public_url": public_url,
                "key": key,
            }
        except Exception as exc:
            logger.error("Failed to generate presigned S3 URL: %s", exc)

    # Fallback / local dev simulation
    fallback_base = settings.api_url.rstrip("/")
    return {
        "upload_url": f"{fallback_base}/api/v1/videos/upload-direct?key={key}",
        "public_url": f"{fallback_base}/static/{key}",
        "key": key,
    }
