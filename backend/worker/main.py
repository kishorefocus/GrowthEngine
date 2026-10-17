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
from worker.jobs.email import check_campaign_health, process_email_events, send_due_emails
from worker.jobs.seo import seo_publish_batch
from worker.jobs.social import (
    generate_weekly_content_batch,
    publish_due_posts,
    refresh_social_tokens,
)


async def startup(ctx):
    """Called once when the worker starts."""
    import logging
    logging.basicConfig(level=logging.INFO)
    if settings.sentry_dsn:
        import sentry_sdk
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            traces_sample_rate=0.2,
        )
    logging.getLogger(__name__).info("ARQ worker started. dry_run=%s", settings.dry_run)


async def shutdown(ctx):
    """Called once when the worker shuts down."""
    pass


class WorkerSettings:
    """ARQ worker configuration."""
    functions = [
        # Prompt 1 jobs
        sync_analytics_rollup,
        # Prompt 2 jobs
        send_due_emails,
        check_campaign_health,
        process_email_events,
        # Prompt 3 jobs
        publish_due_posts,
        generate_weekly_content_batch,
        refresh_social_tokens,
        # Prompt 4 jobs
        seo_publish_batch,
    ]

    cron_jobs = [
        cron(sync_analytics_rollup, hour=2, minute=0),        # nightly at 2am UTC
        cron(send_due_emails, minute=None),                   # every 1 minute
        cron(check_campaign_health, minute={0, 15, 30, 45}),  # every 15 minutes
        cron(publish_due_posts, minute=None),                 # every 1 minute
        cron(generate_weekly_content_batch, weekday=6, hour=18, minute=0),  # Sunday 18:00
        cron(refresh_social_tokens, minute=0),                # hourly
        cron(seo_publish_batch, weekday=0, hour=3, minute=0), # weekly Monday 03:00 UTC
    ]

    on_startup = startup
    on_shutdown = shutdown

    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 10
    job_timeout = 300       # 5 min max per job
    retry_jobs = True
    max_tries = 3           # retry up to 3 times
    keep_result = 3600      # keep results for 1 hour
