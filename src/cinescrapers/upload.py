import mimetypes
import gzip
import os
import boto3
from pathlib import Path
from botocore.client import Config


def get_s3_client():
    access_key = os.environ["R2_ACCESS_KEY_ID"]
    secret_key = os.environ["R2_SECRET_ACCESS_KEY"]
    endpoint_url = os.environ["R2_ENDPOINT_URL"]
    return boto3.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        endpoint_url=endpoint_url,
        config=Config(signature_version="s3v4"),
        region_name="auto",  # R2 ignores this but boto3 requires it
    )


def upload_file(s3_client, path: Path, key: str, gz_compression: bool = True):
    content_type, _ = mimetypes.guess_type(path)
    content_type = content_type or "application/octet-stream"

    with path.open("rb") as f:
        if gz_compression:
            data = gzip.compress(f.read())
        else:
            data = f.read()
        s3_client.put_object(
            Bucket="cinescrapers",
            Key=key,
            Body=data,
            ContentType=content_type,
            ContentEncoding="gzip",
            CacheControl="public,max-age=3600",
        )
    print(f"Uploaded: {key}")
