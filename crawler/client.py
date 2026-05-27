import json
import time
import urllib.parse
import urllib.request

from config import DEFAULT_SLEEP, MAX_RETRIES, PLAY_URL_SLEEP


def fetch_json(url, timeout=20):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 crawler",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def build_url(base, params):
    clean = {k: v for k, v in params.items() if v is not None and v != ""}
    return base + "?" + urllib.parse.urlencode(clean, doseq=False)


def fetch_with_retry(url, sleep_seconds=DEFAULT_SLEEP, max_retries=MAX_RETRIES, timeout=20):
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            result = fetch_json(url, timeout=timeout)
            time.sleep(sleep_seconds)
            return result
        except Exception as e:
            last_error = e
            wait = min(2**attempt, 10)
            print(f"  [retry {attempt}/{max_retries}] {e}, waiting {wait}s...")
            time.sleep(wait)
    raise last_error


def parse_seed_url(seed_url):
    parsed = urllib.parse.urlparse(seed_url)
    params = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
    base = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
    return base, params
