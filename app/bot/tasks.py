from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from loguru import logger

_scheduler = None
_bot = None


def init_tasks(scheduler, bot):
    global _scheduler, _bot
    _scheduler = scheduler
    _bot = bot


def cancel_scheduled_finish(giveaway_id: int):
    if _scheduler is None:
        return
    job_id = f"finish_giveaway_{giveaway_id}"
    job = _scheduler.get_job(job_id)
    if job:
        job.remove()
        logger.info(f"Cancelled scheduled finish for giveaway {giveaway_id}")


def schedule_giveaway(giveaway_id: int, run_date: datetime):
    if _scheduler is None:
        logger.error("Scheduler not initialised")
        return

    # DB stores UTC as naive datetime. APScheduler should receive aware UTC datetime
    # to avoid timezone interpretation drift on different hosts/environments.
    if run_date.tzinfo is None:
        run_date_utc = run_date.replace(tzinfo=timezone.utc)
    else:
        run_date_utc = run_date.astimezone(timezone.utc)

    job_id = f"finish_giveaway_{giveaway_id}"
    _scheduler.add_job(
        finish_giveaway_task,
        trigger="date",
        run_date=run_date_utc,
        args=[giveaway_id],
        id=job_id,
        replace_existing=True,
        misfire_grace_time=600,
    )
    run_date_msk = run_date_utc.astimezone(ZoneInfo("Europe/Moscow"))
    logger.info(
        f"Scheduled finish for giveaway {giveaway_id} at "
        f"{run_date_utc.isoformat()} UTC ({run_date_msk.isoformat()} MSK)"
    )


async def finish_giveaway_task(giveaway_id: int):
    logger.info(f"Auto-finishing giveaway {giveaway_id}")
    from app.application.services.giveaway_service import GiveawayService
    from app.application.services.winner_service import WinnerService
    from app.infrastructure.database import async_session_factory
    from app.infrastructure.models import GiveawayStatus
    from app.infrastructure.repositories.channel_repository import ChannelRepository
    from app.infrastructure.repositories.giveaway_repository import GiveawayRepository
    from app.infrastructure.telegram.telegram_service import TelegramService

    async with async_session_factory() as session:
        repo = GiveawayRepository(session)
        giveaway = await repo.get_by_id(giveaway_id)

        if giveaway is None:
            logger.warning(f"Giveaway {giveaway_id} not found during auto-finish")
            return

        if giveaway.status != GiveawayStatus.active:
            logger.info(f"Giveaway {giveaway_id} already finished")
            return

        winner_service = WinnerService(session)
        result = await winner_service.select_random(giveaway_id, giveaway.winners_count)

        if not result.ok:
            logger.error(f"Cannot finish giveaway {giveaway_id}: {result.error}")
            return

        tg = TelegramService(_bot)
        channel_repo = ChannelRepository(session)
        channel = await channel_repo.get_by_id(giveaway.channel_id)
        giveaway_service = GiveawayService(session, tg)
        await giveaway_service.publish_results(giveaway, result.winners, channel.telegram_channel_id)
        await session.commit()

    logger.info(f"Giveaway {giveaway_id} auto-finished successfully")
