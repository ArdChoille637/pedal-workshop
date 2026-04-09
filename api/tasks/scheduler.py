"""APScheduler setup for background supplier polling."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from api.config import settings

logger = logging.getLogger(__name__)


def start_scheduler() -> BackgroundScheduler | None:
    if settings.poll_interval <= 0:
        logger.info("Supplier polling disabled (poll_interval <= 0)")
        return None

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _run_poll,
        "interval",
        seconds=settings.poll_interval,
        id="supplier_poll",
        name="Poll all enabled suppliers",
        misfire_grace_time=300,
    )
    scheduler.start()
    logger.info(f"Supplier polling scheduler started (interval: {settings.poll_interval}s)")
    return scheduler


def stop_scheduler(scheduler: BackgroundScheduler | None):
    if scheduler:
        scheduler.shutdown(wait=False)
        logger.info("Supplier polling scheduler stopped")


def _run_poll():
    from api.services.supplier_poller import poll_all_suppliers

    try:
        poll_all_suppliers()
    except Exception:
        logger.exception("Supplier poll failed")
