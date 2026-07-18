import io
import subprocess
import time

from storage.s3 import S3StorageClient


def _probe_duration(url: str, timeout: int = 30) -> float:
    """ffprobe 直接读 URL 拿时长（秒）。不落盘。"""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            url,
        ],
        capture_output=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ffprobe failed: {result.stderr.decode('utf-8', errors='replace')[:300]}"
        )
    text = result.stdout.decode("utf-8", errors="replace").strip()
    if not text or text == "N/A":
        raise RuntimeError(f"ffprobe returned no duration for {url}")
    return float(text)


def _seek_to_jpeg(url: str, position_sec: float, timeout: int = 60) -> bytes:
    """ffmpeg 输入级 seek + stdout 输出单帧 JPEG。不落盘。"""
    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-ss", f"{position_sec:.3f}",
            "-i", url,
            "-frames:v", "1",
            "-f", "image2",
            "-q:v", "2",
            "-",
        ],
        capture_output=True,
        timeout=timeout,
    )
    if result.returncode != 0 or not result.stdout:
        raise RuntimeError(
            f"ffmpeg seek failed: {result.stderr.decode('utf-8', errors='replace')[:300]}"
        )
    return result.stdout


def extract_screenshot(
    episode_url: str,
    ratio: float,
    object_key: str,
    max_attempts: int = 3,
) -> tuple[bytes, str]:
    """在视频 ratio 处截图，返回 (jpeg_bytes, tos_url)。全程不落盘。

    1. ffprobe 直接读 URL 拿时长（HTTP 输入，不下载视频）
    2. ffmpeg 输入级 seek (`-ss` 在 `-i` 之前) + stdout 输出单帧 JPEG（不落盘）
    3. JPEG 字节通过 io.BytesIO 上传 TOS（内存流）

    失败重试 max_attempts 次（指数退避 2/4/8s）。
    """
    last_err = None
    for attempt in range(1, max_attempts + 1):
        try:
            duration = _probe_duration(episode_url)
            if duration <= 0:
                raise RuntimeError(f"non-positive duration: {duration}")
            position = duration * ratio
            img_bytes = _seek_to_jpeg(episode_url, position)
            if not img_bytes:
                raise RuntimeError("ffmpeg returned empty jpeg bytes")

            storage = S3StorageClient()
            result = storage.upload_fileobj(
                io.BytesIO(img_bytes),
                object_key,
                content_type="image/jpeg",
            )
            return img_bytes, result.object_url
        except Exception as e:
            last_err = e
            print(f"  [screenshot retry {attempt}/{max_attempts}] {type(e).__name__}: {e}")
            if attempt < max_attempts:
                time.sleep(2 ** attempt)
    raise last_err
