import json
from datetime import date, timedelta

from config import CRAWL_CODE, DAILY_NEW_URL, DEFAULT_SLEEP, DETAIL_URL
from crawler.client import build_url, fetch_with_retry
from models import DailyNewDrama, get_session


def fetch_daily_new_raw(fetch_date: date | None = None) -> list[dict]:
    """GET shangxinrili_hg endpoint for a given date, return raw items list.

    Date is serialized as YYYYMMDD (API requirement). If fetch_date is None, API returns today's data.
    Page 1 returns real items; page 2+ return placeholder/reservation items (empty title) — skip them.
    """
    params = {"code": CRAWL_CODE, "page": 1}
    if fetch_date is not None:
        params["date"] = fetch_date.strftime("%Y%m%d")

    url = build_url(DAILY_NEW_URL, params)
    payload = fetch_with_retry(url, sleep_seconds=DEFAULT_SLEEP)
    data = payload.get("data") or []
    if not isinstance(data, list):
        return []

    # Filter out placeholder items (empty title) returned on page 2+
    return [item for item in data if item.get("title")]


def _enrich_with_detail(series_id: str) -> dict:
    """Fetch detail_hg to fill author + desc (returns dict with author/description or {})."""
    url = build_url(DETAIL_URL, {"book_id": series_id, "code": CRAWL_CODE})
    try:
        payload = fetch_with_retry(url, sleep_seconds=DEFAULT_SLEEP)
        data = payload.get("data") or {}
        return {
            "author": data.get("author"),
            "description": data.get("desc"),
        }
    except Exception as e:
        print(f"  detail_hg failed for {series_id}: {e}")
        return {}


def save_daily_new(items: list[dict], fetch_date: date | None = None) -> int:
    """Insert items into DailyNewDrama table (skip if series_id+fetch_date exists)."""
    if fetch_date is None:
        fetch_date = date.today()
    session = get_session()
    inserted = 0
    try:
        for idx, item in enumerate(items, 1):
            series_id = str(item.get("recommend_group_id") or "")
            if not series_id:
                continue

            existing = session.query(DailyNewDrama).filter_by(
                series_id=series_id, fetch_date=fetch_date
            ).first()
            if existing:
                continue

            sub_titles = item.get("sub_title_list") or []
            category = sub_titles[0].get("content") if sub_titles and isinstance(sub_titles[0], dict) else None

            detail = _enrich_with_detail(series_id)

            drama = DailyNewDrama(
                series_id=series_id,
                fetch_date=fetch_date,
                title=item.get("title", ""),
                cover_url=item.get("cover"),
                episode_cnt=item.get("episode_cnt"),
                category=category,
                author=detail.get("author"),
                description=detail.get("description"),
                raw_payload=json.dumps(item, ensure_ascii=False),
            )
            session.add(drama)
            inserted += 1
            print(f"  [{idx}/{len(items)}] {drama.title} (ep={drama.episode_cnt})")

        session.commit()
    except Exception as e:
        session.rollback()
        print(f"  save_daily_new FAILED: {e}")
        raise
    finally:
        session.close()
    return inserted


def crawl_daily_new(fetch_date: date | None = None) -> int:
    """Fetch + save. Used by CLI subcommand + scheduler."""
    if fetch_date is None:
        fetch_date = date.today()
    print(f"=== Crawling daily new dramas for {fetch_date} ===")
    items = fetch_daily_new_raw(fetch_date=fetch_date)
    print(f"  Fetched {len(items)} items")
    inserted = save_daily_new(items, fetch_date=fetch_date)
    print(f"  Inserted {inserted} new dramas")
    print("=== Daily new crawl complete ===")
    return inserted


def crawl_daily_new_range(start_date: date, end_date: date) -> int:
    """Backfill: crawl every date in [start_date, end_date] inclusive. Skips dates with 0 items."""
    total = 0
    current = start_date
    while current <= end_date:
        print(f"\n--- {current} ---")
        try:
            n = crawl_daily_new(fetch_date=current)
            total += n
        except Exception as e:
            print(f"  FAILED for {current}: {e}")
        current += timedelta(days=1)
    print(f"\n=== Range crawl complete: {total} total inserted ===")
    return total
