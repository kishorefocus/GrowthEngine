"""
ARQ worker application.
Jobs are registered here; each job is defined in worker/jobs/.
The nightly sync_analytics_rollup job is implemented in Prompt 1.
Later prompts register: email sending, social posting, SEO generation.
"""
from arq import cron
from arq.connections import RedisSettings

from app.core.config import settings
from worker.jobs.analytics import sync_analytics_rollup


async def startup(ctx):
    """Called once when the worker starts."""
    import logging
    logging.basicConfig(level=logging.INFO)
    logging.getLogger(__name__).info("ARQ worker started. dry_run=%s", settings.dry_run)


async def shutdown(ctx):
    """Called once when the worker shuts down."""
    pass


class WorkerSettings:
    """ARQ worker configuration."""
    functions = [
        # Prompt 1 jobs
        sync_analytics_rollup,
        # Prompt 2 will add: send_campaign_emails, process_replies
        # Prompt 3 will add: publish_scheduled_posts
        # Prompt 4 will add: generate_seo_pages
    ]

    cron_jobs = [
        cron(sync_analytics_rollup, hour=2, minute=0),  # nightly at 2am UTC
    ]

    on_startup = startup
    on_shutdown = shutdown

    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 10
    job_timeout = 300       # 5 min max per job
    retry_jobs = True
    max_tries = 3           # retry up to 3 times
    keep_result = 3600      # keep results for 1 hour
