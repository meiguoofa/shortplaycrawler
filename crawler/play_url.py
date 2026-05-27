import io
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import tos

from config import CRAWL_CODE, PLAY_URL, PLAY_URL_SLEEP, VIDEO_QUALITY, DOWNLOAD_CONCURRENCY, VEFAAS_URL, TOS_CONFIG
from crawler.client import build_url, fetch_with_retry
from models import DramaSeries, DramaEpisode, get_session
from storage.s3 import S3StorageClient


def _get_tos_client():
    return tos.TosClientV2(
        ak=TOS_CONFIG["access_key_id"],
        sk=TOS_CONFIG["secret_access_key"],
        endpoint="tos-cn-shanghai.volces.com",
        region=TOS_CONFIG["region"],
        request_timeout=120,
    )


# ── Mode 1: TOS fetch_object (server-side fetch, no bandwidth used) ──

def _tos_fetch(video_url, object_key):
    """TOS server-side fetch: TOS downloads the URL internally. Returns (object_url, file_size)."""
    client = _get_tos_client()
    result = client.fetch_object(
        bucket=TOS_CONFIG["bucket"],
        key=object_key,
        url=video_url,
        ignore_same_key=True,
    )
    # Get file size via head_object
    head = client.head_object(TOS_CONFIG["bucket"], object_key)
    file_size = head.content_length if hasattr(head, "content_length") else None
    object_url = f"{TOS_CONFIG['public_base_url']}/{object_key}"
    return object_url, file_size


# ── Mode 2: veFaaS cloud function ──

def _call_vefaas(tasks):
    """Call veFaaS function to transfer videos internally."""
    payload = json.dumps({"tasks": tasks}).encode("utf-8")
    req = urllib.request.Request(
        VEFAAS_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("results", [])


# ── Mode 3: Local streaming fallback ──

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
            time.sleep(0.05)

    def seekable(self):
        return False

    def readable(self):
        return True

    def writable(self):
        return False


def _local_stream_upload(video_url, object_key):
    """Download from video_url, stream-upload to TOS via local server."""
    import threading
    storage = S3StorageClient()
    pipe = _PipeStream()
    total_size = [0]

    def writer():
        try:
            req = urllib.request.Request(video_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=300) as resp:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    pipe.write_chunk(chunk)
                    total_size[0] += len(chunk)
        finally:
            pipe.close_writer()

    t = threading.Thread(target=writer, daemon=True)
    t.start()
    result = storage.upload_fileobj(pipe, object_key)
    t.join(timeout=600)
    return result.object_url, total_size[0]


# ── Unified episode processor ──

def _get_mode():
    if VEFAAS_URL:
        return "veFaaS"
    return "tos_fetch"


def process_episode(episode, series, quality=VIDEO_QUALITY):
    """Fetch play URL, transfer video to TOS (TOS server-side fetch preferred)."""
    db = get_session()
    mode = _get_mode()

    try:
        ep = db.query(DramaEpisode).filter_by(video_id=episode.video_id).first()
        if not ep or ep.upload_status == "uploaded":
            return True

        ep.upload_status = "url_fetched"
        db.commit()

        # Fetch play URL
        url = build_url(PLAY_URL, {"video_id": ep.video_id, "code": CRAWL_CODE, "level": quality})
        payload = fetch_with_retry(url, sleep_seconds=PLAY_URL_SLEEP)
        play_data = payload.get("data") or {}
        video_url = play_data.get("video_url")

        if not video_url:
            ep.upload_status = "failed"
            ep.error_message = "No video_url in response"
            db.commit()
            return False

        ep.quality = play_data.get("quality", quality)
        ep.origin_expire_time = play_data.get("expire_time")
        ep.origin_url_fetched_at = datetime.now(timezone.utc)
        ep.upload_status = "uploading"
        db.commit()

        object_key = f"{series.genre_type}/{series.category}/{series.series_id}/{ep.episode_no:03d}_{ep.video_id}.mp4"

        if mode == "tos_fetch":
            object_url, file_size = _tos_fetch(video_url, object_key)
        elif mode == "veFaaS":
            results = _call_vefaas([{"video_url": video_url, "object_key": object_key}])
            result = results[0] if results else {}
            if result.get("error"):
                ep.upload_status = "failed"
                ep.error_message = result["error"][:500]
                db.commit()
                print(f"    FAILED: {ep.episode_title}: {result['error']}")
                return False
            object_url = result["object_url"]
            file_size = result.get("file_size")
        else:
            object_url, file_size = _local_stream_upload(video_url, object_key)

        ep.upload_status = "uploaded"
        ep.object_storage_url = object_url
        ep.object_key = object_key
        ep.file_size = file_size
        db.commit()

        size_mb = (file_size or 0) / 1024 / 1024
        print(f"    Uploaded [{mode}]: {ep.episode_title} ({size_mb:.1f}MB) -> {object_url}")
        return True

    except Exception as e:
        try:
            ep = db.query(DramaEpisode).filter_by(video_id=episode.video_id).first()
            if ep:
                ep.upload_status = "failed"
                ep.error_message = str(e)[:500]
                db.commit()
        except Exception:
            pass
        print(f"    FAILED: {episode.episode_title}: {e}")
        return False
    finally:
        db.close()


def download_and_upload_all():
    """Download and upload videos for all series, 10 episodes concurrently per series."""
    db = get_session()
    try:
        series_list = db.query(DramaSeries).order_by(DramaSeries.id).all()
        total_series = len(series_list)
        mode = _get_mode()
        print(f"\n=== Download & Upload ({mode}): {total_series} series ===")

        for s_idx, series in enumerate(series_list, 1):
            episodes = db.query(DramaEpisode).filter_by(
                series_id=series.series_id
            ).filter(
                DramaEpisode.upload_status.in_(["pending", "failed"])
            ).order_by(DramaEpisode.episode_no).all()

            if not episodes:
                print(f"  [{s_idx}/{total_series}] {series.title} - all done, skipping")
                continue

            total_eps = len(episodes)
            done_count = 0
            print(f"  [{s_idx}/{total_series}] {series.title} - {total_eps} episodes")

            for batch_start in range(0, total_eps, DOWNLOAD_CONCURRENCY):
                batch = episodes[batch_start:batch_start + DOWNLOAD_CONCURRENCY]
                batch_end = min(batch_start + DOWNLOAD_CONCURRENCY, total_eps)
                print(f"    Batch {batch_start+1}-{batch_end} of {total_eps}")

                with ThreadPoolExecutor(max_workers=DOWNLOAD_CONCURRENCY) as executor:
                    futures = {
                        executor.submit(process_episode, ep, series): ep
                        for ep in batch
                    }
                    for future in as_completed(futures):
                        try:
                            future.result()
                        except Exception as e:
                            print(f"    Batch error: {e}")
                        done_count += 1

                if batch_end < total_eps:
                    time.sleep(0.5)

            print(f"  [{s_idx}/{total_series}] {series.title} - {done_count}/{total_eps} processed")

    finally:
        db.close()

    print("=== Download & Upload complete ===")
