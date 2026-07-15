"""scheduler/jobs.py — Scheduled Job Definitions (UTC times)."""
import asyncio, logging
from apscheduler.triggers.cron import CronTrigger
import config
from storage.database import get_stats

logger = logging.getLogger(__name__)

async def job_ingestion():
    logger.info("Scheduled: INGESTION")
    from services.pipeline import run_ingestion
    try:
        result = await run_ingestion()
        logger.info("Ingestion done | %s", result)
    except Exception as exc:
        logger.exception("Ingestion job failed: %s", exc)

async def job_extraction():
    logger.info("Scheduled: EXTRACTION")
    from services.pipeline import run_content_extraction
    try:
        n = await run_content_extraction(batch_size=30)
        logger.info("Extraction done | processed=%d", n)
    except Exception as exc:
        logger.exception("Extraction job failed: %s", exc)

async def job_analysis():
    logger.info("Scheduled: ANALYSIS")
    from services.pipeline import run_analysis
    try:
        n = await run_analysis()
        stats = get_stats()
        logger.info("Analysis done | done=%d | truncations=%d", n, stats["ai_truncations"])
        if stats["ai_truncations"] > 0:
            logger.warning("AI truncations detected: %d — check TOKENS_* in config.py", stats["ai_truncations"])
    except Exception as exc:
        logger.exception("Analysis job failed: %s", exc)

async def job_backup():
    if not config.GITHUB_TOKEN: return
    logger.info("Scheduled: BACKUP")
    from services.backup import run_backup
    try:
        result = await run_backup()
        logger.info("Backup done | %s", result[:80])
    except Exception as exc:
        logger.exception("Backup job failed: %s", exc)

async def job_full_daily_run():
    logger.info("Full daily pipeline starting")
    await job_ingestion()
    await asyncio.sleep(5)
    await job_extraction()
    await asyncio.sleep(5)
    await job_analysis()
    await job_backup()
    logger.info("Full daily pipeline complete")

def register_jobs(scheduler):
    # 06:30 IST = 01:00 UTC
    scheduler.add_job(job_ingestion, CronTrigger(hour=1, minute=0),
                      id="daily_ingestion", replace_existing=True,
                      max_instances=1, misfire_grace_time=1800)
    # 07:30 IST = 02:00 UTC
    scheduler.add_job(job_extraction, CronTrigger(hour=2, minute=0),
                      id="daily_extraction", replace_existing=True,
                      max_instances=1, misfire_grace_time=1800)
    # 08:30 IST = 03:00 UTC
    scheduler.add_job(job_analysis, CronTrigger(hour=3, minute=0),
                      id="daily_analysis", replace_existing=True,
                      max_instances=1, misfire_grace_time=3600)
    # 00:30 IST = 19:00 UTC
    scheduler.add_job(job_backup, CronTrigger(hour=19, minute=0),
                      id="daily_backup", replace_existing=True,
                      max_instances=1, misfire_grace_time=3600)
    logger.info("Scheduled jobs registered | 01:00/02:00/03:00/19:00 UTC")
