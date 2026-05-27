import sys

from config import CRAWL_CODE, RANKING_BASE_URL, RANKING_LISTS, DEFAULT_LIMIT, DEFAULT_SLEEP
from crawler.client import build_url, fetch_with_retry
from crawler.parsers import parse_recommend_reason_list, hot_content_to_numeric, parse_category_schema
from models import DramaSeries, get_session


def crawl_ranking_list(list_config, limit=DEFAULT_LIMIT, sleep=DEFAULT_SLEEP):
    """Crawl one ranking list with pagination."""
    genre = list_config["genre"]
    genre_type = list_config["genre_type"]
    category = list_config["category"]
    cate = list_config["cate"]

    print(f"\n=== Crawling ranking: {genre_type} - {category} ===")

    seen = {}
    offset = None
    session_id = ""
    rank_order = 0

    while len(seen) < limit:
        params = {
            "filter_ids": genre,
            "session_id": session_id,
            "req_scene": genre,
            "code": CRAWL_CODE,
            "genre": genre,
            "category_dim_theme": cate,
            "category_dim_role": "",
            "category_dim_epoch": "",
            "sort": "hot_score",
            "gender": "",
            "online_time": "",
        }

        if offset is None:
            params.pop("offset", None)
        else:
            params["offset"] = str(offset)
            params["filter_ids"] = ",".join(seen.keys())

        url = build_url(RANKING_BASE_URL, params)
        payload = fetch_with_retry(url, sleep_seconds=sleep)
        data = payload.get("data") or {}
        items = data.get("video_data") or []

        if data.get("session_id"):
            session_id = data["session_id"]

        added = 0
        for item in items:
            series_id = str(item.get("recommend_group_id") or item.get("series_id") or "")
            if not series_id or series_id in seen:
                continue
            seen[series_id] = item
            added += 1

            if len(seen) >= limit:
                break

        print(f"  offset={offset}, got={len(items)}, new={added}, total={len(seen)}")

        if not data.get("has_more") or added == 0:
            break

        offset = 1 if offset is None else offset + 1

    return list(seen.values())


def save_ranking_items(items, list_config):
    """Save ranking items to database."""
    genre_type = list_config["genre_type"]
    category = list_config["category"]

    session = get_session()
    try:
        for idx, item in enumerate(items):
            series_id = str(item.get("recommend_group_id") or item.get("series_id") or "")
            if not series_id:
                continue

            existing = session.query(DramaSeries).filter_by(
                series_id=series_id, genre_type=genre_type, category=category
            ).first()

            if existing:
                continue

            # Parse recommend_reason_list
            raw_reason = item.get("recommend_reason_list")
            if isinstance(raw_reason, list):
                raw_reason = str(raw_reason)
            parsed_reason = parse_recommend_reason_list(raw_reason)

            # Parse category_schema for additional info
            raw_schema = item.get("category_schema")
            if isinstance(raw_schema, list):
                raw_schema = str(raw_schema)
            schema_info = parse_category_schema(raw_schema)

            hot_content = parsed_reason.get("hot_content")
            hot_content_val = hot_content_to_numeric(hot_content) if hot_content else None

            series = DramaSeries(
                series_id=series_id,
                genre_type=genre_type,
                category=category,
                rank_order=idx + 1,
                title=item.get("title", ""),
                cover_url=item.get("cover"),
                episode_cnt=item.get("episode_cnt"),
                play_cnt=item.get("play_cnt"),
                score=item.get("score"),
                video_desc=item.get("video_desc"),
                vid=item.get("vid"),
                hot_score=parsed_reason.get("hot_score"),
                hot_content=hot_content,
                hot_content_value=hot_content_val,
                raw_recommend_reason=raw_reason,
                copyright=schema_info.get("copyright"),
            )
            session.add(series)

        session.commit()
        print(f"  Saved {len(items)} items for {genre_type}-{category}")
    except Exception as e:
        session.rollback()
        print(f"  Error saving ranking items: {e}")
        raise
    finally:
        session.close()


def crawl_all_rankings(limit=DEFAULT_LIMIT, sleep=DEFAULT_SLEEP):
    """Crawl all 6 ranking lists."""
    for list_config in RANKING_LISTS:
        items = crawl_ranking_list(list_config, limit=limit, sleep=sleep)
        if items:
            save_ranking_items(items, list_config)
    print("\n=== All rankings crawled ===")
