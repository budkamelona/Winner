from loguru import logger


class SchedulerService:
    """Thin wrapper — actual scheduling wired in main.py via APScheduler."""

    def __init__(self, scheduler):
        self.scheduler = scheduler

    def schedule_giveaway_finish(self, giveaway_id: int, run_date) -> None:
        from app.bot.tasks import finish_giveaway_task

        job_id = f"finish_giveaway_{giveaway_id}"
        existing = self.scheduler.get_job(job_id)
        if existing:
            existing.remove()
        self.scheduler.add_job(
            finish_giveaway_task,
            trigger="date",
            run_date=run_date,
            args=[giveaway_id],
            id=job_id,
            replace_existing=True,
        )
        logger.info(f"Scheduled finish for giveaway {giveaway_id} at {run_date}")
