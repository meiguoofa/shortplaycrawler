"""
火山引擎 veFaaS 云函数 — 内网转存视频到 TOS

部署步骤：
1. 登录火山引擎控制台 → veFaaS → 创建函数
2. 运行环境选 Python 3.9，触发器选 HTTP API 网关
3. 将此文件内容粘贴为函数代码
4. 依赖管理添加：boto3
5. 函数配置：内存 512MB，超时 120s
6. 部署后获取触发 URL，填入 config.py 的 VEFAAS_URL
"""

import io
import json
import os
import threading
import urllib.request

import boto3
from botocore.config import Config as BotoConfig
from boto3.s3.transfer import TransferConfig

TOS_CONFIG = {
    "endpoint_url": os.environ.get("TOS_ENDPOINT_URL", "https://tos-s3-cn-shanghai.volces.com"),
    "region": os.environ.get("TOS_REGION", "cn-shanghai"),
    "bucket": os.environ.get("TOS_BUCKET", "duanju123123"),
    "access_key_id": os.environ.get("TOS_ACCESS_KEY_ID", ""),
    "secret_access_key": os.environ.get("TOS_SECRET_ACCESS_KEY", ""),
    "public_base_url": os.environ.get("TOS_PUBLIC_BASE_URL", "https://duanju123123.tos-cn-shanghai.volces.com"),
}

_s3_client = None


def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=TOS_CONFIG["endpoint_url"],
            region_name=TOS_CONFIG["region"],
            aws_access_key_id=TOS_CONFIG["access_key_id"],
            aws_secret_access_key=TOS_CONFIG["secret_access_key"],
            config=BotoConfig(
                signature_version="s3v4",
                s3={"addressing_style": "virtual"},
                max_pool_connections=10,
            ),
        )
    return _s3_client


_transfer_config = TransferConfig(
    multipart_threshold=5 * 1024 * 1024,
    multipart_chunksize=5 * 1024 * 1024,
    max_concurrency=5,
)


class _PipeStream:
    """Pipe: writer thread downloads chunks, boto3 reader uploads them."""

    def __init__(self):
        self._buf = io.BytesIO()
        self._closed = False
        self._pos = 0

    def write_chunk(self, data: bytes):
        self._buf.write(data)

    def close_writer(self):
        self._closed = True

    def read(self, size=-1):
        while True:
            current_len = self._buf.tell()
            available = current_len - self._pos
            if available > 0:
                self._buf.seek(self._pos)
                if size == -1 or size > available:
                    size = available
                data = self._buf.read(size)
                self._pos += len(data)
                if self._pos >= current_len:
                    self._buf = io.BytesIO()
                    self._pos = 0
                return data
            if self._closed:
                return b""
            import time
            time.sleep(0.02)

    def seekable(self):
        return False

    def readable(self):
        return True

    def writable(self):
        return False


def _transfer_one(video_url, object_key):
    """Download from video_url, stream-upload to TOS. Returns (object_url, file_size)."""
    pipe = _PipeStream()
    total_size = [0]
    error = [None]

    def writer():
        try:
            req = urllib.request.Request(video_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    pipe.write_chunk(chunk)
                    total_size[0] += len(chunk)
        except Exception as e:
            error[0] = str(e)
        finally:
            pipe.close_writer()

    t = threading.Thread(target=writer, daemon=True)
    t.start()

    client = _get_s3_client()
    client.upload_fileobj(
        pipe,
        TOS_CONFIG["bucket"],
        object_key,
        ExtraArgs={"ContentType": "video/mp4"},
        Config=_transfer_config,
    )
    t.join(timeout=300)

    if error[0]:
        raise RuntimeError(error[0])

    object_url = f"{TOS_CONFIG['public_base_url']}/{object_key}"
    return object_url, total_size[0]


def handler(event, context):
    """veFaaS entry point.
    Expects JSON body: {"tasks": [{"video_url": "...", "object_key": "..."}, ...]}
    Returns: {"results": [{"object_key": "...", "object_url": "...", "file_size": N, "error": null}, ...]}
    """
    try:
        body = json.loads(event.get("body", "{}"))
    except (json.JSONDecodeError, TypeError):
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Invalid JSON body"}),
        }

    tasks = body.get("tasks", [])
    if not tasks:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "No tasks provided"}),
        }

    results = []
    for task in tasks:
        video_url = task.get("video_url")
        object_key = task.get("object_key")
        if not video_url or not object_key:
            results.append({"object_key": object_key, "object_url": None, "file_size": 0, "error": "Missing video_url or object_key"})
            continue
        try:
            object_url, file_size = _transfer_one(video_url, object_key)
            results.append({"object_key": object_key, "object_url": object_url, "file_size": file_size, "error": None})
        except Exception as e:
            results.append({"object_key": object_key, "object_url": None, "file_size": 0, "error": str(e)})

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"results": results}),
    }
