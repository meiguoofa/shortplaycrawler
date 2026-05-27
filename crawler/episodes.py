from config import CRAWL_CODE, EPISODES_URL, DEFAULT_SLEEP
from crawler.client import build_url, fetch_with_retry
from models import DramaSeries, DramaEpisode, get_session


def crawl_episodes(sleep=DEFAULT_SLEEP):
    """Fetch episode lists for all series where episodes_fetched==False."""
    session = get_session()
    try:
        pending = session.query(DramaSeries).filter_by(episodes_fetched=False).all()
        total = len(pending)
        print(f"\n=== Crawling episodes for {total} series ===")

        for idx, series in enumerate(pending, 1):
            url = build_url(EPISODES_URL, {"book_id": series.series_id, "code": CRAWL_CODE})
            try:
                payload = fetch_with_retry(url, sleep_seconds=sleep)
                episodes_data = payload.get("data") or []

                for ep_idx, ep in enumerate(episodes_data, 1):
                    video_id = str(ep.get("video_id", ""))
                    if not video_id:
                        continue

                    existing = session.query(DramaEpisode).filter_by(video_id=video_id).first()
                    if existing:
                        continue

                    episode = DramaEpisode(
                        series_id=series.series_id,
                        video_id=video_id,
                        episode_no=ep_idx,
                        episode_title=ep.get("title", f"第{ep_idx}集"),
                        first_pass_time=ep.get("firstPassTime"),
                    )
                    session.add(episode)

                series.episodes_fetched = True
                session.commit()
                ep_count = len(episodes_data)
                print(f"  [{idx}/{total}] {series.title} - {ep_count} episodes")
            except Exception as e:
                session.rollback()
                print(f"  [{idx}/{total}] FAILED {series.series_id}: {e}")
                continue
    finally:
        session.close()

    print("=== Episode crawl complete ===")
