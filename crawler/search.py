import json
from urllib.parse import urlencode

from config import CRAWL_CODE, DEFAULT_SLEEP, SEARCH_API_BASE, SEARCH_PLATFORMS
from crawler.client import fetch_with_retry


def _build_url(keyword: str, action: str, platform: str) -> str:
    params = [
        ("platform", "wpf11"),
        ("action", action),
        ("name", keyword),
        ("code", CRAWL_CODE),
        ("platform", platform),
    ]
    return SEARCH_API_BASE + "?" + urlencode(params)


def fetch_search_one(keyword: str, action: str, platform: str) -> list[dict]:
    """Call one search endpoint, return raw items list (only items with book_id+title)."""
    url = _build_url(keyword, action, platform)
    payload = fetch_with_retry(url, sleep_seconds=DEFAULT_SLEEP)
    data = payload.get("data") or []
    if not isinstance(data, list):
        return []
    return [it for it in data if it.get("book_id") and it.get("title")]


def fetch_search_all(keyword: str, per_keyword_limit: int | None = None,
                     platform_key: str | None = None) -> list[dict]:
    """Search across one or more ';'-separated keywords on a single platform.

    platform_key selects the platform (e.g. 'hg'/'hgmj'/'hm'/'huolong'/'xingyadongli').
    When per_keyword_limit is set, each keyword contributes at most N items
    (after cross-keyword dedup by series_id).
    """
    platform_cfg = next((p for p in SEARCH_PLATFORMS if p["platform"] == platform_key), None)
    if not platform_cfg:
        raise ValueError(f"unknown platform_key: {platform_key!r}")

    keywords = [k.strip() for k in keyword.split(";") if k.strip()]
    if not keywords:
        return []
    action = platform_cfg["action"]
    platform = platform_cfg["platform"]
    by_keyword: dict[str, list[dict]] = {k: [] for k in keywords}
    for k in keywords:
        try:
            by_keyword[k] = fetch_search_one(k, action, platform)
        except Exception as e:
            print(f"  [{k}/{action}/{platform}] failed: {e}")
            by_keyword[k] = []

    seen: dict[str, dict] = {}
    for k in keywords:
        n = 0
        for item in by_keyword[k]:
            if per_keyword_limit is not None and n >= per_keyword_limit:
                break
            sid = str(item.get("book_id") or "")
            if sid and sid not in seen:
                seen[sid] = item
                n += 1
    return list(seen.values())


def _parse_episode_cnt(raw: str | None) -> int | None:
    """Parse '70集全' / '539集全' → 70 / 539. Returns None if no digits found."""
    if not raw:
        return None
    for tok in str(raw).split():
        if tok.isdigit():
            return int(tok)
    digits = "".join(ch for ch in str(raw) if ch.isdigit())
    return int(digits) if digits else None


def _parse_category(sub_title: str | None) -> str | None:
    """Take first segment of sub_title (split by , or ·)."""
    if not sub_title:
        return None
    first = str(sub_title).split(",")[0].split("·")[0].strip()
    return first or None


def normalize_search_item(item: dict) -> dict:
    """Map raw API item → cart_item fields (mirrors DailyNewDrama shape)."""
    return {
        "series_id": str(item.get("book_id") or ""),
        "title": item.get("title", ""),
        "cover_url": item.get("cover"),
        "episode_cnt": _parse_episode_cnt(item.get("episode_cnt")),
        "category": _parse_category(item.get("sub_title")),
        "author": item.get("author"),
        "description": item.get("series_intro"),
        "raw_payload": json.dumps(item, ensure_ascii=False),
    }
