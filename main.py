#!/usr/bin/env python3
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import init_db
from config import DEFAULT_LIMIT, DEFAULT_SLEEP


def cmd_init_db(args):
    init_db()
    print("Database initialized.")


def cmd_crawl_ranking(args):
    from crawler.ranking import crawl_all_rankings
    crawl_all_rankings(limit=args.limit, sleep=args.sleep)


def cmd_crawl_detail(args):
    from crawler.detail import crawl_details
    crawl_details(sleep=args.sleep)


def cmd_crawl_episodes(args):
    from crawler.episodes import crawl_episodes
    crawl_episodes(sleep=args.sleep)


def cmd_download_upload(args):
    from crawler.play_url import download_and_upload_all
    download_and_upload_all()


def cmd_crawl_daily_new(args):
    from datetime import date as date_cls
    from crawler.daily_new import crawl_daily_new
    fetch_date = date_cls.today()
    if getattr(args, "date", None):
        from datetime import datetime as dt
        fetch_date = dt.strptime(args.date, "%Y-%m-%d").date()
    crawl_daily_new(fetch_date=fetch_date)


def cmd_run_pipeline(args):
    from pipeline import run_pipeline
    job = run_pipeline(
        daily_new_drama_id=args.drama_id,
        target_lang=args.lang,
        image_model=args.model,
        image_prompt=args.prompt,
        batch_id=args.batch_id,
    )
    print(f"\n=== Pipeline result ===")
    print(f"job_id: {job.id}")
    print(f"status: {job.status}")
    print(f"translated_title: {job.translated_title}")
    print(f"translated_desc: {(job.translated_desc or '')[:100]}")
    print(f"poster_url: {job.poster_object_url}")
    print(f"error: {job.error_message}")


def cmd_crawl_full(args):
    cmd_crawl_ranking(args)
    cmd_crawl_detail(args)
    cmd_crawl_episodes(args)
    if not args.skip_download:
        cmd_download_upload(args)


def cmd_serve(args):
    import uvicorn
    from web.app import app
    uvicorn.run(app, host=args.host, port=args.port)


def main():
    parser = argparse.ArgumentParser(description="短剧数据爬虫")
    sub = parser.add_subparsers(dest="command")

    # init-db
    p_init = sub.add_parser("init-db", help="Initialize database")

    # crawl-ranking
    p_ranking = sub.add_parser("crawl-ranking", help="Crawl all 6 ranking lists")
    p_ranking.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    p_ranking.add_argument("--sleep", type=float, default=DEFAULT_SLEEP)

    # crawl-detail
    p_detail = sub.add_parser("crawl-detail", help="Fetch series details")
    p_detail.add_argument("--sleep", type=float, default=DEFAULT_SLEEP)

    # crawl-episodes
    p_episodes = sub.add_parser("crawl-episodes", help="Fetch episode lists")
    p_episodes.add_argument("--sleep", type=float, default=DEFAULT_SLEEP)

    # download-upload
    p_dl = sub.add_parser("download-upload", help="Download videos and upload to TOS")

    # crawl-daily-new
    p_daily = sub.add_parser("crawl-daily-new", help="Crawl shangxinrili_hg list (default: today)")
    p_daily.add_argument("--date", default=None, help="YYYY-MM-DD; default today")

    # run-pipeline
    p_pipe = sub.add_parser("run-pipeline", help="Run full pipeline on one daily-new drama")
    p_pipe.add_argument("--drama-id", type=int, required=True, help="DailyNewDrama.id")
    p_pipe.add_argument("--lang", required=True, help="target_lang ISO code (en/zh/pt/pt-BR/id)")
    p_pipe.add_argument("--model", default="doubao-seedream-4-0-250828")
    p_pipe.add_argument("--batch-id", default=None, help="optional batch_id (UUID) to group jobs")
    p_pipe.add_argument("--prompt", default=None, help="custom image prompt template; default uses config.py")

    # crawl-full
    p_full = sub.add_parser("crawl-full", help="Full pipeline: ranking + detail + episodes + download")
    p_full.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    p_full.add_argument("--sleep", type=float, default=DEFAULT_SLEEP)
    p_full.add_argument("--skip-download", action="store_true", help="Skip video download/upload phase")

    # serve
    p_serve = sub.add_parser("serve", help="Start web server")
    p_serve.add_argument("--host", default="0.0.0.0")
    p_serve.add_argument("--port", type=int, default=5173)

    args = parser.parse_args()

    if args.command == "init-db":
        cmd_init_db(args)
    elif args.command == "crawl-ranking":
        cmd_crawl_ranking(args)
    elif args.command == "crawl-detail":
        cmd_crawl_detail(args)
    elif args.command == "crawl-episodes":
        cmd_crawl_episodes(args)
    elif args.command == "download-upload":
        cmd_download_upload(args)
    elif args.command == "crawl-daily-new":
        cmd_crawl_daily_new(args)
    elif args.command == "run-pipeline":
        cmd_run_pipeline(args)
    elif args.command == "crawl-full":
        cmd_crawl_full(args)
    elif args.command == "serve":
        cmd_serve(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
