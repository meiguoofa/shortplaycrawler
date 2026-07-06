import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import CRAWL_CODE, DEFAULT_SLEEP, SEARCH_ACTIONS, SEARCH_API_BASE
from crawler.client import build_url, fetch_with_retry


def fetch_search_one(keyword: str, action: str) -> list[dict]:
    """Call one search endpoint, return raw items list (only items with book_id+title)."""
    url = build_url(SEARCH_API_BASE, {
        "platform": "wpf11",
        "action": action,
        "name": keyword,
        "code": CRAWL_CODE,
    })
    payload = fetch_with_retry(url, sleep_seconds=DEFAULT_SLEEP)
    data = payload.get("data") or []
    if not isinstance(data, list):
        return []
    return [it for it in data if it.get("book_id") and it.get("title")]


def fetch_search_all(keyword: str) -> list[dict]:
    """Aggregate search across 5 platforms, dedup by book_id."""
    seen: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(fetch_search_one, keyword, action): action for action in SEARCH_ACTIONS}
        for f in as_completed(futures):
            action = futures[f]
            try:
                items = f.result()
            except Exception as e:
                print(f"  [{action}] failed: {e}")
                items = []
            for item in items:
                sid = str(item.get("book_id") or "")
                if sid and sid not in seen:
                    seen[sid] = item
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
