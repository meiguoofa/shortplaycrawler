import base64
import io
import json
import urllib.error
import urllib.request

from openai import OpenAI

from config import (
    DOUBAO_API_KEY,
    DOUBAO_BASE_URL,
    DOUBAO_DEFAULT_IMAGE_MODEL,
    DOUBAO_IMAGE_SIZE,
    MOBINOVA_API_KEY,
    MOBINOVA_BASE_URL,
    MOBINOVA_IMAGE_MODEL,
    MOBINOVA_IMAGE_SIZE,
)
from storage.s3 import S3StorageClient


def _client() -> OpenAI:
    return OpenAI(api_key=DOUBAO_API_KEY, base_url=DOUBAO_BASE_URL)


def _fetch_url_bytes(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def generate_poster(
    prompt: str,
    reference_image_url: str | None = None,
    reference_image_bytes: bytes | None = None,
    model: str = DOUBAO_DEFAULT_IMAGE_MODEL,
    size: str = DOUBAO_IMAGE_SIZE,
) -> bytes:
    """Call doubao-seedream image generation. Returns generated image bytes.

    Either reference_image_url (string URL) or reference_image_bytes (raw bytes,
    will be base64-encoded and passed as a data URL) can be supplied for image-to-image.
    If neither is given, falls back to pure text-to-image.
    """
    body = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "response_format": "url",
    }
    if reference_image_url:
        body["image_url"] = reference_image_url
    elif reference_image_bytes:
        body["image_url"] = "data:image/jpeg;base64," + base64.b64encode(reference_image_bytes).decode("ascii")

    # ARK images.generate doesn't accept image_url via OpenAI SDK param; use raw POST.
    # Retry up to 3 times on transient errors (上游 400/5xx 偶发)
    last_err = None
    data = None
    for attempt in range(1, 4):
        req = urllib.request.Request(
            DOUBAO_BASE_URL + "/images/generations",
            data=json.dumps(body).encode(),
            headers={
                "Authorization": f"Bearer {DOUBAO_API_KEY}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")[:500]
            last_err = RuntimeError(f"HTTP {e.code} {e.reason}: {err_body}")
            print(f"  [doubao retry {attempt}/3] HTTP {e.code}: {err_body[:200]}")
            if attempt < 3:
                import time
                time.sleep(2 ** attempt)
        except Exception as e:
            last_err = e
            print(f"  [doubao retry {attempt}/3] {type(e).__name__}: {e}")
            if attempt < 3:
                import time
                time.sleep(2 ** attempt)
    else:
        raise last_err

    img_url = (data.get("data") or [{}])[0].get("url") if isinstance(data.get("data"), list) else None
    if not img_url:
        raise RuntimeError(f"doubao image gen returned no url: {data}")

    return _fetch_url_bytes(img_url, timeout=120)


def generate_poster_mobinova(
    prompt: str,
    reference_image_url: str | None = None,
    reference_image_bytes: bytes | None = None,
    model: str = MOBINOVA_IMAGE_MODEL,
    size: str = MOBINOVA_IMAGE_SIZE,
) -> bytes:
    """Call Mobinova gpt-image-2. Returns generated image bytes.

    Uses /v1/images/edits (multipart) when a reference image is available (image-to-image),
    otherwise falls back to /v1/images/generations (text-to-image).
    """
    # Build multipart body for /images/edits, or JSON body for /images/generations.
    if reference_image_url:
        ref_bytes = _fetch_url_bytes(reference_image_url, timeout=60)
    elif reference_image_bytes:
        ref_bytes = reference_image_bytes
    else:
        ref_bytes = None

    last_err = None
    img_url = None

    if ref_bytes is not None:
        # /v1/images/edits — multipart form-data
        boundary = "----MobinovaBoundary" + str(hash(prompt))[-8:]
        body_parts = []
        body_parts.append(f"--{boundary}\r\n".encode())
        body_parts.append(b'Content-Disposition: form-data; name="model"\r\n\r\n')
        body_parts.append(f"{model}\r\n".encode())
        body_parts.append(f"--{boundary}\r\n".encode())
        body_parts.append(b'Content-Disposition: form-data; name="prompt"\r\n\r\n')
        body_parts.append(f"{prompt}\r\n".encode())
        body_parts.append(f"--{boundary}\r\n".encode())
        body_parts.append(b'Content-Disposition: form-data; name="size"\r\n\r\n')
        body_parts.append(f"{size}\r\n".encode())
        body_parts.append(f"--{boundary}\r\n".encode())
        body_parts.append(b'Content-Disposition: form-data; name="image"; filename="cover.jpg"\r\n')
        body_parts.append(b'Content-Type: image/jpeg\r\n\r\n')
        body_parts.append(ref_bytes)
        body_parts.append(f"\r\n--{boundary}--\r\n".encode())
        body = b"".join(body_parts)

        for attempt in range(1, 4):
            req = urllib.request.Request(
                MOBINOVA_BASE_URL + "/images/edits",
                data=body,
                headers={
                    "Authorization": f"Bearer {MOBINOVA_API_KEY}",
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=300) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                img_url = (data.get("data") or [{}])[0].get("url")
                if not img_url:
                    raise RuntimeError(f"mobinova edits returned no url: {data}")
                break
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")[:500]
                last_err = RuntimeError(f"HTTP {e.code} {e.reason}: {err_body}")
                print(f"  [mobinova edits retry {attempt}/3] HTTP {e.code}: {err_body[:200]}")
                if attempt < 3:
                    import time
                    time.sleep(2 ** attempt)
            except Exception as e:
                last_err = e
                print(f"  [mobinova edits retry {attempt}/3] {type(e).__name__}: {e}")
                if attempt < 3:
                    import time
                    time.sleep(2 ** attempt)
        else:
            raise last_err
    else:
        # /v1/images/generations — pure text-to-image
        body = json.dumps({
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": size,
            "quality": "medium",
        }).encode()
        for attempt in range(1, 4):
            req = urllib.request.Request(
                MOBINOVA_BASE_URL + "/images/generations",
                data=body,
                headers={
                    "Authorization": f"Bearer {MOBINOVA_API_KEY}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=300) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                img_url = (data.get("data") or [{}])[0].get("url")
                if not img_url:
                    raise RuntimeError(f"mobinova generations returned no url: {data}")
                break
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")[:500]
                last_err = RuntimeError(f"HTTP {e.code} {e.reason}: {err_body}")
                print(f"  [mobinova gen retry {attempt}/3] HTTP {e.code}: {err_body[:200]}")
                if attempt < 3:
                    import time
                    time.sleep(2 ** attempt)
            except Exception as e:
                last_err = e
                print(f"  [mobinova gen retry {attempt}/3] {type(e).__name__}: {e}")
                if attempt < 3:
                    import time
                    time.sleep(2 ** attempt)
        else:
            raise last_err

    return _fetch_url_bytes(img_url, timeout=120)


def upload_poster_to_tos(image_bytes: bytes, object_key: str) -> str:
    """Upload generated poster bytes to TOS. Returns public URL."""
    storage = S3StorageClient()
    result = storage.upload_fileobj(
        io.BytesIO(image_bytes),
        object_key,
        content_type="image/png",
    )
    return result.object_url
