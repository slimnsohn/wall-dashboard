"""APScheduler integration: weekly Amtrak refresh, cold-start bootstrap."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .amtrak import refresh_amtrak_schedule

logger = logging.getLogger(__name__)

CHICAGO = ZoneInfo("America/Chicago")


def build_scheduler(data_dir: Path) -> AsyncIOScheduler:
    sched = AsyncIOScheduler(timezone=CHICAGO)
    sched.add_job(
        refresh_amtrak_schedule,
        CronTrigger(day_of_week="sun", hour=3, minute=0, timezone=CHICAGO),
        kwargs={"data_dir": data_dir},
        id="amtrak_weekly",
        replace_existing=True,
    )
    return sched


@asynccontextmanager
async def scheduler_lifespan(app, data_dir: Path):
    """FastAPI lifespan: start scheduler + bootstrap missing Amtrak data on cold start."""
    sched = build_scheduler(data_dir)
    sched.start()
    if not (data_dir / "amtrak_schedule.pkl").exists():
        logger.info("No Amtrak schedule cached; triggering initial refresh")
        asyncio.create_task(refresh_amtrak_schedule(data_dir))
    try:
        yield
    finally:
        sched.shutdown(wait=False)
