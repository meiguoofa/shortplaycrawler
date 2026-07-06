import base64
import io
import urllib.request

from openai import OpenAI

from config import (
    DOUBAO_API_KEY,
    DOUBAO_BASE_URL,
    DOUBAO_DEFAULT_IMAGE_MODEL,
    DOUBAO_IMAGE_SIZE,
)
from storage.s3 import S3StorageClient


def _client() -> OpenAI:
    return OpenAI(api_key=DOUBAO_API_KEY, base_url=DOUBAO_BASE_URL)


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
    import json
    req = urllib.request.Request(
        DOUBAO_BASE_URL + "/images/generations",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {DOUBAO_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    img_url = (data.get("data") or [{}])[0].get("url") if isinstance(data.get("data"), list) else None
    if not img_url:
        raise RuntimeError(f"doubao image gen returned no url: {data}")

    # Download the generated image bytes (ARK-hosted URL is temporary)
    img_req = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(img_req, timeout=120) as img_resp:
        return img_resp.read()


def upload_poster_to_tos(image_bytes: bytes, object_key: str) -> str:
    """Upload generated poster bytes to TOS. Returns public URL."""
    storage = S3StorageClient()
    result = storage.upload_fileobj(
        io.BytesIO(image_bytes),
        object_key,
        content_type="image/png",
    )
    return result.object_url
