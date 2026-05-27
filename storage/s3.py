from boto3.s3.transfer import TransferConfig

import boto3
from botocore.config import Config as BotoConfig

from storage.base import ObjectStorageClient, UploadResult
from config import TOS_CONFIG


class S3StorageClient(ObjectStorageClient):
    def __init__(self):
        self.endpoint_url = TOS_CONFIG["endpoint_url"]
        self.region = TOS_CONFIG["region"]
        self.bucket = TOS_CONFIG["bucket"]
        self.public_base_url = TOS_CONFIG["public_base_url"]

        self.client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            region_name=self.region,
            aws_access_key_id=TOS_CONFIG["access_key_id"],
            aws_secret_access_key=TOS_CONFIG["secret_access_key"],
            config=BotoConfig(
                signature_version="s3v4",
                s3={"addressing_style": "virtual"},
                max_pool_connections=20,
            ),
        )
        self.transfer_config = TransferConfig(
            multipart_threshold=5 * 1024 * 1024,   # 5MB above → multipart
            multipart_chunksize=5 * 1024 * 1024,    # 5MB per part
            max_concurrency=10,                      # 10 threads per upload
        )

    def upload_fileobj(self, fileobj, object_key: str, content_type: str = "video/mp4") -> UploadResult:
        self.client.upload_fileobj(
            fileobj,
            self.bucket,
            object_key,
            ExtraArgs={"ContentType": content_type},
            Config=self.transfer_config,
        )
        return UploadResult(
            object_key=object_key,
            object_url=self.get_public_url(object_key),
        )

    def get_public_url(self, object_key: str) -> str:
        return f"{self.public_base_url}/{object_key}"
