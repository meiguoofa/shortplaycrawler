from config import CRAWL_CODE, DETAIL_URL, DEFAULT_SLEEP
from crawler.client import build_url, fetch_with_retry
from models import DramaSeries, get_session


def crawl_details(sleep=DEFAULT_SLEEP):
    """Fetch detail for all series where detail_fetched==False."""
    session = get_session()
    try:
        pending = session.query(DramaSeries).filter_by(detail_fetched=False).all()
        total = len(pending)
        print(f"\n=== Crawling details for {total} series ===")

        for idx, series in enumerate(pending, 1):
            url = build_url(DETAIL_URL, {"book_id": series.series_id, "code": CRAWL_CODE})
            try:
                payload = fetch_with_retry(url, sleep_seconds=sleep)
                data = payload.get("data") or {}

                series.author = data.get("author")
                series.duration = data.get("duration")
                series.detail_category = data.get("category")
                series.detail_desc = data.get("desc")
                series.book_pic = data.get("book_pic")
                series.total_episodes = int(data["total"]) if data.get("total") else None

                # Update title from detail if available
                if data.get("book_name"):
                    series.title = data["book_name"]

                # copyright might come from detail API
                if data.get("copyright"):
                    series.copyright = data["copyright"]
                elif data.get("author") and not series.copyright:
                    series.copyright = data["author"]

                series.detail_fetched = True
                session.commit()
                print(f"  [{idx}/{total}] {series.title} - {series.series_id}")
            except Exception as e:
                session.rollback()
                print(f"  [{idx}/{total}] FAILED {series.series_id}: {e}")
                continue
    finally:
        session.close()

    print("=== Detail crawl complete ===")
