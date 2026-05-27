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
    elif args.command == "crawl-full":
        cmd_crawl_full(args)
    elif args.command == "serve":
        cmd_serve(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
