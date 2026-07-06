from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config import DAILY_NEW_CRON_HOUR, DAILY_NEW_TIMEZONE

_scheduler: BackgroundScheduler | None = None


def _run_daily_crawl():
    """Triggered by scheduler. Imports here to avoid circular import at module load."""
    from crawler.daily_new import crawl_daily_new
    crawl_daily_new()


def start_scheduler() -> None:
    """Start the background scheduler. Idempotent — safe to call multiple times."""
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(timezone=DAILY_NEW_TIMEZONE)
    _scheduler.add_job(
        _run_daily_crawl,
        CronTrigger(hour=DAILY_NEW_CRON_HOUR, minute=0),
        id="daily_new_crawl",
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
