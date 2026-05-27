import argparse
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_CODE = "FXKBAGV5OJQH"
DETAIL_URL = "http://160.202.253.154:1231/api/hg/wai_api_detail.php"
EPISODES_URL = "http://160.202.253.154:1231/api/hg/wai_api_book.php"
PLAY_URL = "http://43.142.49.190:1789/api/g/gui_play.php"


def fetch_json(url, timeout=20):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 crawler-simulation",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def build_url(base, params):
    clean = {k: v for k, v in params.items() if v is not None}
    return base + "?" + urllib.parse.urlencode(clean, doseq=False)


def parse_seed_url(seed_url):
    parsed = urllib.parse.urlparse(seed_url)
    params = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
    base = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
    return base, params


def crawl_ranking(seed_url, limit, sleep_seconds):
    base, seed_params = parse_seed_url(seed_url)
    seen = {}
    page_summaries = []
    offset = None
    session_id = seed_params.get("session_id", "")

    while len(seen) < limit:
        params = dict(seed_params)
        params["session_id"] = session_id
        if offset is None:
            params.pop("offset", None)
            params["filter_ids"] = seed_params.get("filter_ids") or seed_params.get("genre", "")
        else:
            params["offset"] = str(offset)
            params["filter_ids"] = ",".join(seen.keys())

        url = build_url(base, params)
        payload = fetch_json(url)
        data = payload.get("data") or {}
        items = data.get("video_data") or []
        added = 0

        if data.get("session_id"):
            session_id = data["session_id"]

        for item in items:
            series_id = str(item.get("recommend_group_id") or item.get("series_id") or "")
            if not series_id or series_id in seen:
                continue
            seen[series_id] = item
            added += 1
            if len(seen) >= limit:
                break

        page_summaries.append(
            {
                "offset": offset,
                "request_count": len(items),
                "added_count": added,
                "unique_total": len(seen),
                "has_more": data.get("has_more"),
                "next_offset": data.get("next_offset"),
                "session_id": session_id,
            }
        )

        if not data.get("has_more") or added == 0:
            break

        offset = 1 if offset is None else offset + 1
        time.sleep(sleep_seconds)

    return list(seen.values())[:limit], page_summaries


def fetch_detail(series_id, code):
    return fetch_json(build_url(DETAIL_URL, {"book_id": series_id, "code": code}))


def fetch_episodes(series_id, code):
    return fetch_json(build_url(EPISODES_URL, {"book_id": series_id, "code": code}))


def fetch_play(video_id, code, level):
    return fetch_json(build_url(PLAY_URL, {"video_id": video_id, "code": code, "level": level}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Seed ranking URL captured from the app.")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--code", default=DEFAULT_CODE)
    parser.add_argument("--level", default="720p")
    parser.add_argument("--sleep", type=float, default=0.3)
    parser.add_argument("--sample-play-series", type=int, default=3)
    parser.add_argument("--sample-play-episodes", type=int, default=2)
    parser.add_argument("--detail-limit", type=int, default=0, help="Only fetch details/episodes for the first N ranking items. 0 means all.")
    parser.add_argument("--out-dir", default="data/output/simulations/latest")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ranking_items, page_summaries = crawl_ranking(args.url, args.limit, args.sleep)
    ranking_path = out_dir / "ranking_items.json"
    ranking_path.write_text(json.dumps(ranking_items, ensure_ascii=False, indent=2), encoding="utf-8")

    details = []
    episodes_by_series = {}
    play_samples = []

    detail_items = ranking_items[: args.detail_limit] if args.detail_limit > 0 else ranking_items

    for index, item in enumerate(detail_items, start=1):
        series_id = str(item.get("recommend_group_id") or item.get("series_id"))
        title = item.get("title")
        print(f"[{index}/{len(detail_items)}] detail+episodes {series_id} {title}")

        detail_payload = fetch_detail(series_id, args.code)
        details.append({"series_id": series_id, "payload": detail_payload})
        time.sleep(args.sleep)

        episodes_payload = fetch_episodes(series_id, args.code)
        episodes_by_series[series_id] = episodes_payload
        time.sleep(args.sleep)

        if index <= args.sample_play_series:
            for ep in (episodes_payload.get("data") or [])[: args.sample_play_episodes]:
                video_id = ep.get("video_id")
                if not video_id:
                    continue
                play_payload = fetch_play(video_id, args.code, args.level)
                play_data = play_payload.get("data") or {}
                play_samples.append(
                    {
                        "series_id": series_id,
                        "series_title": title,
                        "episode_title": ep.get("title"),
                        "video_id": video_id,
                        "level": args.level,
                        "code": play_payload.get("code"),
                        "quality": play_data.get("quality"),
                        "expire_time": play_data.get("expire_time"),
                        "video_url_present": bool(play_data.get("video_url")),
                    }
                )
                time.sleep(args.sleep)

    (out_dir / "details.json").write_text(json.dumps(details, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "episodes.json").write_text(json.dumps(episodes_by_series, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "play_url_samples.json").write_text(json.dumps(play_samples, ensure_ascii=False, indent=2), encoding="utf-8")

    total_episodes = 0
    for payload in episodes_by_series.values():
        total_episodes += len(payload.get("data") or [])

    summary = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "ranking_count": len(ranking_items),
        "detail_count": len(details),
        "series_with_episodes": len(episodes_by_series),
        "total_episode_count": total_episodes,
        "play_url_sample_count": len(play_samples),
        "page_summaries": page_summaries,
        "outputs": {
            "ranking_items": str(ranking_path),
            "details": str(out_dir / "details.json"),
            "episodes": str(out_dir / "episodes.json"),
            "play_url_samples": str(out_dir / "play_url_samples.json"),
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
